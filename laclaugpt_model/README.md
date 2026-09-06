# LaclauGPT Data Model — canonical observations, graphs as views

The canonical social/text data model for the AI edition. **Store
observations and assertions; generate networks.** Borrowed, not
invented: DNA (statement as atomic unit), Wikidata (qualifiers +
references on statements), W3C Web Annotation (evidence spans), PROV-O
(analytical provenance), ActivityStreams 2.0 (social actor types),
UIMA CAS (typed spans), Neo4j property-graph (projection only).

## Module layout

```
laclaugpt_model/
├── __init__.py     canonical types (Pydantic)
├── projections.py  graphs as pure views (NetworkX)
├── store.py        SQLite + Parquet persistence
└── bridge.py       interchange 1.0 → canonical adapter
```

## The seven canonical types

| Type | Borrowed from | Purpose |
|---|---|---|
| `Document` | ActivityStreams 2.0 | anything observed (post/article/video...) |
| `Actor` | AS2 Person/Org/Account | who |
| `Concept` | — (theory-light) | what; no Laclau subtypes |
| `Annotation` | UIMA CAS + W3C Web Annotation | typed span in a document |
| `Statement` | **DNA** | actor + concept + stance + time + evidence |
| `Relation` | Wikidata qualifiers | generic typed edge with evidence_ids |
| `AnalysisRun` | PROV-O Activity | model/prompt/operator provenance |

Plus `AnalysisResult`: nodal_point / empty_signifier_candidate /
topic_hub classifications as **versioned analytical layer** — the same
concept can carry competing classifications from different methods.
This is the structural answer to the theory-forcing problem (paper §3.4).

## Graphs are views

```python
from laclaugpt_model.projections import ...
actor_concept_graph(statements, ...)       # DNA affiliation network
actor_congruence_graph(statements, ...)    # DNA congruence network
signifier_graph(concepts, relations)       # signifier co-occurrence graph
social_interaction_graph(documents, ...)   # reply/mention network
temporal_slices(statements)                # GEXF-ready time buckets
```

Same canonical rows → as many graphs as needed. Never store the graph.

## Storage

- `init_sqlite(db)` / `upsert(conn, table, rows)` — operational queries
  (same schema on laptop and Roihu; keep the file in persistent scratch)
- `export_parquet(tables, dir)` — bulk analytics (Arrow-backed; falls
  back to JSONL if pyarrow is absent, so Slurm jobs never die on it)
- interchange JSONL (schema 1.1) remains the pipeline's output format;
  `bridge.interchange_to_canonical()` lifts it into the canonical model
  non-destructively.

## Quick example

```python
from laclaugpt_model import Actor, Concept, Statement, AnalysisResult, Stance
from laclaugpt_model.projections import actor_concept_graph
from laclaugpt_model.store import init_sqlite, upsert, model_to_row

altman = Actor(name="Sam Altman")
abundance = Concept(label="abundance")
st = Statement(document_id="doc_1", actor_id=altman.id,
               concept_id=abundance.id, stance=Stance.SUPPORT,
               stance_score=0.9, evidence_span=(84, 164))

conn = init_sqlite("memory/model.db")
upsert(conn, "statements", [model_to_row(st)])

g = actor_concept_graph([st], {altman.id: altman}, {abundance.id: abundance})
```

Interpretations (nodal points, hegemonic articulations) attach as
`AnalysisResult` rows referencing statements as evidence — reproducible,
falsifiable, and separable from the raw observations.
