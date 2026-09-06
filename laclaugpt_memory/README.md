# laclaugpt_memory — persistent analytical memory

Stable-ID codebook + resolution loop for LaclauGPT 2.0. Same API and
SQLite schema on the laptop and CSC Roihu. Single file + optional
embedding index, no external services, Slurm-batch safe.

## Design (per Tomi's spec)

- **Stable IDs**: `E001` entities, `T001` topics, `S001` signifiers,
  `C001` sentiment/stance targets, `A001` actors, `F001` formations.
  Free-text labels are only aliases, never the identity.
- **Open-world codebook**: `CANONICAL / PROVISIONAL / MERGED /
  DEPRECATED / REJECTED`. New objects start `PROVISIONAL`; promoted to
  `CANONICAL` after `promote_threshold` uses or human validation.
- **Workflow**: EXTRACT → RETRIEVE EXISTING CANDIDATES → RESOLVE →
  UPDATE MEMORY. Creating a new canonical object is the last option;
  the resolver returns `EXISTING / NEW / UNCERTAIN`.
- **Raw wording preserved**: every surface form is kept in `aliases`
  with provenance. e.g. `"prosperity"`, `"economic prosperity"`,
  `"economic growth"` may resolve to `S017 ECONOMIC_GROWTH`, but the
  raw forms stay for discourse analysis.
- **Temporal drift**: `temporal` table records relations with periods
  (e.g. `AI_SAFETY → X_RISK` in one period; `AI_SAFETY → REGULATION`
  in another), each with source provenance.
- **Provenance & decisions**: every created/matched/merged/promoted
  action lands in `decisions` with stage, video_key, evidence, model.

## Usage

```python
from laclaugpt_memory import Memory

mem = Memory(memory_dir=os.environ.get("LACLAUGPT_MEMORY_DIR"))

# in a stage, for each extracted candidate:
res = mem.resolve("advanced AI", kind="target", stage="postprocess",
                  video_key="user::video123", evidence="quote from transcript")
# -> Resolution(raw="advanced AI", obj_id="C001", label="artificial intelligence",
#               decision="EXISTING", score=0.97)

# retrieve a compact, relevant subset for a prompt (never the whole DB):
block = mem.context_prompt_block(chunk_text)

# record the coding with provenance:
mem.record_analysis("user::video123", "postprocess", payload, evidence)

# consolidation after N documents/batches:
result = mem.consolidate_memory()   # auto-merges ≥0.97, writes merge_suggestions.csv
```

## Embeddings

Local `sentence-transformers` (default model
`paraphrase-multilingual-MiniLM-L12-v2`, cached under the memory dir)
when available; similarity search is a numpy linear scan over the
embedding table (fast to ~50k objects; swap to FAISS later without a
schema change). Graceful degradation: without the package, matching
falls back to exact/alias/fuzzy string logic — the pipeline keeps
working, slightly dumber.

Environment:
- `LACLAUGPT_MEMORY_DIR` — persistent storage location (CSC scratch!)
- `LACLAUGPT_EMBED_MODEL` — override the embedding model

## Tables

`objects` (stable IDs + state + definition + centroid), `aliases`
(raw surface forms + provenance), `alias_meta` (normalised lookup),
`embeddings` (blob vectors), `decisions` (provenance log),
`temporal` (period-stamped relations), `runs`.

## Compatibility

`memory.py` is a shim delegating `ContextMemory` /
`resolve_candidates` to this module, so existing stage code keeps
working. `pipeline.py` constructs the Memory from
`LACLAUGPT_MEMORY_DIR` (fallback: `<database_dir>/memory`) and runs a
consolidation pass at run end.

## Consolidation

`consolidate_memory()`: duplicate scan per kind → auto-merges only
high-confidence pairs (≥0.97 similarity, winner = higher usage), and
writes everything below that to `merge_suggestions.csv` for human
validation. Merges keep both IDs: loser becomes `MERGED` with
`merged_into` pointing at the survivor; aliases move to the winner
but their history rows are preserved.