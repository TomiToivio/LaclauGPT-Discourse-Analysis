"""Run lifecycle, checkpoints and idempotent canonical pipeline dispatch."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable

from pydantic import BaseModel, ConfigDict, Field

from laclaugpt.config import compose_config
from laclaugpt.model import Run


class ClaimReason(str, Enum):
    ACQUIRED = "acquired"
    BUSY = "busy"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ClaimResult:
    """Result of trying to acquire exclusive ownership of one document."""
    claimed: bool
    reason: ClaimReason
    token: str | None = None

    def __bool__(self) -> bool:
        return self.claimed


class EffectiveRunConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    project: str
    arena: str = ""
    analysis_profile: str = ""
    machine: str
    execution: str
    analysis: dict[str, bool]
    dataset: dict[str, Any] = Field(default_factory=dict)
    codebook: dict[str, Any] = Field(default_factory=dict)
    backends: dict[str, str]
    services: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    orchestration: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def compose(cls, project: str, machine: str, execution: str = "cli",
                overrides: dict[str, Any] | None = None, *,
                arena: str | None = None):
        return cls.model_validate(
            compose_config(project, machine, execution, overrides, arena=arena)
        )

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"), sort_keys=True,
            ensure_ascii=False, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RunStore:
    """SQLite run journal; unique work keys make retries idempotent."""
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY, project TEXT, machine TEXT, execution_mode TEXT,
            started_at TEXT, finished_at TEXT, status TEXT, hostname TEXT,
            slurm_job_id TEXT, parent_run_id TEXT, configuration_snapshot TEXT,
            pipeline_version TEXT, config_fingerprint TEXT,
            analysis_profile TEXT, arena_id TEXT)""")
        run_columns = {
            row[1] for row in self.connection.execute("PRAGMA table_info(runs)")
        }
        if "analysis_profile" not in run_columns:
            self.connection.execute(
                "ALTER TABLE runs ADD COLUMN analysis_profile TEXT DEFAULT ''"
            )
        if "arena_id" not in run_columns:
            self.connection.execute(
                "ALTER TABLE runs ADD COLUMN arena_id TEXT DEFAULT ''"
            )

        self.connection.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
            config_fingerprint TEXT, source_id TEXT, run_id TEXT, status TEXT,
            attempts INTEGER DEFAULT 1, updated_at TEXT, error TEXT, claim_token TEXT,
            PRIMARY KEY(config_fingerprint, source_id))""")
        columns = {
            row[1] for row in self.connection.execute("PRAGMA table_info(checkpoints)")
        }
        if "claim_token" not in columns:
            self.connection.execute(
                "ALTER TABLE checkpoints ADD COLUMN claim_token TEXT"
            )
        self.connection.commit()

    def create_run(self, config: EffectiveRunConfig, pipeline_version: str,
                   parent_run_id: str | None = None) -> Run:
        run = Run(
            project=config.project,
            machine=config.machine,
            execution_mode=config.execution,
            status="running",
            started_at=datetime.now(timezone.utc),
            hostname=socket.gethostname(),
            slurm_job_id=os.getenv("SLURM_JOB_ID"),
            parent_run_id=parent_run_id,
            configuration_snapshot=config.model_dump(mode="json"),
            pipeline_version=pipeline_version,
        )
        row = run.model_dump(mode="json")
        snapshot = json.dumps(
            row["configuration_snapshot"], ensure_ascii=False, sort_keys=True
        )
        self.connection.execute(
            """INSERT INTO runs (
                run_id, project, machine, execution_mode, started_at, finished_at,
                status, hostname, slurm_job_id, parent_run_id,
                configuration_snapshot, pipeline_version, config_fingerprint,
                analysis_profile, arena_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["run_id"], row["project"], row["machine"],
                row["execution_mode"], row["started_at"], row["finished_at"],
                row["status"], row["hostname"], row["slurm_job_id"],
                row["parent_run_id"], snapshot, row["pipeline_version"],
                config.fingerprint(), config.analysis_profile, config.arena,
            ),
        )
        self.connection.commit()
        return run

    def finish_run(self, run: Run, status: str) -> Run:
        finished = datetime.now(timezone.utc)
        self.connection.execute(
            "UPDATE runs SET status=?, finished_at=? WHERE run_id=?",
            (status, finished.isoformat(), run.run_id),
        )
        self.connection.commit()
        return run.model_copy(update={"status": status, "finished_at": finished})

    def claim(self, config: EffectiveRunConfig, run_id: str, source_id: str,
              *, retry_failed: bool = False, skip_completed: bool = True,
              stale_after: timedelta | None = None) -> ClaimResult:
        fingerprint = config.fingerprint()
        now = datetime.now(timezone.utc)
        token = uuid.uuid4().hex
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            row = self.connection.execute(
                "SELECT status, attempts, updated_at FROM checkpoints "
                "WHERE config_fingerprint=? AND source_id=?",
                (fingerprint, source_id),
            ).fetchone()
            if row and row[0] == "completed" and skip_completed:
                self.connection.commit()
                return ClaimResult(False, ClaimReason.COMPLETED)
            if row and row[0] == "failed" and not retry_failed:
                self.connection.commit()
                return ClaimResult(False, ClaimReason.FAILED)
            if row and row[0] == "running":
                updated_at = datetime.fromisoformat(row[2])
                is_stale = (
                    stale_after is not None and now - updated_at >= stale_after
                )
                if not is_stale:
                    self.connection.commit()
                    return ClaimResult(False, ClaimReason.BUSY)
            if row:
                self.connection.execute(
                    "UPDATE checkpoints SET run_id=?, status='running', attempts=?, "
                    "updated_at=?, error=NULL, claim_token=? "
                    "WHERE config_fingerprint=? AND source_id=?",
                    (
                        run_id, row[1] + 1, now.isoformat(), token,
                        fingerprint, source_id,
                    ),
                )
            else:
                self.connection.execute(
                    "INSERT INTO checkpoints "
                    "(config_fingerprint, source_id, run_id, status, attempts, "
                    "updated_at, error, claim_token) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        fingerprint, source_id, run_id, "running", 1,
                        now.isoformat(), None, token,
                    ),
                )
            self.connection.commit()
            return ClaimResult(True, ClaimReason.ACQUIRED, token)
        except Exception:
            self.connection.rollback()
            raise

    def checkpoint(self, config: EffectiveRunConfig, run_id: str, source_id: str,
                   status: str = "completed", error: str | None = None,
                   *, claim_token: str | None = None) -> bool:
        ownership = "run_id=?"
        parameters: list[Any] = [
            status, datetime.now(timezone.utc).isoformat(), error,
            config.fingerprint(), source_id, run_id,
        ]
        if claim_token is not None:
            ownership += " AND claim_token=?"
            parameters.append(claim_token)
        cursor = self.connection.execute(
            "UPDATE checkpoints SET status=?, updated_at=?, error=? "
            "WHERE config_fingerprint=? AND source_id=? AND status='running' AND "
            + ownership,
            parameters,
        )
        self.connection.commit()
        return cursor.rowcount == 1


