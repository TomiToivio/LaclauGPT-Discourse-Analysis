# Canonical Laclaudian discourse graph schema

## Purpose

LaclauGPT represents discourse as an evidence-linked graph without creating a second ontology beside `laclaugpt.model` and `laclaugpt_interchange`. The graph is a **projection layer** over canonical analysis objects. It exists to support corpus comparison, visualization, export and external graph tooling.

The design question is not only *who talks about what?* It is:

> Who articulates what with what, into which collective subject, against which frontier, under which affective investment, and with which signifiers competing for fixation?

The graph follows three rules:

1. canonical IDs are reused whenever they exist;
2. interpretive relations remain linked to evidence, provenance, uncertainty and review state;
3. Laclaudian roles are contextual analytical assignments, never permanent ontology classes.

## Relationship to existing graph traditions

The schema borrows graph patterns rather than ontologies from existing tools.

- **Discourse Network Analyzer (DNA):** actor-concept and actor-statement projections motivate the actor-signifier view.
- **DATS:** interactive research-object/annotation graphs motivate evidence inspection and researcher-facing views.
- **Argdown:** separation of claims/relations from their visualization motivates explicit projection semantics.
- **NetworkX / GraphML / GEXF:** provide an interoperability path to visone, Gephi and Cytoscape-style workflows.

LaclauGPT adds a specifically Laclaudian layer: equivalence, difference, antagonism/frontiers, collective subjects, affective investment, signifier-role assignments and candidate discursive formations.

## Canonical sources

The graph does **not** replace these sources of truth:

- `laclaugpt.model`: canonical storage-neutral domain model;
- `laclaugpt_interchange.DocumentAnnotation`: canonical batch/publication interchange;
- `THEORY.md`: theoretical invariants;
- Context Memory: stable entity/signifier/formation identity resolution.

`laclaugpt.graph` converts canonical interchange records into `DiscourseGraph` projections. `GraphNode` and `GraphEdge` are transport/view wrappers, not new research-domain classes.

## Core entities

| Graph type | Canonical source | Meaning |
|---|---|---|
| `document` | `SourceItem` / `DocumentAnnotation` | Source/document context |
| `actor` | `Actor` or source author | Speaker/author when resolved/available |
| `signifier` / `concept` | `Concept`, `MemoryRef` | Signifier/concept with stable ID where available |
| `discourse` | `Discourse` | Candidate discourse/structured articulation |
| `formation` | formation `MemoryRef` | Candidate ideological/discursive formation |
| `collective_subject` | `CollectiveSubject` / Palonen Us projection | Constructed political subject |
| `frontier` | `AntagonisticFrontier` / Palonen Frontier projection | Political boundary/antagonistic frontier |
| `affect` | `Affect` / `AffectiveInvestment` | Affective investment, distinct from sentiment |
| `discursive_role_assignment` | `DiscursiveRoleAssignment` / `SignifierRole` | Contextual nodal/floating/empty/etc. assignment |
| `evidence` | `EvidenceSpan` / evidence-bearing interchange fields | Exact supporting source material |

Statements are canonical domain objects in `laclaugpt.model`. Current interchange output does not yet expose stable statement IDs for every coding, so document/evidence context is used in the batch graph until statement references are available in interchange. This is an implementation boundary, not a theoretical claim that statements are unnecessary.

Demands are represented through canonical concepts/signifiers until a distinct demand object is required by a project. The graph must not manufacture a universal `Demand` ontology where the underlying analysis did not make that distinction.

## Relations

Implemented graph relations include:

| Relation | Semantics |
|---|---|
| `AUTHORS` | actor is source author/speaker context for a document |
| `MENTIONS_SIGNIFIER` | document contains/resolves a signifier |
| `ARTICULATES` | evidence-bearing articulation between signifiers/concepts; actor-signifier projection also uses this relation descriptively |
| `EQUIVALENT_TO` | equivalential articulation |
| `DIFFERENTIATED_FROM` | relation of difference, not automatically an antagonistic side |
| `ANTAGONISTIC_TO` | evidenced antagonistic relation |
| `ORGANIZES` | discourse organizes a signifier/concept |
| `HAS_DISCURSIVE_ROLE` | signifier has a contextual role-assignment claim |
| `CANDIDATE_IN` | document supplies evidence for candidate discourse |
| `CANDIDATE_FORMATION` | document supplies evidence for candidate formation |
| `CONSTRUCTS` | document/articulation constructs a collective subject or frontier in the Palonen projection |
| `MEMBER_OF_US` | element is articulated into the Us side |
| `FRONTIER_AGAINST` | frontier is constructed against an element/other side |
| `ANTAGONISTIC_FRONTIER` | relation between constructed Us and Frontier |
| `INVESTED_BY` | target receives an affective investment |
| `SUPPORTED_BY` | a reified interpretive claim/assignment is linked to evidence |

Relation names are graph-level normalized names mapped from existing interchange/canonical relation families. They must not override `DiscursiveRelationType` semantics.

## Evidence, provenance and human review

Every interpretive graph object carries as much of the following context as the source annotation supplies:

- document ID;
- project and arena;
- analysis profile;
- run ID;
- source timestamp;
- model/model digest;
- prompt versions;
- confidence/uncertainty where present;
- claim status where present;
- evidence verification state;
- review status;
- exact evidence reference/text.

The graph is therefore not a flattened network in which an edge becomes a fact merely because it exists. An edge or role assignment is an analytical claim with provenance.

