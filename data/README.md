# data/ — restricted/runtime research data

This directory is the default **working research-data root** for collected material, pipeline outputs and derived state. It is deliberately gitignored.

**`data/` is never a publication directory.** Do not commit a "small sample" of real social-media data here for convenience. Public releases belong in explicitly reviewed locations such as documentation, synthetic examples, or disclosure-reviewed aggregate outputs.

See:

- [`docs/DATA_PUBLICATION_POLICY.md`](../docs/DATA_PUBLICATION_POLICY.md)
- [`docs/DATA_LIFECYCLE.md`](../docs/DATA_LIFECYCLE.md)

## What lives here

| Path | Purpose |
|---|---|
| `memory/` | Context Memory SQLite store (canonical codebook, decisions, temporal relations) — default of `LACLAUGPT_DATA_DIR` |
| `annotations.jsonl` | Batch interchange output, one annotation per document (schema version in `laclaugpt_interchange.SCHEMA_VERSION`) |
| `merge_suggestions.csv` | Similarity-driven merge proposals written for human review — never auto-applied |
| `audit/` | Hermes audit trail (`hermes-actions.jsonl` by default) |

Nothing here is validated research output until a human researcher has adjudicated it (`INV_HUMAN_REVIEW`). The pipeline produces provisional, model-proposed records only. Human adjudication does **not** by itself make row-level data anonymous or suitable for public release.

## Conventions

- Local/controlled first: research data stays in the approved working environment unless explicitly exported through a reviewed publication workflow.
- `data/input.csv` is the usual dataset mount point for `run_pipeline` (see `docs/HERMES_INTEGRATION.md`).
- Point `LACLAUGPT_DATA_DIR` elsewhere to relocate the whole root (for example approved CSC scratch/storage); the code never assumes this exact path.
- Do not commit anything under this directory; provenance and reproducible configuration live in the repo, volatile/restricted data does not.
- Raw media, ASR/OCR, document-level annotations, embeddings, user metadata, review databases and researcher notes are restricted by default.
- Safe publication should normally use synthetic fixtures or disclosure-reviewed aggregates rather than row-level real records.
- Secrets, credentials and pseudonymisation keys must not be stored in Git and should be separated from the research records they unlock.
