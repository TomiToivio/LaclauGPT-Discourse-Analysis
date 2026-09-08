# Claude Code integration (optional)

[Claude Code](https://claude.com/claude-code) is a terminal AI agent. LaclauGPT
ships no runtime dependency on Claude Code — the integration is a set of
conventions and a thin wrapper that let a Claude Code session drive the
canonical pipeline as its analysis workhorse, exactly like the
[Hermes Agent integration](HERMES_INTEGRATION.md). Nothing here is required for
human use; the same CLI commands work with or without an agent.

## Theory contract

Before any theory-facing work, the Claude Code session must read
[`THEORY.md`](../THEORY.md) in full. It is the framework-independent semantic
contract for prompts, schemas, discourse-analysis logic, Context
Memory/codebook behaviour, corpus synthesis, visualisations and methodology
documentation. The original Laclau, Laclau & Mouffe, and Palonen sources remain
authoritative if a theoretical definition is changed. [`CLAUDE.md`](../CLAUDE.md)
repeats the operational rule so that it reaches the agent system context.

The agent may orchestrate preliminary analysis, but it may not weaken the
human-in-the-loop boundary. LaclauGPT outputs remain preliminary,
human-reviewable research proposals until a human researcher verifies the
source evidence and interpretation.

## Design principle

Claude Code participates as an ordinary **caller of the canonical CLI**, never
as a parallel implementation. The execution layer already formalises this: the
`agent` execution backend
([`laclaugpt/execution/backends.py`](../laclaugpt/execution/backends.py)) calls
exactly the same `ExecutionCoordinator` as a human `--execution cli`
invocation, so agent runs stay configuration-validated, reproducible and
evidence-linked like every other run.

## What the agent drives

| task | command the Claude Code session runs |
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

## Audited Python tool surface

For tool-calling, LaclauGPT also exposes a small optional wrapper at
`laclaugpt.integrations.claude`. It imports no Claude/Anthropic SDK and
therefore adds no dependency to the core package. It reuses the audited
Hermes tool surface (`laclaugpt.integrations.hermes`) with a `claude-code`
audit actor.

```python
from laclaugpt.integrations.claude import ClaudeTools

claude = ClaudeTools()

claude.profiles()
claude.dry_run(
    project="ai26",
    arena="elites",
    machine="roihu",
    dataset="data/input.csv",
)
claude.run_analysis(
    project="ai26",
    arena="elites",
    machine="roihu",
    dataset="data/input.csv",
)
```

The wrapper is intentionally narrower than the CLI. It accepts project, arena,
machine and dataset selection, but not arbitrary shell arguments, environment
variables, model-routing flags, credentials or cloud-fallback permissions.
Every execution is forced through the canonical `agent` backend. This prevents
an agent tool call from bypassing the local-only/data-governance policy
configured elsewhere in LaclauGPT.

Agent actions are written to the append-only JSONL audit log
`data/audit/claude-actions.jsonl` by default. A different path may be supplied
when constructing `ClaudeTools`. The log records timestamp, actor
(`claude-code`), action, status and action details. The canonical `RunStore`
separately records the actual LaclauGPT run with `execution_mode=agent`.

Destructive, publishing and repository-changing operations are deliberately
not exposed by this integration. `request_destructive_action()` exists only as
a fail-closed boundary for tool schemas that need an explicit rejection path.
Such operations require a separate human-authorised interface.

## Project context file

Claude Code reads a project-instruction file from the repository. This
repository ships [`CLAUDE.md`](../CLAUDE.md) for that purpose: it requires
`THEORY.md` before theory-facing work, pins the memory boundary, names the
canonical entry points, and defines the agent-caller rule for provenance.

Optional, not installed by any default: a user who wants this integration
installs Claude Code and opens this checkout; the repo itself still needs no
Claude dependency.

## Model routing boundary: local Ollama open-source models only

Both agent integrations — **Hermes and Claude Code** — are restricted to
**local Ollama open-source models**. This is enforced in the shared tool
surface ([`laclaugpt/integrations/agent_policy.py`](../laclaugpt/integrations/agent_policy.py)):

- agent-triggered runs require `LLM_MODE=local` in the environment;
- `auto`, `cloud` and `external` routing are refused, because they can send
  research data to Ollama cloud or an off-machine endpoint;
- `LLM_ALLOW_CLOUD_FALLBACK=1` is refused, so a local run can never silently
  fall back to a cloud model mid-run;
- agent tool calls accept no model-routing flags or credentials.

Human CLI invocations keep the full machine-tier routing described in
`llm.py`; this restriction applies to the agent tool surface and to the
instructions in `HERMES.md` / `CLAUDE.md`.

## Security and data-governance boundary

Claude Code must not:

- change `LLM_MODE`, `OLLAMA_HOST`, cloud-fallback permission or credentials;
- send research data to any model endpoint other than the local Ollama server;
- bypass LaclauGPT configuration validation;
- write to GitHub, publish outputs or delete research data through this tool
  surface;
- present the agent's private/session memory as LaclauGPT research memory;
- bypass `THEORY.md` invariants or human review in order to make analysis more
  autonomous.

The agent may inspect, propose and orchestrate. Canonical LaclauGPT code owns
analysis semantics, provenance, routing, storage and research-state changes.