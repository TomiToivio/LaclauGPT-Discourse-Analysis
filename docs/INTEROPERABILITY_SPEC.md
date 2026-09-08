# LaclauGPT Interoperability Specification

**Version:** 0.1
**Status:** Draft
**Project:** LaclauGPT
**Purpose:** Define a stable interoperability architecture for exchanging data between LaclauGPT and external social-data-science, discourse-analysis, qualitative-analysis, annotation, collection, and visualisation tools.

---

# 1. Scope

LaclauGPT is a theory-guided computational discourse-analysis framework based primarily on Ernesto Laclau's discourse theory, Emilia Palonen's Formula of Populism, sociotechnical imaginaries, and related social-data-science methods.

LaclauGPT should not attempt to replace existing tools for:

* web and social-media collection;
* digital ethnography;
* qualitative coding;
* human annotation;
* discourse network analysis;
* exploratory text analysis;
* graph analysis;
* visualisation.

Instead, LaclauGPT should function as an **interoperable analytical engine** between these systems.

The principal architecture is:

```text
COLLECTION
    │
    ├── minet
    ├── Zeeschuimer
    ├── 4CAT
    ├── platform APIs
    └── manual digital ethnography
    │
    ▼
LACLauGPT INTERMEDIATE REPRESENTATION
    │
    ▼
LACLauGPT ANALYSIS
    │
    ├── descriptive analysis
    ├── signifiers
    ├── articulations
    ├── equivalence / difference
    ├── antagonism
    ├── affect
    ├── sociotechnical imaginaries
    ├── discourse formations
    └── Formula of Populism
    │
    ▼
INTEROPERABILITY LAYER
    │
    ├── QDPX / REFI-QDA
    │      ├── ATLAS.ti
    │      ├── MAXQDA
    │      ├── NVivo
    │      └── QualCoder
    │
    ├── DNA / rDNA
    │
    ├── INCEpTION / UIMA CAS
    │
    ├── DATS
    │
    ├── GraphML / GEXF
    │      ├── Gephi
    │      └── Cytoscape
    │
    └── CSV / JSON / Parquet
```

The central principle is:

> **LaclauGPT should integrate through stable data contracts rather than tool-specific internal dependencies whenever possible.**

---

# 2. Architectural principles

## 2.1 LaclauGPT Core

The LaclauGPT Core MUST remain independent of any particular external application.

The core accepts source documents represented using the LaclauGPT Intermediate Representation and produces structured analytical objects.

External integrations SHOULD be implemented through adapters.

```text
external tool
     │
     ▼
input adapter
     │
     ▼
LaclauGPT IR
     │
     ▼
LaclauGPT Core
     │
     ▼
LaclauGPT IR
     │
     ▼
output adapter
     │
     ▼
external tool
```

---

## 2.2 Source preservation

Original source material MUST remain distinguishable from:

* preprocessing;
* transcription;
* translation;
* model summaries;
* machine coding;
* human coding;
* corpus-level inference.

LaclauGPT MUST NOT silently overwrite source content.

---

## 2.3 Model output is provisional

Every machine-produced analytical object MUST initially have:

```yaml
status: PROVISIONAL
```

Only an explicit human validation action MAY change an object to:

```yaml
status: CANONICAL
```

Additional permitted states SHOULD include:

```yaml
status:
  - PROVISIONAL
  - ACCEPTED
  - REJECTED
  - REVISED
  - CANONICAL
  - SUPERSEDED
```

---

## 2.4 Evidence grounding

Every interpretive machine-generated claim SHOULD contain source evidence.

Example:

```json
{
  "type": "articulation",
  "source": "AI",
  "target": "economic_growth",
  "relation": "articulated_with",
  "evidence": {
    "quote": "AI will unlock unprecedented economic growth",
    "start": 142,
    "end": 188
  }
}
```

Corpus-level theoretical claims MUST NOT be inferred solely from frequency.

---

## 2.5 Abstention

Every analysis stage MUST permit:

```json
{
  "result": null,
  "status": "ABSTAIN",
  "reason": "Insufficient evidence"
}
```

The absence of a theoretical structure is a valid analytical result.

---

# 3. LaclauGPT Intermediate Representation

The canonical interchange representation is **LaclauGPT IR**.

Recommended serialisations:

1. JSON / JSONL — canonical interchange and APIs
2. Parquet — large analytical datasets
3. CSV — compatibility
4. SQLite or DuckDB — local analytical storage

JSONL SHOULD be the default batch-exchange format.

---

# 4. Document object

