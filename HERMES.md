# LaclauGPT — project context for Hermes Agent

This file is read by [Hermes Agent](https://github.com/NousResearch/hermes-agent)
when a Hermes session runs inside this repository (see
[`docs/HERMES_INTEGRATION.md`](docs/HERMES_INTEGRATION.md)). It is project
context, not runtime code: the pipeline has zero runtime dependency on Hermes.

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

1. Run `python -m pytest -q tests` before declaring any change done; CI
   (`Repository CI`) is the gate.
2. Research data roots (`laclaugpt-brasil-data/`, `collection-data/`, `*.har`)
   are never committed; `.gitignore` enforces this.
3. Do not commit secrets: endpoints and credentials come from environment
   variables, never from files in this tree.
4. Collection is for public political content only; the collector does not
   bypass authentication barriers, private accounts or CAPTCHAs.
5. Statement-level claims must trace to source evidence; the agent may reject
   its own interpretation, never invent evidence.

## Conversational personality

When the conversation is not an operational task, keep the grounded register
of the manuscript: discourse theory (Laclau, Mouffe, Palonen), political
economy of AI, and honest uncertainty. Do not sermonize; be concrete.