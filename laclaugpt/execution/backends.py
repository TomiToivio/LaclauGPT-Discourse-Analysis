"""Execution adapters. None implements analysis; all dispatch one coordinator."""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Protocol

from .core import ExecutionCoordinator


class ExecutionBackend(Protocol):
    def run(self, coordinator: ExecutionCoordinator): ...


class CLIExecutionBackend:
    def run(self, coordinator: ExecutionCoordinator):
        return coordinator.execute()


class AgentExecutionBackend(CLIExecutionBackend):
    """Agent calls exactly the same coordinator as a human CLI invocation."""


class ManualExecutionBackend(CLIExecutionBackend):
    pass


class CronExecutionBackend(CLIExecutionBackend):
    def cron_entry(self, coordinator: ExecutionCoordinator) -> str:
        schedule = coordinator.config.orchestration.get("schedule", "0 */6 * * *")
        command = _command(coordinator, "cron")
        return f"{schedule} {command}"


class SlurmExecutionBackend:
    def render_script(self, coordinator: ExecutionCoordinator) -> str:
        resources = coordinator.config.orchestration.get("resources", {})
        directives = {
            "partition": resources.get("partition"), "time": resources.get("time"),
            "cpus-per-task": resources.get("cpus"), "mem": resources.get("memory"),
            "gpus": resources.get("gpus"),
        }
        lines = ["#!/bin/bash", "set -euo pipefail"]
        lines[1:1] = [f"#SBATCH --{key}={value}" for key, value in directives.items()
                      if value is not None]
        lines.append(_command(coordinator, "slurm"))
        return "\n".join(lines) + "\n"

    def write_script(self, coordinator: ExecutionCoordinator, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render_script(coordinator), encoding="utf-8", newline="\n")
        return path

    def run(self, coordinator: ExecutionCoordinator):
        # Inside an allocated job, execute directly. Outside it, script
        # generation/submission is an explicit orchestration action.
        if __import__("os").getenv("SLURM_JOB_ID"):
            return coordinator.execute()
        return self.render_script(coordinator)

    def submit(self, coordinator: ExecutionCoordinator, path: str | Path):
        script = self.write_script(coordinator, path)
        return subprocess.run(["sbatch", str(script)], check=True,
                              capture_output=True, text=True)


def _command(coordinator: ExecutionCoordinator, execution: str) -> str:
    c = coordinator.config
    parts = ["laclaugpt", "run",
             "--project", c.project, "--machine", c.machine,
             "--execution", execution, "--inside-scheduler"]
    if c.arena:
        parts.extend(["--arena", c.arena])
    if coordinator.parent_run_id:
        parts.extend(["--parent-run-id", coordinator.parent_run_id])
    if c.dataset.get("input"):
        parts.extend(["--dataset", c.dataset["input"]])
    if c.dataset.get("output"):
        parts.extend(["--output", c.dataset["output"]])
    if c.dataset.get("run_config"):
        parts.extend(["--pipeline-config", c.dataset["run_config"]])
    return " ".join(shlex.quote(str(part)) for part in parts)


def execution_backend(name: str) -> ExecutionBackend:
    try:
        return {"cli": CLIExecutionBackend, "agent": AgentExecutionBackend,
                "manual": ManualExecutionBackend, "cron": CronExecutionBackend,
                "slurm": SlurmExecutionBackend}[name]()
    except KeyError as exc:
        raise KeyError(f"unknown execution backend: {name}") from exc
