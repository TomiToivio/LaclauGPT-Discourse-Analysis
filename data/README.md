# data/ — collected & analyzed research data

This directory holds **working research data**: collected material,
pipeline outputs and derived state. It is deliberately **gitignored**
(research data roots are never committed — `.gitignore`).

## What lives here

| Path | Purpose |
|---|---|
| `memory/` | Context Memory SQLite store (canonical codebook, decisions, temporal relations) — default of `LACLAUGPT_DATA_DIR` |
| `annotations.jsonl` | Batch interchange output, one annotation per document (schema version in `laclaugpt_interchange.SCHEMA_VERSION`) |
| `merge_suggestions.csv` | Similarity-driven merge proposals written for human review — never auto-applied |
| `audit/` | Hermes audit trail (`hermes-actions.jsonl` by default) |

Nothing here is validated research output until a human researcher has
adjudicated it (INV_HUMAN_REVIEW). The pipeline produces provisional,
model-proposed records only.

## Conventions

- Local-first: data stays on this machine unless explicitly exported.
- `data/input.csv` is the usual dataset mount point for `run_pipeline`
  (see `docs/HERMES_INTEGRATION.md`).
- Point `LACLAUGPT_DATA_DIR` elsewhere to relocate the whole root
  (e.g. scratch on CSC); the code never assumes this exact path.
- Do not commit anything under this directory; provenance and reproducible
  configuration live in the repo, volatile data does not.