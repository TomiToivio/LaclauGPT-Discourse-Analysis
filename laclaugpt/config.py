"""Strict composition of research and infrastructure configuration layers."""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "config"
PROJECT_DIR = CONFIG_ROOT / "projects"
MACHINE_DIR = CONFIG_ROOT / "machines"
EXECUTION_DIR = CONFIG_ROOT / "execution"

MODULES = {
    "laclau", "palonen", "sociotechnical_imaginaries", "sentiment",
    "topics", "entities", "context_memory", "sna", "ant", "valueflows",
    "temporal", "multimodal",
}


def _load(directory: Path, name: str, identity_key: str) -> dict[str, Any]:
    path = directory / f"{name}.yaml"
    if not path.exists():
        raise KeyError(f"unknown {identity_key}: {name}")
    data = yaml.safe_load(os.path.expandvars(path.read_text(encoding="utf-8"))) or {}
    if data.get(identity_key) != name:
        raise ValueError(f"{path}: expected {identity_key}: {name}")
    return data


def load_project(name: str) -> dict[str, Any]:
    data = _load(PROJECT_DIR, name, "project")
    unknown = set(data.get("analysis", {})) - MODULES
    if unknown:
        raise ValueError(f"unknown analysis modules in project {name}: {sorted(unknown)}")
    # No module inherits a hidden global default.
    data["analysis"] = {module: bool(data.get("analysis", {}).get(module, False))
                        for module in sorted(MODULES)}
    return data


def load_machine(name: str) -> dict[str, Any]:
    return _load(MACHINE_DIR, name, "machine")


def load_execution(name: str) -> dict[str, Any]:
    data = _load(EXECUTION_DIR, name, "execution")
    if "analysis" in data or "backends" in data:
        raise ValueError("execution profiles must not contain research or backend settings")
    return data


def compose_config(project: str, machine: str, execution: str = "cli",
                   overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compose without allowing a machine profile to select research theory."""
    research = load_project(project)
    infrastructure = load_machine(machine)
    orchestration = load_execution(execution)
    if "analysis" in infrastructure:
        raise ValueError("machine profiles must not contain analysis settings")
    effective = {"project": project, "machine": machine, "execution": execution,
                 "analysis": copy.deepcopy(research["analysis"]),
                 "dataset": copy.deepcopy(research.get("dataset", {})),
                 "codebook": copy.deepcopy(research.get("codebook", {})),
                 "backends": copy.deepcopy(infrastructure.get("backends", {})),
                 "services": copy.deepcopy(infrastructure.get("services", {})),
                 "runtime": copy.deepcopy(infrastructure.get("runtime", {})),
                 "orchestration": {k: copy.deepcopy(v) for k, v in orchestration.items()
                                   if k != "execution"}}
    if overrides:
        _deep_update(effective, overrides)
    # Preserve the layer boundary after overrides as well.
    effective["project"] = project
    effective["machine"] = machine
    effective["execution"] = execution
    return effective


def _deep_update(target: dict[str, Any], changes: dict[str, Any]) -> None:
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def list_projects() -> list[str]:
    return sorted(p.stem for p in PROJECT_DIR.glob("*.yaml"))


def list_machines() -> list[str]:
    return sorted(p.stem for p in MACHINE_DIR.glob("*.yaml"))


def list_executions() -> list[str]:
    return sorted(p.stem for p in EXECUTION_DIR.glob("*.yaml"))