Each source document SHOULD contain:

```json
{
  "schema_version": "0.1",
  "document_id": "doc_000001",

  "source": {
    "platform": "web",
    "source_type": "article",
    "url": "https://example.org/article",
    "external_id": null
  },

  "actor": {
    "id": "actor_001",
    "name": "Example Actor",
    "type": "person"
  },

  "time": {
    "published_at": "2026-09-05T12:00:00Z",
    "collected_at": "2026-09-05T13:20:00Z"
  },

  "language": {
    "source": "en",
    "analysis": "en"
  },

  "collection": {
    "tool": "minet",
    "query": "artificial intelligence",
    "collector": "researcher",
    "arena": "AI_elites"
  },

  "content": {
    "raw": "...",
    "normalized": "...",
    "title": "..."
  },

  "provenance": [],

  "analysis": {}
}
```

---

# 5. Provenance model

Every transformation MUST be recorded.

```json
{
  "operation": "translation",
  "tool": "model-or-library",
  "version": "x.y.z",
  "timestamp": "2026-09-05T13:40:00Z",
  "input": "content.raw",
  "output": "content.translation.en"
}
```

Typical provenance operations include:

* collection
* URL resolution
* extraction
* transcription
* OCR
* translation
* normalization
* segmentation
* LLM analysis
* human revision
* codebook merge
* export

---

# 6. Analytical object model

## 6.1 Signifier

```json
{
  "id": "sig_ai",
  "surface_form": "artificial intelligence",
  "canonical_form": "AI",
  "type": "signifier",
  "role": "floating_signifier_candidate",
  "status": "PROVISIONAL",
  "evidence": []
}
```

Roles MAY include:

```text
element
moment
nodal_point_candidate
floating_signifier_candidate
empty_signifier_candidate
subject_signifier
frontier_element
```

A single document MUST NOT normally establish floating- or empty-signifier status at corpus level.

---

# 7. Articulation relations

Relations SHOULD be represented as graph-compatible edges.

```json
{
  "id": "rel_001",
  "type": "articulation",
  "source": "sig_ai",
  "target": "sig_growth",
  "relation": "articulated_with",
  "polarity": null,
  "confidence": 0.82,
  "status": "PROVISIONAL",
  "evidence": []
}
```

Recommended relation vocabulary:

```text
articulated_with
equivalent_to
differentiated_from
antagonistic_to
supports
opposes
represents
identifies_with
governs
threatens
enables
```

Tool-specific adapters MAY use narrower vocabularies.

---

# 8. Affects

Affect MUST NOT be reduced to sentiment polarity.

```json
{
  "target": "sig_technology",
  "affects": [
    {
      "label": "hope",
      "confidence": 0.85,
      "evidence": []
    },
    {
      "label": "ambition",
      "confidence": 0.76,
      "evidence": []
    }
  ]
}
```

Positive/negative sentiment MAY exist as a separate descriptive field.
Implemented since schema 1.4 as `DocumentAnnotation.sentiment_observations`
(descriptive `positive|neutral|negative` polarity over resolved stable-ID
targets, with model/prompt provenance and `review_status`), deliberately a
separate record family from `affects` (affective investment). Enabling or
displaying a sentiment view never transforms sentiment polarity into
affective investment (THEORY.md INV_AFFECT).

---

# 9. Sociotechnical imaginaries

```json
{
  "id": "imaginary_001",

  "present_diagnosis": "...",

  "future": {
    "type": "desired",
    "description": "..."
  },

  "technology_role": "...",

  "human_agency": "...",

  "governance": {
    "authorized_actors": []
  },

  "status": "PROVISIONAL",
  "evidence": []
}
```

---

# 10. Ideological formations

Ideological formations are corpus-level objects.

```json
{
  "id": "formation_001",
  "label": "accelerationist_candidate",

  "members": {
    "actors": [],
    "documents": [],
    "signifiers": []
  },

  "characteristic_relations": [],

  "status": "PROVISIONAL"
}
```

Seed categories MAY include:

* accelerationism
* existential-risk discourse
* Critical AI
* anti-AI mobilisation
* left techno-optimism

These MUST remain **sensitising categories**, not mandatory classifications.

Unanticipated formations MUST be permitted.

---

# 11. Formula of Populism

Formula of Populism analysis SHOULD be represented structurally rather than solely as formatted text.

