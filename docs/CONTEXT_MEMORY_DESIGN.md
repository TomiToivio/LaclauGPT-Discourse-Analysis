# LaclauGPT 2.0 — Context Memory Design

**Problem from v1:** entity/topic/sentiment-target multiplication. Every
LLM call wrote NER entities differently ("Musk" / "Elon Musk" / "Elon
Musk (Twitter owner)" / "ELON MUSK"), and nothing could be joined.
The old pipeline had no shared memory: each stage saw only its own
prompt and the row's previous columns.

## Why RAG alone is the wrong tool here

RAG solves *recall over a large corpus*. Our problem is different: it is
**controlled vocabulary drift within a run**. We do not need to find
relevant chunks of text; we need the *same list of canonical entity/topic
strings* to be in front of the model at every extraction step, and for
every new candidate to be resolved against that list *before it is
written*. That is not retrieval — that is a **glossary + normalisation
loop** (an entity-resolution memory).

The design below therefore combines four cheap mechanisms (no vector DB
required for v1; RAG is an optional add-on for v2):

1. **Canonical glossary (the memory).** A per-run SQLite table mapping
   `canonical_name → [aliases, type, first_seen_stage]`. Injected into
   every prompt as a compact list.
2. **Resolution step (the discipline).** Structured output now includes
   `new_candidates` alongside `matched`. The model must first try to
   match against the injected glossary; only unmatched items go to
   `new_candidates`. A post-processing normaliser (difflib + lowercase
   + alias rules) merges near-duplicates deterministically.
3. **Canonicalisation by normalisation.** Before the LLM is even asked,
   candidates are normalised (case, punctuation, whitespace, common
   suffixes stripped, diacritics folded). 80% of v1's multiplication
   was surface-form noise that dies here without any LLM call.
4. **Frozen vocabulary per corpus.** After the first N videos, the
   glossary is locked for high-frequency entities (appearing ≥ 3 times);
   later calls may only map onto it. New entities still possible but
   flagged `provisional` and reviewed at run end.

## What this replaces

- Message history in prompts (useless across 10k calls — cost + drift).
- "Merge similar/related" instructions in the prompt (the model had no
  list to merge against; instructions without memory do nothing).
- Post-hoc dedup attempts on the CSV.

## Where each memory lives

| Memory | Store | Scope | Written by | Read by |
|---|---|---|---|---|
| Entity/topic glossary | SQLite `glossary` table | one analysis run | postprocess + resolution step | frame/summary/postprocess/populism prompts |
| Per-video memory | SQLite `videos` row (JSON blob) | one video | every stage | the next stage for that video |
| Run context (topic background) | SQLite `run_context` KV | one run | config + topic module | every stage's prompt builder |
| Schema cache | Pydantic models | code | — | all structured outputs |

## Prompt-injection contract

Every LLM stage receives:

```
[CONTEXT]
Topic background: <from topic module, stable for the whole run>
Source: <platform, country, collection query — from source-metadata module>
Glossary (canonical, use these exact forms): <top N by usage, capped ~60 lines>
Previous stage output for this item: <JSON from the previous stage>

[EXTRACTION]
<task-specific instructions>
Return JSON: matched: {...}, new_candidates: {...}, ...
```

The glossary is capped (config, default 200 lines / ~1500 tokens) sorted
by usage frequency. This keeps context memory affordable at 8k ctx.

## Why this kills the multiplication

- The model *sees* the canonical list → matches instead of inventing.
- Everything still unmatched goes through deterministic normalisation
  (casefold, strip, diacritic fold, title-case entities) → merges.
- Remaining variants are merged by fuzzy match (difflib ratio ≥ 0.86
  for topics, ≥ 0.9 for person names) with a human review CSV export.
- Entity counts are *monitored*: if `new_candidates` per 100 videos
  keeps rising, the run is flagged in the log (regression alarm).

## Optional v2 upgrades (explicitly deferred)

- **Embedding-based resolution**: sentence-transformers on entity names,
  threshold match — better cross-language merging (e.g. "Migrantit" ↔
  "migrants") — costs a model download on Roihu, worth it after v1 runs.
- **RAG for corpus facts**: only if we later add "answer questions about
  the corpus" features; not needed for extraction.
- **Claude Code memory / external agent memory**: not appropriate —
  LaclauGPT runs are batch jobs on CSC; memory must be a file/DB in the
  job directory, portable and GDPR-safe. A *run-local* glossary is the
  correct scope; anything global would leak between projects.