class ExecutionCoordinator:
    """All backends end here and call the same pipeline function."""
    def __init__(self, config: EffectiveRunConfig, store: RunStore,
                 pipeline: Callable[[EffectiveRunConfig, Run, RunStore], Any],
                 pipeline_version: str = "2.0.0",
                 parent_run_id: str | None = None):
        self.config, self.store, self.pipeline = config, store, pipeline
        self.pipeline_version = pipeline_version
        self.parent_run_id = parent_run_id

    def execute(self, parent_run_id: str | None = None):
        run = self.store.create_run(
            self.config, self.pipeline_version,
            parent_run_id or self.parent_run_id,
        )
        try:
            result = self.pipeline(self.config, run, self.store)
        except Exception:
            self.store.finish_run(run, "failed")
            raise
        return self.store.finish_run(run, "completed"), result

    def process_items(self, run: Run, items: Iterable[Any],
                      analyzer: Callable[[Any, str], Any]):
        policy = self.config.orchestration.get("runtime", {})
        results = []
        for item in items:
            source_id = getattr(item, "source_id", None) or item["source_id"]
            lease_seconds = policy.get("claim_lease_seconds")
            claim = self.store.claim(
                self.config, run.run_id, source_id,
                retry_failed=policy.get("retry_failed_items", False),
                skip_completed=policy.get("skip_already_processed", True),
                stale_after=(
                    timedelta(seconds=lease_seconds)
                    if lease_seconds is not None else None
                ),
            )
            if not claim:
                continue
            try:
                result = analyzer(item, run.run_id)
                results.append(_attach_run_id(result, run.run_id))
                self.store.checkpoint(
                    self.config, run.run_id, source_id,
                    claim_token=claim.token,
                )
            except Exception as exc:
                self.store.checkpoint(
                    self.config, run.run_id, source_id, "failed", str(exc),
                    claim_token=claim.token,
                )
                if not policy.get("retry_failed_items", False):
                    raise
        return results


def _attach_run_id(result: Any, run_id: str) -> Any:
    """Attach lineage recursively to model/dict/list analysis outputs."""
    if isinstance(result, BaseModel):
        if "run_id" not in type(result).model_fields:
            raise TypeError(
                f"analysis result {type(result).__name__} has no run_id field"
            )
        return result.model_copy(update={"run_id": run_id})
    if isinstance(result, list):
        return [_attach_run_id(value, run_id) for value in result]
    if isinstance(result, tuple):
        return tuple(_attach_run_id(value, run_id) for value in result)
    if isinstance(result, dict):
        return {**result, "run_id": run_id}
    raise TypeError(
        "analysis results must be Pydantic models, mappings, or sequences"
    )
