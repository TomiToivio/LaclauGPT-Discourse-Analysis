# -*- coding: utf-8 -*-
"""Context/memory profiles for the analysis pipeline (issue #140).

A profile is a declarative description of what every analysis stage sees as
context. Profiles are configuration, not code: switching from the default
balanced policy to a fast/local or high-accuracy/Roihu policy must never
require pipeline edits. Each profile defines:

- ``context_memory`` — whether the SQLite entity/topic memory is consulted;
- ``glossary_top_k`` — how many retrieved glossary candidates per kind are
  injected (retrieval depth);
- ``inject_codebook`` — whether the human-curated codebook block is injected
  into every theory-facing prompt (mandatory at these stages);
- ``inject_previous_batch_summary`` — structured previous-batch/daily state as
  situational context (opt-in; validated against anchoring-bias benchmarks
  before production use);
- ``inject_corpus_stats`` — corpus-level counts (documents, formations) as
  descriptive context;
- ``truncation_limits`` — per-stage character caps for prompt blocks;
- ``provenance`` — whether each prompt's injected context is logged
  (context fingerprint) for reproducibility.

Every field is introspectable, so a run's effective profile can be printed
and stored with the run artifacts (reproducibility requirement from the
issue: "context provenance is recorded sufficiently for reproducibility").

The module is pure data + validation: it never performs LLM calls and never
reads network resources, so profiles can be unit-tested deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml

PROFILES_DIR = Path(__file__).resolve().parent / "profiles"

PROFILE_NAMES = ("fast_local", "balanced", "high_accuracy", "validation")


@dataclass
class ContextProfile:
    """Declarative context/memory policy for one analysis run."""

    name: str
    description: str = ""
    # Context memory (glossary retrieval)
    context_memory: bool = True
    glossary_top_k: int = 5
    # Codebook injection
    inject_codebook: bool = True
    codebook_required_stages: tuple[str, ...] = ("summary", "discourse", "populism")
    # Situational state
    inject_previous_batch_summary: bool = False
    inject_corpus_stats: bool = False
    # Prompt hygiene
    max_context_chars: int = 6000
    max_transcript_chars: int = 12000
    # Reproducibility
    context_provenance: bool = True
    # Optional retrieval add-on (v2, benchmark-gated — off by default)
    vector_rag: bool = False

    def resolved(self) -> "ContextProfile":
        """Return a normalised copy (bounds checked)."""
        clone = ContextProfile(**asdict(self))
        clone.glossary_top_k = max(0, min(int(clone.glossary_top_k), 20))
        clone.max_context_chars = max(200, int(clone.max_context_chars))
        clone.max_transcript_chars = max(500, int(clone.max_transcript_chars))
        return clone

    def to_dict(self) -> dict:
        return asdict(self)


# ── Bundled profiles ─────────────────────────────────────────────────

_BUNDLED: dict[str, ContextProfile] = {
    "fast_local": ContextProfile(
        name="fast_local",
        description=("Interactive development and pilot samples: minimal "
                     "retrieval, no situational state, small context budget."),
        context_memory=True,
        glossary_top_k=3,
        inject_codebook=True,
        inject_previous_batch_summary=False,
        inject_corpus_stats=False,
        max_context_chars=2000,
        max_transcript_chars=4000,
        context_provenance=False,
    ),
    "balanced": ContextProfile(
        name="balanced",
        description=("Default production policy: glossary retrieval, "
                     "codebooks always injected, provenance recorded."),
        context_memory=True,
        glossary_top_k=5,
        inject_codebook=True,
        inject_previous_batch_summary=False,
        inject_corpus_stats=False,
        max_context_chars=6000,
        max_transcript_chars=12000,
        context_provenance=True,
    ),
    "high_accuracy": ContextProfile(
        name="high_accuracy",
        description=("Validation/research-run policy: deeper retrieval, corpus "
                     "statistics, previous batch state, generous truncation."),
        context_memory=True,
        glossary_top_k=8,
        inject_codebook=True,
        inject_previous_batch_summary=True,
        inject_corpus_stats=True,
        max_context_chars=12000,
        max_transcript_chars=20000,
        context_provenance=True,
    ),
    "validation": ContextProfile(
        name="validation",
        description=("Audit policy: deterministic context capture with full "
                     "provenance so memory on/off comparisons are possible."),
        context_memory=True,
        glossary_top_k=5,
        inject_codebook=True,
        inject_previous_batch_summary=True,
        inject_corpus_stats=True,
        max_context_chars=6000,
        max_transcript_chars=12000,
        context_provenance=True,
    ),
}


def load_profile(name: str) -> ContextProfile:
    """Resolve a profile by name: bundled first, then YAML overrides."""
    bundled = _BUNDLED.get(name)
    if bundled is not None:
        return bundled.resolved()
    path = PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        raise KeyError(
            f"unknown context profile: {name!r} (bundled: {sorted(_BUNDLED)})")
    import yaml
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw["name"] = str(raw.get("name") or name)
    return ContextProfile(**{k: v for k, v in raw.items()
                             if k in ContextProfile.__dataclass_fields__}).resolved()


def available_profiles() -> list[str]:
    return sorted(set(_BUNDLED) | {p.stem for p in PROFILES_DIR.glob("*.yaml")})


def apply_profile(run_config, profile: ContextProfile) -> None:
    """Apply a context profile onto a loaded RunConfig in place.

    Only context/memory knobs are touched: models, stages, evidence gates,
    and relevance handling remain the run YAML's authority (issue #140:
    switching context/memory policy must not change analytical config).
    """
    run_config.context_profile = profile.name
    run_config.context_memory_enabled = profile.context_memory
    run_config.glossary_top_k = profile.glossary_top_k
    run_config.inject_codebook = profile.inject_codebook
    run_config.max_context_chars = profile.max_context_chars
    run_config.max_transcript_chars = profile.max_transcript_chars
    run_config.context_provenance = profile.context_provenance