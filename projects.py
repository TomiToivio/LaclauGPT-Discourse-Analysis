# -*- coding: utf-8 -*-
"""Compatibility project presets for the current paper pipeline.

The canonical package configuration lives under ``config/``:

    config/projects/<project>.yaml
    config/machines/<machine>.yaml
    config/execution/<execution>.yaml

The lower-level paper pipeline still uses arena-specific YAML files under
``run_configs/arena_*.yaml``.  This module provides a small compatibility preset
for utilities that still expect Python project metadata.  It does not replace
the canonical CLI configuration chain.

A project preset answers: WHAT topic/background is used, WHICH codebook seeds
apply, and WHERE project-scoped Context Memory lives.  Data, memory and seeds
must not auto-mix across projects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECTS_DIR = Path(__file__).resolve().parent / "config" / "projects"


@dataclass(frozen=True)
class ProjectPreset:
    """A named research project compatibility preset."""
    name: str                       # ai26
    topic_key: str                  # key into prompts.topic_background.REGISTRY
    title: str
    default_sources: list[dict[str, str]]   # platform/country/language/query
    seed_signifiers: list[str] = field(default_factory=list)
    seed_actors: list[str] = field(default_factory=list)
    seed_formations: list[str] = field(default_factory=list)
    languages: tuple[str, ...] = ()
    memory_subdir: str = ""         # memory/<name>/, project-scoped state
    notes: str = ""

    def memory_dir(self, base: Path | None = None) -> Path:
        base = base or Path("./data/memory")
        return base / (self.memory_subdir or self.name)


PROJECTS: dict[str, ProjectPreset] = {
    "ai26": ProjectPreset(
        name="ai26",
        topic_key="ai-contestation",
        title="Ideological contestation over AI (paper project, 3 arenas)",
        default_sources=[
            {"platform": "web", "country": "us", "language": "en",
             "query": "elite blogs / substacks / forums (Goertzel round)"},
            {"platform": "tiktok", "country": "fi", "language": "fi",
             "query": "grassroots: data centres, jobs, surveillance"},
            {"platform": "x", "country": "eu", "language": "en",
             "query": "elite + grassroots X discourse"},
        ],
        seed_signifiers=[
            "artificial intelligence", "existential risk", "abundance",
            "stagnation", "innovation", "data centre", "job displacement",
        ],
        seed_actors=[
            "Machine Intelligence Research Institute",
            "Distributed AI Research Institute",
            "Effective Accelerationism", "PauseAI",
        ],
        seed_formations=[
            "accelerationism", "x-risk doomerism", "critical ai studies",
            "TESCREAL", "left techno-optimism", "anti-ai backlash",
        ],
        languages=("en", "fi"),
        memory_subdir="ai26",
        notes="Arena runs live in run_configs/arena_*.yaml "
              "(elites/grassroots/parliamentary). This preset is the "
              "compatibility project umbrella for topic_key, seeds and memory "
              "scope. No publication deadline is encoded here.",
    ),
}


def get_project(name: str) -> ProjectPreset:
    if name not in PROJECTS:
        raise KeyError(f"unknown project: {name!r} (known: {sorted(PROJECTS)})")
    return PROJECTS[name]


def project_yaml_path(name: str) -> Path:
    """Return the canonical package YAML path for ``name``."""
    return PROJECTS_DIR / f"{name}.yaml"


def list_projects() -> list[str]:
    return sorted(PROJECTS)