## Discursive roles are assignments, not node classes

Nodal point, floating signifier and empty signifier are roles that a signifier can acquire in a discourse under particular empirical conditions. They are not types of word.

Canonical model:

```text
Concept/Signifier
       |
       +-- HAS_DISCURSIVE_ROLE --> DiscursiveRoleAssignment
                                      |
                                      +-- SUPPORTED_BY --> Evidence
```

A role assignment retains discourse/context, temporal scope, evidence, provenance, confidence and review state. The existing canonical invariant remains authoritative: settled floating- and empty-signifier roles require corpus validation. A document-level candidate cannot silently become a corpus-level role merely because it is visualized.

This allows the same signifier to be, for example, a nodal point inside one discourse while floating between competing formations.

## Palonen Formula of Populism projection

The dedicated projection represents:

`Populism = Us^Affects₁ + Frontier^Affects₂`

as a graph with:

- a constructed `collective_subject` node for Us;
- an `frontier` node;
- evidence-bearing Us/frontier elements;
- affect nodes linked through `INVESTED_BY`;
- an `ANTAGONISTIC_FRONTIER` relation;
- evidence/provenance on the component claims.

The projection does **not** infer populism merely because an in-group and opponent exist. `DocumentAnnotation.populist`, `non_populist_reason`, evidentiary gates and human review remain authoritative. If the required elements are missing, the graph contains no complete Palonen configuration.

## Projections

One canonical graph can produce multiple deterministic views:

### `actor_signifier`

DNA-style actor/signifier projection. Useful for comparing which actors articulate which signifiers. This is a descriptive projection and does not by itself establish ideological formation or hegemony.

### `signifier_field`

Signifiers/concepts connected through articulation, equivalence, difference and antagonism, with contextual role assignments and evidence.

### `formation_map`

Candidate formations/discourses linked to the documents and evidence that support them. Current interchange carries formation candidates and supporting/counter-features but not yet a complete formation-to-signifier relation object, so this projection intentionally does not fabricate such edges.

### `populism`

Collective subject, equivalential Us-side elements, frontier/antagonist and affective investments following Palonen's formula.

### `temporal`

Canonical graph with timestamp metadata retained for time filtering/slicing. Temporal visualization should compare equivalent projections over explicit intervals rather than infer change from layout movement alone.

### `evidence_claim`

Researcher inspection view emphasizing role assignments, candidate discourse/formation claims and the evidence supporting them.

## Pipeline integration

`run_canonical_pipeline()` now writes the ordinary annotation JSONL and three graph sidecars from the **post-switch** annotations:

- `*.graph.json`
- `*.graph.graphml`
- `*.graph.gexf`

This ordering matters. Project analysis switches are applied before graph construction, so a disabled Laclaudian or Palonen module cannot reappear through a graph projection.

Graph generation uses the same project/arena provenance written into the canonical annotations. Stable `MemoryRef.obj_id` values are retained as graph node IDs where possible.

## Visualization semantics

The dashboard adapter in `laclaugpt.visualization.graph` consumes canonical annotations and calls `laclaugpt.graph`. It does not reconstruct a second ad-hoc graph schema.

Graph views should be small projections rather than one universal hairball. Node size/layout may be visual conveniences, but must never be interpreted automatically as theoretical importance, hegemony or nodal status.

Click/hover inspection should expose at least relation type, document/run context, confidence, claim/review status and evidence identifiers where present.

## Export formats and external tools

### GraphML

GraphML is emitted as the primary interoperable graph format. It is intended for:

- NetworkX;
- visone;
- Gephi;
- Cytoscape and other GraphML-capable tooling.

Properties that cannot be represented as scalar XML text are serialized deterministically as JSON strings.

### GEXF

A deterministic static GEXF projection is also emitted for Gephi and related tools. The current GEXF writer intentionally keeps the portable node/edge core small. Rich evidence/provenance remains most complete in JSON and GraphML.

### JSON

The JSON graph bundle is the loss-minimizing LaclauGPT representation for web/dashboard consumers.

## DNA compatibility

LaclauGPT should provide DNA-style **projections**, not redefine its canonical ontology to match DNA. The `actor_signifier` projection can be converted to two-mode actor-concept data for external discourse-network workflows while preserving the richer Laclaudian graph internally.

## Data-publication boundary

Graph outputs derived from real social-media research data may remain personal or special-category data even when raw text is absent. Per-person political positions, identifiable actor-signifier relations, rare temporal combinations and document-linked evidence remain restricted by default under `docs/DATA_PUBLICATION_POLICY.md`.

Synthetic graph fixtures may be public. Aggregate graph publications require disclosure review.

## Implemented now vs later

Implemented in issue #84:

- canonical graph projection module;
- stable-ID reuse for interchange references;
- evidence/provenance/review-carrying graph relations;
- contextual discursive-role assignments;
- actor-signifier, signifier-field, formation, populism, temporal and evidence projections;
- pipeline graph sidecars;
- GraphML, GEXF and JSON exports;
- dashboard projection adapter;
- synthetic offline tests.

Later enhancements can include:

- first-class stable statement IDs in interchange graph exports;
- richer corpus-level formation-to-signifier/fixation objects after validation logic is defined;
- interactive Cytoscape.js/Sigma.js rendering if it improves the Streamlit experience;
- DNA import/export convenience tables;
- graph-database persistence as an optional backend, without making storage technology part of the canonical model.
