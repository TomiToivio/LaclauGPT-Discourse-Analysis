# `laclaugpt_model`: transitional observation/graph model

This package is an **older model generation retained for compatibility and
migration work**. It is no longer the canonical import path for new LaclauGPT
package code.

For new code, use the storage-neutral domain model under:

```python
from laclaugpt.model import ...
```

The current batch interchange remains `laclaugpt_interchange/`, schema **1.3**.
The current paper pipeline still uses `laclaugpt_memory/` for persistent Context
Memory and emits schema-1.3 interchange annotations.

`laclaugpt_model/` remains useful because it contains the earlier
observation-first design, SQLite/Parquet storage helpers and NetworkX projection
functions. These are not automatically wrong or removed; they are simply not
the authoritative model API for new integrations. Consolidation of the older
and newer model/memory layers is tracked separately.

## Design preserved here

The package follows the rule: **store observations and assertions; generate
networks as views**. Its design draws on DNA (statement as atomic unit), Wikidata
(qualifiers and references on statements), W3C Web Annotation (evidence spans),
PROV-O (analytical provenance), ActivityStreams 2.0 (social actor types), UIMA
CAS (typed spans), and property-graph projections.

## Module layout

```text
laclaugpt_model/
├── __init__.py     older Pydantic observation/assertion types
├── projections.py  graphs as pure views (NetworkX)
├── store.py        SQLite + Parquet persistence
├── lenses.py       optional analytical projection helpers
└── bridge.py       legacy interchange bridge
```

The bridge is a compatibility path. New interchange conversion work should use
`laclaugpt/adapters/interchange.py`; do not assume `bridge.py` defines the
canonical conversion semantics.

## Types in this model generation

| Type | Borrowed from | Purpose |
|---|---|---|
| `Document` | ActivityStreams 2.0 | anything observed (post/article/video...) |
| `Actor` | AS2 Person/Org/Account | who |
| `Concept` | theory-light | what; no Laclau subtypes |
| `Annotation` | UIMA CAS + W3C Web Annotation | typed span in a document |
| `Statement` | DNA | actor + concept + stance + time + evidence |
| `Relation` | Wikidata-style qualifiers | generic typed edge with evidence IDs |
| `AnalysisRun` | PROV-O Activity | model/prompt/operator provenance |

`AnalysisResult` stores theoretical or analytic classifications as versioned
results rather than turning nodal points, empty-signifier candidates or graph
metrics into ontology types. That anti-theory-forcing principle is retained in
the current architecture.

## Graphs are views

```python
from laclaugpt_model.projections import ...
actor_concept_graph(statements, ...)       # DNA affiliation network
actor_congruence_graph(statements, ...)    # DNA congruence network
signifier_graph(concepts, relations)       # signifier graph
social_interaction_graph(documents, ...)   # reply/mention network
temporal_slices(statements)                # GEXF-ready time buckets
```

The intended rule is still useful: the same observation/assertion rows may be
projected into several graphs; graph structure is not itself the source record.

## Storage

- `init_sqlite(db)` / `upsert(conn, table, rows)` provide local operational
  persistence for this model generation.
- `export_parquet(tables, dir)` supports bulk analytics, with JSONL fallback
  where configured.
- Current pipeline exchange uses `laclaugpt_interchange` **schema 1.3**.

## Compatibility example

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

This example documents the retained API; it should not be read as a recommendation
that new adapters import their canonical domain objects from this package.
