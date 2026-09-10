"""Audited, policy-preserving tools for optional Hermes orchestration.

No Hermes SDK is imported here.  The wrapper deliberately exposes only a
small allowlist of canonical LaclauGPT operations and never accepts arbitrary
CLI arguments, environment overrides, model-routing flags, repository writes,
or shell commands.  Agent-triggered runs are additionally restricted to
local Ollama open-source models (see
``laclaugpt.integrations.agent_policy``); the Claude Code integration
(``laclaugpt.integrations.claude``) reuses this wrapper with a different
audit actor.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from laclaugpt.cli import main as cli_main
from laclaugpt.config import compose_config, list_arenas, list_executions, list_machines, list_projects
from laclaugpt.execution import EffectiveRunConfig
from laclaugpt.integrations.agent_policy import enforce_local_ollama_policy


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class HermesAuditLog:
    """Append-only JSONL audit trail for agent-triggered actions."""

    path: Path
    actor: str = "hermes-agent"

    def append(self, action: str, status: str, details: dict[str, Any] | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": _utc_now(),
            "actor": self.actor,
            "action": action,
            "status": status,
            "details": details or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


class HermesTools:
    """Small, safe tool surface for Hermes or another external agent.

    The integration is intentionally narrower than the CLI.  It cannot mutate
    repository files, publish results, delete data, inject arbitrary env vars,
    or override LLM routing/data-governance policy.  Execution is always the
    canonical ``agent`` backend so provenance identifies the caller, and every
    run is routed to local Ollama open-source models only (no Ollama cloud,
    external endpoints or cloud fallback).
    """

    def __init__(
        self,
        audit_log: str | Path = "data/audit/hermes-actions.jsonl",
        *,
        actor: str = "hermes-agent",
        cli: Callable[[list[str] | None], int] = cli_main,
    ) -> None:
        self.audit = HermesAuditLog(Path(audit_log), actor=actor)
        self._cli = cli

    def profiles(self) -> dict[str, list[str]]:
        result = {
            "projects": list_projects(),
            "arenas": list_arenas(),
            "machines": list_machines(),
            "executions": list_executions(),
        }
        self.audit.append("profiles", "ok", result)
        return result

    def validate_run(
        self,
        *,
        project: str,
        arena: str,
        machine: str,
        dataset: str | None = None,
    ) -> dict[str, Any]:
        """Compose and validate an agent run without executing it.

        Only dataset input may be overridden.  In particular, callers cannot
        use this API to change Ollama mode, endpoints, fallback permissions,
        credentials, or other data-governance settings, and the run must be
        routed to local Ollama open-source models only.
        """
        try:
            enforce_local_ollama_policy()
        except PermissionError as exc:
            self.audit.append("model_policy", "rejected", {"error": str(exc)})
            raise
        overrides = {"dataset": {"input": dataset}} if dataset else None
        try:
            raw = compose_config(project, machine, "agent", overrides, arena=arena)
            config = EffectiveRunConfig.model_validate(raw)
        except Exception as exc:
            self.audit.append(
                "validate_run",
                "rejected",
                {"project": project, "arena": arena, "machine": machine, "error": str(exc)},
            )
            raise
        payload = config.model_dump(mode="json")
        self.audit.append(
            "validate_run",
            "ok",
            {"project": project, "arena": arena, "machine": machine, "dataset": dataset or ""},
        )
        return payload

    def dry_run(
        self,
        *,
        project: str,
        arena: str,
        machine: str,
        dataset: str | None = None,
    ) -> int:
        """Invoke the canonical CLI's validation path as execution=agent."""
        self.validate_run(project=project, arena=arena, machine=machine, dataset=dataset)
        argv = [
            "analyze",
            *( [dataset] if dataset else [] ),
            "--project", project,
            "--arena", arena,
            "--machine", machine,
            "--execution", "agent",
            "--show-config",
        ]
        self.audit.append("dry_run", "started", {"argv": argv})
        try:
            code = self._cli(argv)
        except Exception as exc:
            self.audit.append("dry_run", "failed", {"error": str(exc)})
            raise
        self.audit.append("dry_run", "ok", {"exit_code": code})
        return code

    def run_analysis(
        self,
        *,
        project: str,
        arena: str,
        machine: str,
        dataset: str,
        parent_run_id: str | None = None,
    ) -> int:
        """Launch one canonical LaclauGPT analysis run through the agent backend."""
        self.validate_run(project=project, arena=arena, machine=machine, dataset=dataset)
        argv = [
            "run",
            "--project", project,
            "--arena", arena,
            "--machine", machine,
            "--execution", "agent",
            "--dataset", dataset,
        ]
        if parent_run_id:
            argv.extend(["--parent-run-id", parent_run_id])
        self.audit.append("run_analysis", "started", {"argv": argv})
        try:
            code = self._cli(argv)
        except Exception as exc:
            self.audit.append("run_analysis", "failed", {"error": str(exc)})
            raise
        self.audit.append("run_analysis", "ok", {"exit_code": code})
        return code

    def request_destructive_action(self, action: str) -> None:
        """Explicitly reject destructive/repository-changing actions.

        Hermes may propose such an action conversationally, but this integration
        never executes it.  A human must perform it through an appropriate,
        separately authorised interface.
        """
        self.audit.append("destructive_action", "rejected", {"requested_action": action})
        raise PermissionError(
            "Hermes integration does not execute destructive, publishing, or repository-changing actions"
        )