```json
{
  "populism": {
    "detected": true,

    "us": {
      "elements": [
        "technology",
        "markets",
        "growth"
      ],
      "affects": [
        "hope",
        "confidence"
      ]
    },

    "frontier": {
      "elements": [
        "bureaucracy",
        "deceleration"
      ],
      "affects": [
        "anger",
        "contempt"
      ]
    },

    "status": "PROVISIONAL",
    "evidence": []
  }
}
```

The formula MUST NOT be produced unless both:

1. a collective political subject; and
2. a constitutive frontier

are supported by evidence.

---

# 12. Minet interoperability

Minet is treated primarily as an **upstream web-mining and collection layer**.

Minet's CSV- and Unix-oriented design makes it particularly suitable for loose coupling with LaclauGPT. Minet can fetch, crawl, extract web content, normalise URLs, and collect material from several web and social platforms, while also exposing a Python interface.

Recommended pipeline:

```text
minet
  │
  ├── fetch
  ├── extract
  ├── scrape
  ├── crawl
  ├── url-parse
  └── platform collection
  │
  ▼
CSV / JSON
  │
  ▼
laclaugpt import-minet
  │
  ▼
LaclauGPT IR
```

LaclauGPT SHOULD provide:

```bash
laclaugpt import minet input.csv \
    --text-column text \
    --url-column url \
    --author-column author \
    --timestamp-column timestamp \
    --output corpus.jsonl
```

The adapter MUST preserve all unmapped Minet fields inside:

```json
{
  "external_metadata": {
    "minet": {}
  }
}
```

The Minet adapter SHOULD NOT require Minet itself to be installed.

Optional direct Unix piping SHOULD be supported:

```bash
minet extract -i fetched.csv -I downloaded \
  | laclaugpt import minet --stdin \
  | laclaugpt analyse --stdin \
  > analysed.jsonl
```

This preserves Minet's Unix-style workflow rather than forcing database integration.

---

# 13. 4CAT and Zeeschuimer interoperability

Recommended flow:

```text
Zeeschuimer
     ↓
4CAT
     ↓
LaclauGPT processor
     ↓
LaclauGPT IR
     ↓
4CAT results
```

Two modes SHOULD be supported:

## Export/import mode

```text
4CAT dataset
→ CSV/JSON
→ LaclauGPT
→ analysis JSON/CSV
→ 4CAT
```

## Native processor mode

A LaclauGPT 4CAT processor SHOULD eventually:

1. accept a 4CAT dataset;
2. map records to LaclauGPT documents;
3. run configured LaclauGPT stages;
4. return structured result files;
5. expose graph and coding outputs to subsequent 4CAT processors.

Zeeschuimer data SHOULD retain browser-collection provenance.

---

# 14. DATS interoperability

DATS SHOULD be treated as a general-purpose discourse-analysis workbench.

Preferred architecture:

```text
DATS
  │
  ▼
LaclauGPT adapter
  │
  ▼
LaclauGPT analysis
  │
  ▼
DATS annotations / analysis
```

Mappings SHOULD include:

```text
DATS document      ↔ LaclauGPT document
DATS annotation    ↔ code/evidence
DATS entity        ↔ actor/signifier
DATS relation      ↔ articulation relation
DATS project       ↔ corpus
```

LaclauGPT SHOULD eventually be usable as a DATS analysis module rather than only through file export.

---

# 15. DNA / rDNA interoperability

Discourse Network Analysis provides the principal network-analysis interoperability target.

LaclauGPT relational output SHOULD be convertible into DNA statement structures.

Conceptual mapping:

```text
LaclauGPT actor
        ↓
DNA actor

LaclauGPT signifier / concept
        ↓
DNA concept

LaclauGPT stance / relation
        ↓
DNA qualifier

LaclauGPT document
        ↓
DNA source

timestamp
        ↓
DNA temporal metadata
```

This enables:

```text
actor × concept networks
concept × concept networks
actor × actor networks
temporal discourse networks
```

LaclauGPT MUST retain its richer theory-specific representation even where DNA requires reduction to actor–concept statements.

DNA export is therefore a **projection**, not the canonical data model.

---

# 16. QDPX / REFI-QDA interoperability

QDPX SHOULD be the primary interoperability mechanism for CAQDAS applications.

Target applications include:

```text
ATLAS.ti
MAXQDA
NVivo
QualCoder
other REFI-QDA-compatible tools
```

LaclauGPT SHOULD export:

* source documents;
* document metadata;
* code hierarchy;
* coded text spans;
* coder identity;
* provisional status where representable;
* comments/memos containing confidence and provenance.

Recommended code hierarchy:

