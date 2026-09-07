# `laclaugpt_model`: frozen pre-2.0 compatibility model

`laclaugpt_model` is an older observation/graph model retained so historical
SQLite/Parquet/projection workflows and old scripts can still be read and
migrated. It is **not** the canonical model for new code.

Use this for new domain objects:

```python
from laclaugpt.model import SourceItem, Statement, Concept, Articulation
```

Use this for current schema-1.3 interchange conversion:

```python
from laclaugpt.adapters.interchange import interchange_to_v2
```

Importing `laclaugpt_model` emits a `FutureWarning` and exposes metadata naming
`laclaugpt.model` as its replacement. The package is frozen: bug fixes needed to
keep historical data readable are allowed, but no new domain concepts or new
integrations should be added here.

## Why it remains

The package still contains useful earlier helpers:

```text
laclaugpt_model/
├── __init__.py     frozen Pydantic observation/assertion types
├── projections.py  older NetworkX graph projections
├── store.py        older SQLite + Parquet helpers
├── lenses.py       optional older analytical projections
└── bridge.py       legacy interchange compatibility bridge
```

The store/projection functions do not yet have exact one-for-one replacements in
the canonical package. Removing them before those replacements exist would make
old work harder to reproduce, so they remain compatibility utilities rather than
an alternative canonical architecture.

## Migration map

| Frozen API | Canonical/new-code replacement |
|---|---|
| `laclaugpt_model.Document` | `laclaugpt.model.SourceItem` + `Representation` |
| `laclaugpt_model.Actor` | `laclaugpt.model.Actor` |
| `laclaugpt_model.Concept` | `laclaugpt.model.Concept` |
| `laclaugpt_model.Statement` | `laclaugpt.model.Statement` plus evidence/provenance objects |
| `laclaugpt_model.Relation` | `Articulation`, `DiscursiveRelation` or `AnalyticRelation` depending on meaning |
| `laclaugpt_model.AnalysisRun` | `laclaugpt.model.Run` + `Provenance` |
| `bridge.interchange_to_canonical()` | `laclaugpt.adapters.interchange.interchange_to_v2()` |
| `store.py` / `projections.py` | retained compatibility helpers until verified canonical equivalents exist |

The old bridge now understands schema-1.3 `Discourse` objects correctly, but its
five-list return shape remains legacy. New code should not build against that
shape.

## Theory rule retained across generations

Laclaudian roles must remain **evidence-bearing analytical results**, not
ontology/node types. The frozen `AnalysisResult` already followed this rule. The
canonical `laclaugpt.model` continues it with explicit evidence-linked role and
relation objects.

For example, a nodal-point assignment in the canonical model requires evidence:

```python
from laclaugpt.model import DiscursiveRoleAssignment

role = DiscursiveRoleAssignment(
    concept_id="con-1",
    discourse_id="disc-1",
    role="NODAL_POINT",
    evidence_ids=["ev-1"],
    provenance_id="prov-1",
)
```

## Compatibility lifetime

This package remains supported while repository history or external scripts still
need its store/projection API and until those functions have tested canonical
replacements. During that window:

- historical data remains readable;
- compatibility bugs may be fixed;
- the API is not extended;
- new adapters and integrations use `laclaugpt.model` instead.
