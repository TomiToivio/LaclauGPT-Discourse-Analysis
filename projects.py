# -*- coding: utf-8 -*-
"""Project presets: one self-contained configuration set per research project.

Maintainer ruling (2026-09-06): no monolithic settings — each project
(ai26) gets its OWN run configs, prompt
backgrounds, codebook seeds and storage defaults, selected explicitly.
Nothing auto-mixes across projects: data, memory and seeds are
project-scoped.

Layout:

    run_configs/
      projects/<project>.yaml      the project preset (this module's source)
      arena_*.yaml                 paper-arena runs (AI project)
    prompts/topic_background.py    REGISTRY of project backgrounds

A project preset answers: WHAT is collected (topic background), WHERE
data comes from (sources), WHICH codebook seeds apply, and WHERE state
lives (memory_dir per project — never shared between projects).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECTS_DIR = Path(__file__).resolve().parent / "run_configs" / "projects"


@dataclass(frozen=True)
class ProjectPreset:
    """A named research project with its own config surface."""
    name: str                       # ai26
    topic_key: str                  # key into prompts.topic_background.REGISTRY
    title: str
    default_sources: list[dict[str, str]]   # platform/country/language/query
    seed_signifiers: list[str] = field(default_factory=list)
    seed_actors: list[str] = field(default_factory=list)
    seed_formations: list[str] = field(default_factory=list)
    languages: tuple[str, ...] = ()
    memory_subdir: str = ""         # memory/<name>/ — project-scoped state
    notes: str = ""

    def memory_dir(self, base: Path | None = None) -> Path:
        base = base or Path("./data/memory")
        return base / (self.memory_subdir or self.name)


# ── the four projects ────────────────────────────────────────────────

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
        notes="Paper 1 locks 2026-09-07. Arena runs: run_configs/arena_*.yaml "
              "(elites/grassroots/parliamentary) stay the arena-level specs; "
              "this preset is the project-level umbrella (topic_key + seeds + "
              "memory scope).",
    ),
}


def get_project(name: str) -> ProjectPreset:
    if name not in PROJECTS:
        raise KeyError(f"unknown project: {name!r} (known: {sorted(PROJECTS)})")
    return PROJECTS[name]


def project_yaml_path(name: str) -> Path:
    """Per-project YAML overrides live in run_configs/projects/<name>.yaml;
    optional — the preset above is the fallback."""
    return PROJECTS_DIR / f"{name}.yaml"


def list_projects() -> list[str]:
    return sorted(PROJECTS)