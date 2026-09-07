# Hermes Agent integration (optional)

[Hermes Agent](https://github.com/NousResearch/hermes-agent) is an open-source
terminal AI agent. LaclauGPT ships no runtime dependency on Hermes — the
integration is a set of conventions that lets a Hermes instance drive the
canonical pipeline as its analysis workhorse. Nothing here is required for
human use; the same CLI commands work with or without an agent.

## Design principle

Hermes participates as an ordinary **caller of the canonical CLI**, never as a
parallel implementation. The execution layer already formalises this: the
`agent` execution backend
([`laclaugpt/execution/backends.py`](laclaugpt/execution/backends.py)) calls
exactly the same `ExecutionCoordinator` as a human `--execution cli`
invocation, so agent runs stay configuration-validated, reproducible and
evidence-linked like every other run.

## What the agent drives

| task | command the Hermes instance runs |
|---|---|
| list profiles | `laclaugpt profiles` |
| compose/validate a run | `laclaugpt analyze <csv> --project ai26 --arena elites --machine roihu --execution agent --show-config` |
| execute a run | `laclaugpt run --project ai26 --arena elites --machine roihu --execution agent --dataset <csv>` |
| import legacy CSV | `laclaugpt import-legacy <csv> -o <jsonl>` |
| open the dashboard | `laclaugpt dashboard <jsonl> --project ai26 --arena elites` |
| collect (Firefox path) | `python -m collector.firefox.firefox_backend --config collector/config/<study>.yaml --data-root <data-root>` |
| collect (CLI/CDP path) | `python -m collector.run --config <config.yaml> --data-root <data-root>` |

The `--execution agent` selection is recorded in the run's provenance; it
changes bookkeeping, not behaviour.

## Project context file

Hermes reads a project-context file from the repository and injects it into
its system prompt. This repository ships
[`HERMES.md`](HERMES.md) for that purpose: it pins the memory boundary
(Hermes memory = individual cognition; the interchange/Context Memory stores
= shared social memory), names the canonical entry points above, and sets the
agent's personality boundary for conversational use.

Optional, not installed by any default: a user who wants this integration
installs [Hermes](https://hermes-agent.nousresearch.com/docs/) and points a
profile at this checkout; the repo needs no changes.

## Scheduling pattern

Hermes cron jobs can wrap the collector and the pipeline the same way plain
crontab entries do. The canonical examples in this repository:

- a watchdog that keeps the Firefox capture backend up
  (`/ping` on `127.0.0.1:8765`, restart when down);
- an hourly media pass that archives referenced videos/thumbnails before
  signed CDN URLs expire.

Both are plain-shell/Python loops that a Hermes cron job or a plain crontab
can call; the scheduler choice is left to the operator.