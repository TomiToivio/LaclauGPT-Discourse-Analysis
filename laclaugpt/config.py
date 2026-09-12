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
SOURCE_FAMILY_DIR = CONFIG_ROOT / "source-families"

MODULES = {
    "laclau", "palonen", "sociotechnical_imaginaries", "sentiment",
    "topics", "entities", "context_memory", "sna", "ant", "valueflows",
    "temporal", "multimodal",
}

# Declarative source-family registry fields. A family entry describes a
# candidate source category and its boundaries; it never enables collection.
SOURCE_FAMILY_REQUIRED_FIELDS = (
    "family", "project", "category", "label", "status", "default_enabled",
    "research_target", "motifs", "must_not_absorb", "candidate_targets",
    "provenance_fields", "literature",
)
SOURCE_FAMILY_STATUSES = {"exploratory", "established"}

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


def load_source_family(name: str) -> dict[str, Any]:
    """Load and validate one declarative source-family entry.

    A source family describes a *candidate* category: what it means, what it
    must not absorb, which public collection targets are proposed and which
    literature anchors it. It never turns collection on: ``default_enabled``
    is part of the validated payload and defaults to false.
    """
    path = SOURCE_FAMILY_DIR / f"{name}.yaml"
    if not path.exists():
        raise KeyError(f"unknown source family: {name}")
    data = yaml.safe_load(os.path.expandvars(path.read_text(encoding="utf-8"))) or {}
    missing = [field for field in SOURCE_FAMILY_REQUIRED_FIELDS if field not in data]
    if missing:
        raise ValueError(f"{path}: missing source-family fields: {missing}")
    if data.get("family") != name:
        raise ValueError(f"{path}: expected family: {name}")
    if data.get("status") not in SOURCE_FAMILY_STATUSES:
        raise ValueError(
            f"{path}: status must be one of {sorted(SOURCE_FAMILY_STATUSES)}"
        )
    if not isinstance(data.get("default_enabled"), bool):
        raise ValueError(f"{path}: default_enabled must be a boolean")
    if not isinstance(data.get("candidate_targets"), dict) or not data["candidate_targets"]:
        raise ValueError(f"{path}: candidate_targets must be a non-empty mapping")
    if not isinstance(data.get("literature"), list) or not data["literature"]:
        raise ValueError(f"{path}: literature must be a non-empty list")
    return data


def list_source_families(project: str | None = None) -> list[str]:
    families = []
    for path in SOURCE_FAMILY_DIR.glob("*.yaml"):
        try:
            data = load_source_family(path.stem)
        except (KeyError, ValueError):
            continue
        if project is None or data.get("project") == project:
            families.append(path.stem)
    return sorted(families)


def source_family_default_state(name: str) -> bool:
    """Return the declared default collection state (False unless opted in)."""
    return bool(load_source_family(name)["default_enabled"])


def source_family_status(project: str | None = None) -> dict[str, dict[str, Any]]:
    """Compact, non-secret status of the declarative source families.

    Reports the declared default state only; live operational opt-in belongs to
    private configuration and is never published.
    """
    return {
        name: {
            "project": load_source_family(name)["project"],
            "category": load_source_family(name)["category"],
            "status": load_source_family(name)["status"],
            "default_enabled": source_family_default_state(name),
        }
        for name in list_source_families(project)
    }


def list_executions() -> list[str]:
    return sorted(p.stem for p in EXECUTION_DIR.glob("*.yaml"))
