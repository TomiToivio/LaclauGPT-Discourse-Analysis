# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

LaclauGPT is an LLM-assisted discourse-analysis pipeline applying Laclau/Mouffe/Palonen theory to text corpora. This is the sanitized public core: **no research data, no secrets** — raw captures, run outputs and data roots (`laclaugpt-brasil-data/`, `collection-data/`, `*.har`) are never committed, and endpoints/credentials come from environment variables only.

## Commands

```bash
python -m pip install -e ".[collector,test]"   # exact CI install
python -m pytest -q tests                      # full offline suite (no LLM/GPU/network calls)
python -m pytest -q tests/test_pipeline_failure_cleanup.py -k name   # single test
LACLAUGPT_EMBED_BACKEND=none python -m pytest -q tests               # CI sets this env var

python -m laclaugpt.cli profiles               # list projects/arenas/machines/executions
python -m laclaugpt.cli analyze my_corpus.csv \
  --project ai26 --arena elites --machine roihu --execution cli --show-config
laclaugpt dashboard data/annotations.jsonl --project ai26 --arena elites
```

The test suite is fully offline; mocked end-to-end tests run real pipeline I/O with only model calls replaced. CI (`.github/workflows/ci.yml`) additionally runs `compileall` over the shipped Python surface and CLI smoke tests — run those before pushing a broad refactor.

## Theory contract (read before theory-facing changes)

[`THEORY.md`](THEORY.md) is the canonical theory/methodology contract. Before changing prompts, schemas, discourse-analysis logic, Context Memory behaviour, visualizations or theory-facing docs: read it in full, treat its concept registry (§14) and invariants (§15) as normative (e.g. `INV_EVIDENCE` — coding must preserve source evidence; `INV_ABSTAIN` — abstention beats forced coding; `INV_POPULISM` — populist=true requires evidenced Us + Frontier; `INV_HUMAN_REVIEW` — LLM output stays provisional/rejectable), and report theory–implementation mismatches explicitly rather than silently normalizing them. The original sources (Laclau 2005; Laclau & Mouffe 2001; Palonen 2025) outrank THEORY.md when they conflict.

Key modeling stance: Laclaudian concepts are **roles supported by evidence**, not ontology types — do not add schema/ontology types just because a theoretical term exists; NLP features (NER, sentiment, embeddings) stay analytically subordinate to discourse-theoretical interpretation.

## Architecture

Canonical domain-model import paths for all new code:

```python
from laclaugpt.model import SourceItem, Statement, Concept, Articulation
from laclaugpt.memory import Memory, MemoryRef, ContextBuilder
```

- **Configuration chain** (single runtime authority): `config/projects/` → `config/arenas/` → `config/machines/` → `config/execution/`. Projects own analysis-module switches; arenas own dataset/source metadata and data-boundary policy; machines own infrastructure; executions own scheduler/retry/checkpoint policy. Composed into an `EffectiveRunConfig`. See `docs/CANONICAL_CONFIGURATION.md`.
- **Orchestration**: `laclaugpt/canonical_pipeline.py` + `laclaugpt/execution/` dispatch to root `pipeline.py` (the current evidence-linked analysis implementation) through `run_config.py`, which adapts `EffectiveRunConfig` for the pipeline and also loads legacy/custom YAML. `run_config.py` is an adapter, not a second configuration authority.
- **Memory layering**: `laclaugpt/memory/` is the public facade; persistent stable-ID codebook/entity resolution lives in `laclaugpt_memory/` (SQLite), and `laclaugpt/memory/context.py` does repository-aware context orchestration. New callers never pick between memory generations. Root `memory.py` is a warning-emitting legacy shim.
- **Interchange**: `laclaugpt_interchange/` is the JSONL/Pydantic batch-exchange pivot; the version lives in `laclaugpt_interchange.SCHEMA_VERSION` — never hard-code it. Current interchange enters the canonical model via `laclaugpt.adapters.interchange.interchange_to_v2()`.
- **Frozen layers** (bug fixes only, no new features, no new dependencies from new code): `laclaugpt_model/` (older model generation, emits deprecation warning) and `run_configs/arena_*.yaml` (deprecated aliases for canonical arena profiles, still accepted via `--pipeline-config`).
- **Entry points**: `laclaugpt.cli` is canonical (`laclaugpt` console script equivalent); `laclaugpt_processor.py` is the shipped 4CAT processor delegating analysis to the same canonical execution path; `laclaugpt/visualization/` is an optional Streamlit dashboard driven by project analysis-module switches — local/Pouta only, it rejects Roihu markers and Slurm allocations.
- **Agents as callers**: agent-triggered runs must go through the CLI with `--execution agent` so provenance records the caller; never reimplement pipeline stages or bypass config validation. See `HERMES.md` / `docs/HERMES_INTEGRATION.md` for Hermes and `docs/CLAUDE_INTEGRATION.md` for Claude Code.

## Claude Code agent boundary (this file is the Claude project context)

Claude Code is a participant **caller** of this pipeline, exactly like the
Hermes integration: trigger analyses only through the canonical CLI with
`--execution agent`, never reimplement pipeline stages or bypass config
validation. An audited tool surface (`laclaugpt.integrations.claude`,
reusing the Hermes wrapper with a `claude-code` audit actor) is available for
tool-driven runs.

**Model routing**: both Hermes and Claude Code use **only local Ollama
open-source models** — agent-triggered runs require `LLM_MODE=local`;
Ollama cloud, external endpoints, auto routing and cloud fallback are refused
by `laclaugpt.integrations.agent_policy`. Human CLI invocations keep the full
machine-tier routing.

LaclauGPT output stays preliminary and human-reviewed; never present model
coding as a final scholarly finding.

Analysis chain per document: prepare → describe → propose theoretical codes (with exact evidence quotes, uncertainty, counter-evidence, explicit abstention) → resolve entities via Context Memory → corpus comparison → human review.

## Docs status

`docs/INTEROPERABILITY_SPEC.md` is a design spec — QDPX/REFI-QDA targets (ATLAS.ti, MAXQDA, NVivo, QualCoder) are targets, not shipped adapters. `docs/PAPER_IMPLEMENTATION_AUDIT.md` records what the code actually implements.