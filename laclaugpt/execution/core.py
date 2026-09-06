"""Run lifecycle, checkpoints and idempotent canonical pipeline dispatch."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from pydantic import BaseModel, ConfigDict, Field

from laclaugpt.config import compose_config
from laclaugpt.model import Run


class EffectiveRunConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    project: str
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
                overrides: dict[str, Any] | None = None):
        return cls.model_validate(compose_config(project, machine, execution, overrides))

    def fingerprint(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True,
                             ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RunStore:
    """SQLite run journal; unique work keys make retries idempotent."""
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY, project TEXT, machine TEXT, execution_mode TEXT,
            started_at TEXT, finished_at TEXT, status TEXT, hostname TEXT,
            slurm_job_id TEXT, parent_run_id TEXT, configuration_snapshot TEXT,
            pipeline_version TEXT, config_fingerprint TEXT)""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS checkpoints (
            config_fingerprint TEXT, source_id TEXT, run_id TEXT, status TEXT,
            attempts INTEGER DEFAULT 1, updated_at TEXT, error TEXT,
            PRIMARY KEY(config_fingerprint, source_id))""")
        self.connection.commit()

    def create_run(self, config: EffectiveRunConfig, pipeline_version: str,
                   parent_run_id: str | None = None) -> Run:
        run = Run(project=config.project, machine=config.machine,
                  execution_mode=config.execution, status="running",
                  started_at=datetime.now(timezone.utc), hostname=socket.gethostname(),
                  slurm_job_id=os.getenv("SLURM_JOB_ID"), parent_run_id=parent_run_id,
                  configuration_snapshot=config.model_dump(mode="json"),
                  pipeline_version=pipeline_version)
        row = run.model_dump(mode="json")
        row["configuration_snapshot"] = json.dumps(row["configuration_snapshot"],
                                                    ensure_ascii=False, sort_keys=True)
        self.connection.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (*[row[k] for k in ("run_id", "project", "machine", "execution_mode",
                "started_at", "finished_at", "status", "hostname", "slurm_job_id",
                "parent_run_id", "configuration_snapshot", "pipeline_version")],
             config.fingerprint()))
        self.connection.commit()
        return run

    def finish_run(self, run: Run, status: str) -> Run:
        finished = datetime.now(timezone.utc)
        self.connection.execute("UPDATE runs SET status=?, finished_at=? WHERE run_id=?",
                                (status, finished.isoformat(), run.run_id))
        self.connection.commit()
        return run.model_copy(update={"status": status, "finished_at": finished})

    def claim(self, config: EffectiveRunConfig, run_id: str, source_id: str,
              *, retry_failed: bool = False, skip_completed: bool = True) -> bool:
        fingerprint = config.fingerprint()
        row = self.connection.execute(
            "SELECT status, attempts FROM checkpoints WHERE config_fingerprint=? AND source_id=?",
            (fingerprint, source_id)).fetchone()
        if row and row[0] == "completed" and skip_completed:
            return False
        if row and row[0] == "failed" and not retry_failed:
            return False
        now = datetime.now(timezone.utc).isoformat()
        if row:
            self.connection.execute(
                "UPDATE checkpoints SET run_id=?, status='running', attempts=?, updated_at=?, error=NULL "
                "WHERE config_fingerprint=? AND source_id=?",
                (run_id, row[1] + 1, now, fingerprint, source_id))
        else:
            self.connection.execute("INSERT INTO checkpoints VALUES (?,?,?,?,?,?,?)",
                (fingerprint, source_id, run_id, "running", 1, now, None))
        self.connection.commit()
        return True

    def checkpoint(self, config: EffectiveRunConfig, run_id: str, source_id: str,
                   status: str = "completed", error: str | None = None) -> None:
        self.connection.execute(
            "UPDATE checkpoints SET run_id=?, status=?, updated_at=?, error=? "
            "WHERE config_fingerprint=? AND source_id=?",
            (run_id, status, datetime.now(timezone.utc).isoformat(), error,
             config.fingerprint(), source_id))
        self.connection.commit()


class ExecutionCoordinator:
    """All backends end here and call the same pipeline function."""
    def __init__(self, config: EffectiveRunConfig, store: RunStore,
                 pipeline: Callable[[EffectiveRunConfig, Run, RunStore], Any],
                 pipeline_version: str = "2.0.0", parent_run_id: str | None = None):
        self.config, self.store, self.pipeline = config, store, pipeline
        self.pipeline_version = pipeline_version
        self.parent_run_id = parent_run_id

    def execute(self, parent_run_id: str | None = None):
        run = self.store.create_run(self.config, self.pipeline_version,
                                    parent_run_id or self.parent_run_id)
        try:
            result = self.pipeline(self.config, run, self.store)
        except Exception:
            self.store.finish_run(run, "failed")
            raise
        return self.store.finish_run(run, "completed"), result

    def process_items(self, run: Run, items: Iterable[Any], analyzer: Callable[[Any, str], Any]):
        policy = self.config.orchestration.get("runtime", {})
        results = []
        for item in items:
            source_id = getattr(item, "source_id", None) or item["source_id"]
            if not self.store.claim(self.config, run.run_id, source_id,
                    retry_failed=policy.get("retry_failed_items", False),
                    skip_completed=policy.get("skip_already_processed", True)):
                continue
            try:
                result = analyzer(item, run.run_id)
                results.append(_attach_run_id(result, run.run_id))
                self.store.checkpoint(self.config, run.run_id, source_id)
            except Exception as exc:
                self.store.checkpoint(self.config, run.run_id, source_id, "failed", str(exc))
                if not policy.get("retry_failed_items", False):
                    raise
        return results


def _attach_run_id(result: Any, run_id: str) -> Any:
    """Attach lineage recursively to model/dict/list analysis outputs."""
    if isinstance(result, BaseModel):
        if "run_id" not in type(result).model_fields:
            raise TypeError(f"analysis result {type(result).__name__} has no run_id field")
        return result.model_copy(update={"run_id": run_id})
    if isinstance(result, list):
        return [_attach_run_id(value, run_id) for value in result]
    if isinstance(result, tuple):
        return tuple(_attach_run_id(value, run_id) for value in result)
    if isinstance(result, dict):
        return {**result, "run_id": run_id}
    raise TypeError("analysis results must be Pydantic models, mappings, or sequences")