```text
LaclauGPT
├── Signifiers
│   ├── Elements
│   ├── Nodal candidates
│   ├── Floating candidates
│   └── Empty candidates
│
├── Relations
│   ├── Articulation
│   ├── Equivalence
│   ├── Difference
│   └── Antagonism
│
├── Political subject
│   ├── Us
│   └── Frontier
│
├── Affect
│
├── Sociotechnical imaginaries
│
└── Ideological formations
```

QDPX import SHOULD also permit human-coded QDA material to become training, validation, or comparison data inside LaclauGPT.

---

# 17. QualCoder interoperability

QualCoder SHOULD initially be supported through QDPX.

A later native integration MAY support:

```text
QualCoder project
     ↓
LaclauGPT coding suggestions
     ↓
human accept/edit/reject
     ↓
QualCoder canonical coding
```

QualCoder SHOULD be considered the preferred open-source QDA reference implementation.

---

# 18. INCEpTION interoperability

INCEpTION SHOULD be considered a primary human-validation platform.

Preferred architecture:

```text
INCEpTION
     │
     ▼
LaclauGPT external recommender
     │
     ▼
candidate annotations
     │
     ▼
human annotation
```

Potential annotation layers include:

```text
Signifier
Articulation
Equivalence
Difference
Antagonism
Us
Frontier
Affect
Imaginary
FormationCandidate
```

LaclauGPT SHOULD distinguish:

```text
machine suggestion
human annotation
adjudicated annotation
```

UIMA CAS MAY be used as the interchange representation where required by INCEpTION.

---

# 19. Graph interoperability

Every relational analytical object SHOULD be exportable into a property graph representation.

Core node types:

```text
Document
Actor
Signifier
Imaginary
Formation
Arena
```

Core edge types:

```text
AUTHORED
MENTIONS
ARTICULATES
EQUIVALENT_TO
DIFFERENT_FROM
ANTAGONISTIC_TO
BELONGS_TO
INVESTED_WITH
APPEARS_IN
```

Example:

```text
Actor ──ARTICULATES──> AI
AI ──EQUIVALENT_TO──> progress
AI ──EQUIVALENT_TO──> abundance
Actor ──ANTAGONISTIC_TO──> regulation
```

---

# 20. GraphML and GEXF

LaclauGPT SHOULD support:

```bash
laclaugpt export graphml analysis.jsonl > discourse.graphml
```

and optionally:

```bash
laclaugpt export gexf analysis.jsonl > discourse.gexf
```

These formats provide interoperability with:

* Gephi;
* Cytoscape;
* NetworkX;
* igraph;
* other network-analysis systems.

---

# 21. Cytoscape.js interoperability

The LaclauGPT web interface SHOULD use a graph representation compatible with Cytoscape.js.

Recommended API response:

```json
{
  "nodes": [
    {
      "data": {
        "id": "sig_ai",
        "label": "AI",
        "type": "signifier"
      }
    }
  ],

  "edges": [
    {
      "data": {
        "id": "rel_1",
        "source": "sig_ai",
        "target": "sig_growth",
        "relation": "equivalent_to"
      }
    }
  ]
}
```

This SHOULD be derivable automatically from LaclauGPT IR.

---

# 22. Generic tabular interoperability

Every major object SHOULD also be exportable as tables.

Recommended files:

```text
documents.csv
actors.csv
signifiers.csv
relations.csv
affects.csv
imaginaries.csv
formations.csv
populism.csv
evidence.csv
reviews.csv
```

This provides compatibility with:

* R;
* Python/pandas;
* DuckDB;
* PostgreSQL;
* SPSS/Stata where needed;
* spreadsheet applications;
* generic visualisation tools.

---

# 23. Human review protocol

Adapters for annotation/QDA applications MUST preserve the difference between:

```text
MODEL
HUMAN
ADJUDICATED
```

Example:

```json
{
  "coding_id": "code_123",

  "generated_by": {
    "type": "model",
    "model": "gemma4"
  },

  "model_status": "PROVISIONAL",

  "review": {
    "reviewer": "coder_01",
    "decision": "ACCEPT",
    "timestamp": "..."
  },

  "status": "CANONICAL"
}
```

Human revision SHOULD preserve the original machine suggestion for methodological auditing.

---

# 24. Reproducibility metadata

Every LaclauGPT analysis run SHOULD archive:

```text
LaclauGPT version
Git commit
schema version
model name
model digest
Ollama/server version
prompt version
analysis configuration
temperature
seed where applicable
timestamp
language
input corpus hash
codebook version
```

Example:

```json
{
  "run": {
    "laclaugpt_version": "0.2.0",
    "git_commit": "...",
    "schema_version": "0.1",

    "model": {
      "name": "gemma4",
      "digest": "..."
    },

    "prompt_version": "discourse-v4",
    "temperature": 0.0,

    "corpus_hash": "sha256:..."
  }
}
```

---

# 25. Adapter interface

All adapters SHOULD follow a common Python protocol.

```python
class LaclauGPTAdapter:

    def detect(self, source) -> bool:
        ...

    def import_documents(self, source):
        ...

    def export_documents(self, corpus, destination):
        ...

    def export_analysis(self, analysis, destination):
        ...
```

Suggested package structure:

```text
laclaugpt/
├── core/
├── schema/
├── analysis/
├── codebook/
├── provenance/
│
└── adapters/
    ├── minet/
    ├── fourcat/
    ├── dats/
    ├── dna/
    ├── qdpx/
    ├── inception/
    ├── graphml/
    └── generic/
```

External tool dependencies SHOULD be optional extras wherever possible.

Example:

```text
pip install laclaugpt[minet]
pip install laclaugpt[qdpx]
pip install laclaugpt[dna]
pip install laclaugpt[inception]
pip install laclaugpt[all]
```

---

# 26. Command-line interface

Recommended general CLI:

```bash
laclaugpt import <format>
laclaugpt analyse
laclaugpt validate
laclaugpt export <format>
```

Examples:

```bash
laclaugpt import minet corpus.csv -o corpus.jsonl
```

```bash
laclaugpt analyse corpus.jsonl -o analysis.jsonl
```

```bash
laclaugpt export qdpx analysis.jsonl -o project.qdpx
```

```bash
laclaugpt export dna analysis.jsonl -o statements.csv
```

```bash
laclaugpt export graphml analysis.jsonl -o discourse.graphml
```

Unix streams SHOULD be supported where feasible:

```bash
minet ... |
laclaugpt import minet --stdin |
laclaugpt analyse --stdin |
laclaugpt export csv --stdout
```

---

# 27. Priority implementation roadmap

## Phase 1 — Stable core interchange

Implement first:

```text
LaclauGPT IR JSON/JSONL
CSV importer/exporter
stable identifiers
evidence spans
provenance
review states
```

---

## Phase 2 — Collection interoperability

Implement:

```text
minet adapter
4CAT adapter
Zeeschuimer/4CAT workflow
generic web/social-data importer
```

Minet integration SHOULD be particularly lightweight because its CSV/Unix design already maps naturally onto LaclauGPT's batch workflow.

---

## Phase 3 — Discourse-analysis interoperability

Implement:

```text
DNA/rDNA export
DATS adapter/plugin
```

---

## Phase 4 — Qualitative-analysis interoperability

Implement:

```text
REFI-QDA/QDPX export/import
QualCoder validation workflow
ATLAS.ti compatibility through QDPX
```

---

## Phase 5 — Annotation and validation

Implement:

```text
INCEpTION External Recommender
human annotation import
coder agreement datasets
adjudication
```

---

## Phase 6 — Network and visualisation

Implement:

```text
GraphML
GEXF
Cytoscape.js
Gephi workflow
```

---

# 28. Recommended canonical ecosystem

The preferred LaclauGPT ecosystem should therefore be:

```text
DATA COLLECTION

minet
Zeeschuimer
4CAT
    │
    ▼

LACLauGPT
theory-guided computational discourse analysis
    │
    ├──────────────┬──────────────┬─────────────┐
    ▼              ▼              ▼             ▼

DATS           DNA/rDNA        QDPX        INCEpTION
                                 │
                         ┌───────┼────────┐
                         ▼       ▼        ▼
                     ATLAS.ti MAXQDA QualCoder

    │
    ▼

GraphML / GEXF
    │
    ├── Gephi
    └── Cytoscape
```

The architectural objective is not to make LaclauGPT another monolithic social-science application.

The objective is:

> **LaclauGPT should become an interoperable theory-guided discourse-analysis engine that can be inserted into existing social-data-science workflows.**

Its distinctive responsibility is the computational operationalisation of discourse theory.

Collection should be delegated to specialised collectors where appropriate.

Human interpretation should remain interoperable with existing qualitative-analysis and annotation environments.

Network analysis should be delegated to established graph and discourse-network tools.

Visualisation should use generic graph and data formats.

This separation keeps LaclauGPT theoretically distinctive while allowing it to participate in a broader open social-data-science ecosystem.