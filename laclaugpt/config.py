"""Canonical project -> arena -> machine -> execution configuration chain."""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "config"
PROJECT_DIR = CONFIG_ROOT / "projects"
ARENA_DIR = CONFIG_ROOT / "arenas"
MACHINE_DIR = CONFIG_ROOT / "machines"
EXECUTION_DIR = CONFIG_ROOT / "execution"

MODULES = {
    "laclau", "palonen", "sociotechnical_imaginaries", "sentiment",
    "topics", "entities", "context_memory", "sna", "ant", "valueflows",
    "temporal", "multimodal",
}

LEGACY_ARENA_NAMES = {
    "arena_elites": "elites",
    "arena_grassroots": "grassroots",
    "arena_parliamentary": "parliamentary",
    "arena-elites": "elites",
    "arena-grassroots": "grassroots",
    "arena-parliamentary": "parliamentary",
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
    # The project profile is the sole source of truth for analysis-module
    # switches. Missing modules are explicit false values, never hidden defaults.
    data["analysis"] = {
        module: bool(data.get("analysis", {}).get(module, False))
        for module in sorted(MODULES)
    }
    return data


def load_arena(name: str, project: str | None = None) -> dict[str, Any]:
    data = _load(ARENA_DIR, name, "arena")
    owner = str(data.get("project") or "")
    if not owner:
        raise ValueError(f"arena {name!r} must declare its project")
    if project is not None and owner != project:
        raise ValueError(f"arena {name!r} belongs to project {owner!r}, not {project!r}")
    if "analysis" in data:
        raise ValueError("arena profiles must not redefine project analysis modules")
    return data


def load_machine(name: str) -> dict[str, Any]:
    return _load(MACHINE_DIR, name, "machine")


def load_execution(name: str) -> dict[str, Any]:
    data = _load(EXECUTION_DIR, name, "execution")
    if "analysis" in data or "backends" in data or "dataset" in data:
        raise ValueError(
            "execution profiles must not contain research, dataset or backend settings"
        )
    return data


def compose_config(project: str, machine: str, execution: str = "cli",
                   overrides: dict[str, Any] | None = None, *,
                   arena: str | None = None) -> dict[str, Any]:
    """Compose the canonical research/infrastructure execution configuration.

    Layer ownership is deliberate:
    - project: theory/codebook and authoritative analysis-module switches;
    - arena: dataset/source metadata, analytic hints, model options and data policy;
    - machine: service/backend/runtime infrastructure;
    - execution: scheduler/retry/checkpoint orchestration;
    - overrides: execution-instance dataset values such as input/output only.
    """
    research = load_project(project)
    arena_profile = load_arena(arena, project) if arena else {}
    infrastructure = load_machine(machine)
    orchestration = load_execution(execution)
    if "analysis" in infrastructure:
        raise ValueError("machine profiles must not contain analysis settings")

    dataset = copy.deepcopy(research.get("dataset", {}))
    if arena_profile:
        _deep_update(dataset, copy.deepcopy(arena_profile.get("dataset", {})))

    analysis_profile = f"{project}:{arena}" if arena else project
    if arena:
        dataset["arena_id"] = arena
        dataset["analysis_profile"] = analysis_profile

    effective = {
        "project": project,
        "arena": arena or "",
        "analysis_profile": analysis_profile,
        "machine": machine,
        "execution": execution,
        "analysis": copy.deepcopy(research["analysis"]),
        "dataset": dataset,
        "codebook": copy.deepcopy(research.get("codebook", {})),
        "backends": copy.deepcopy(infrastructure.get("backends", {})),
        "services": copy.deepcopy(infrastructure.get("services", {})),
        "runtime": copy.deepcopy(infrastructure.get("runtime", {})),
        "orchestration": {
            key: copy.deepcopy(value) for key, value in orchestration.items()
            if key != "execution"
        },
    }
    if overrides:
        forbidden = set(overrides) & {
            "project", "arena", "analysis_profile", "machine", "execution", "analysis"
        }
        if forbidden:
            raise ValueError(
                "runtime overrides cannot replace configuration-layer identity or "
                f"analysis switches: {sorted(forbidden)}"
            )
        _deep_update(effective, overrides)

    # Reassert immutable layer identities after composition.
    effective["project"] = project
    effective["arena"] = arena or ""
    effective["analysis_profile"] = analysis_profile
    effective["machine"] = machine
    effective["execution"] = execution
    effective["analysis"] = copy.deepcopy(research["analysis"])
    return effective


def arena_from_legacy_config(path: str | Path) -> str:
    """Map the three historical run_configs/arena_*.yaml files to arena IDs."""
    stem = Path(path).stem
    arena = LEGACY_ARENA_NAMES.get(stem)
    if arena is None:
        raise ValueError(
            f"{path!s} is not one of the migrated AI arena configs; use --arena"
        )
    return arena


def _deep_update(target: dict[str, Any], changes: dict[str, Any]) -> None:
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def list_projects() -> list[str]:
    return sorted(p.stem for p in PROJECT_DIR.glob("*.yaml"))


def list_arenas(project: str | None = None) -> list[str]:
    arenas = []
    for path in ARENA_DIR.glob("*.yaml"):
        if project is None:
            arenas.append(path.stem)
            continue
        try:
            if load_arena(path.stem).get("project") == project:
                arenas.append(path.stem)
        except (KeyError, ValueError):
            continue
    return sorted(arenas)


def list_machines() -> list[str]:
    return sorted(p.stem for p in MACHINE_DIR.glob("*.yaml"))


def list_executions() -> list[str]:
    return sorted(p.stem for p in EXECUTION_DIR.glob("*.yaml"))
