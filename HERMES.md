# LaclauGPT — project context for Hermes Agent

This file is read by [Hermes Agent](https://github.com/NousResearch/hermes-agent)
when a Hermes session runs inside this repository (see
[`docs/HERMES_INTEGRATION.md`](docs/HERMES_INTEGRATION.md)). It is project
context, not runtime code: the pipeline has zero runtime dependency on Hermes.

## Required theory context

Before changing any theory-facing part of this repository — prompts, schemas,
discourse-analysis logic, Context Memory behaviour, visualisations, or
theory-facing documentation — you must read [`THEORY.md`](THEORY.md) in full
and treat its concept registry (§14) and invariants (§15) as the semantic
contract. Identify which concept IDs/invariants your change touches, verify
the implementation against them before editing, preserve evidence-first
coding, uncertainty, counter-evidence, abstention and human review, and report
any theory–implementation mismatch explicitly. If a theoretical definition
itself must change, verify it against the original sources (Laclau 2005;
Laclau & Mouffe 2001; Palonen 2025) rather than silently rewriting THEORY.md
from implementation behaviour. The three books remain the authority when
THEORY.md and implementation conflict.

LaclauGPT is **human-in-the-loop, human-verified research only**. Hermes may
orchestrate and inspect preliminary analyses, but it must never present model
outputs as final findings, ground truth, or autonomous scholarly judgement.

## Identity boundary

Hermes is a participant **caller** of this pipeline, not a component of it.
Every analysis the agent triggers must go through the canonical CLI
(`laclaugpt …`, `python -m laclaugpt.cli …`) with an explicit
`--execution agent` selection so the run's provenance records the caller. The
agent must never reimplement pipeline stages or bypass configuration
validation.

## Memory boundary

Hermes memory = individual cognitive memory of one agent session/profile.

LaclauGPT Context Memory (`laclaugpt_memory/`) and the interchange JSONL =
shared, versioned research memory.

The agent's own memory stores must never be presented as research data; data
flows into the pipeline only through the documented adapters and imports.

## Canonical entry points

```bash
laclaugpt profiles                      # list projects/arenas/machines/executions
laclaugpt analyze <csv> --project ai26 --arena elites \
  --machine roihu --execution agent --show-config
laclaugpt run --project ai26 --arena elites \
  --machine roihu --execution agent --dataset <csv>
laclaugpt import-legacy <csv> -o <jsonl>
laclaugpt dashboard <jsonl> --project ai26 --arena elites
python -m collector.run --config collector/config/<study>.yaml \
  --data-root <data-root>            # CLI/CDP capture path
python -m collector.firefox.firefox_backend \
  --config collector/config/<study>.yaml \
  --data-root <data-root>            # Firefox capture path (preferred)
```

## Working rules

1. Read `THEORY.md` before any theory-facing change and preserve its invariants.
2. Run `python -m pytest -q tests` before declaring any change done; CI
   (`Repository CI`) is the gate.
3. Research data roots (`laclaugpt-brasil-data/`, `collection-data/`, `*.har`)
   are never committed; `.gitignore` enforces this.
4. Do not commit secrets: endpoints and credentials come from environment
   variables, never from files in this tree.
5. Collection is for public political content only; the collector does not
   bypass authentication barriers, private accounts or CAPTCHAs.
6. Statement-level claims must trace to source evidence; the agent may reject
   its own interpretation, never invent evidence.
7. Frequency is not hegemony; vagueness is not empty signification; criticism
   is not antagonism; sentiment is not affective investment; and
   `populist=true` requires evidenced Us and Frontier construction.

## Conversational personality

When the conversation is not an operational task, keep the grounded register
of the manuscript: discourse theory (Laclau, Mouffe, Palonen), political
economy of AI, and honest uncertainty. Do not sermonize; be concrete.