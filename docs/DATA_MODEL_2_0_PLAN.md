# LaclauGPT Data Model 2.0 — Architecture Plan (2026-09-06)

**Trigger:** maintainer directive — design the data model for LaclauGPT with:
MongoDB/ArangoDB as the scraped-data store on GPU machines (Laskin, CSC Pouta),
CSV+SQLite fallback and remote-DB connectivity on CSC Roihu, Context Memory
(GraphRAG-style) for the analysis stage, Palonen's Formula of Populism and
Laclau's core concepts in the schema, DNA compatibility with import/export,
Argdown compatibility, 4CAT/Zeeschuimer and DATS compatibility, spaCy/textnets/
NetworkX/PathPy/minet installed INTO the model, multimodal (TikTok) + text
(X, blogs) support, legacy-field compatibility (sentiment_target positive/
negative/neutral, topic, entity), unique source URL dedup, variable platform
metadata, and ValueFlows alignment for the Lindgren political-economy layer.

**Status of this document:** plan (v1.0). Implementation follows in stages;
each stage lands with tests in `tests/`.

---

## 0. What already exists (build ON this, not beside it)

The AI edition already has a validated canonical model
(`laclaugpt_model/`, 21 tests) and a Context Memory module
(`laclaugpt_memory/`) that already solved the entity-explosion problem.
Data model 2.0 **extends** these; it does not replace them.

| Existing | Role | 2.0 disposition |
|---|---|---|
| `laclaugpt_model/` (7 Pydantic types + store.py + projections.py + lenses.py) | canonical data model, SQLite+Parquet, NetworkX projections, ANT/VF lenses | **core stays**; gains DB backends, spaCy/textnets/PathPy adapters, Argdown/DNA round-trips |
| `laclaugpt_memory/` (Context Memory) | codebook, resolution loop, aliases, temporal drift, provenance, embeddings | **stays**; becomes the context layer for analysis runs (paper §3.4 stage 3); optionally mirrored into ArangoDB |
| `laclaugpt_interchange/` (v1.2 JSONL) | review-first interchange format | **stays** as the interop pivot; gains Argdown + DNA 1:1 mappings |
| `dna_adapter/`, `dats_adapter/`, `fourcat-processor/`, `minet_adapter/`, `inception_adapter/` | five adapters already working | **stays**; wire the new model fields into them |
| `pipeline.py` stages | evidence-first analysis | gains Context-Memory injection (GraphRAG) at stages 2–5 |

## 1. Storage architecture — three profiles, one model

The Pydantic model is the contract. Storage is pluggable behind it:

```text
                    ┌──────────────────────────┐
                    │   laclaugpt_model (API)  │
                    │  Pydantic types + repos  │
                    └──────────┬───────────────┘
                               │  Repository interface (protocol class)
          ┌────────────────────┼───────────────────────┐
          ▼                    ▼                       ▼
   SqliteRepo            ArangoRepo                MongoRepo
   (Roihu default,       (Laskin/Pouta primary,    (optional, scrapers
   zero-dep fallback)     remote from Roihu)        already emit it)
          │                    │                       │
          ▼                    ▼                       ▼
   documents.db          arangodb://laskin:8529   mongodb://pouta:27017
   + Parquet bulk        graph: statements↔concepts
```

### 1.1 Repository protocol (`laclaugpt_model/repo.py`)

```python
class Repo(Protocol):
    def put_document(self, d: Document) -> None: ...
    def get_document(self, doc_id: str) -> Document | None: ...
    def find_by_url(self, url: str) -> Document | None: ...   # dedup key
    def put_statement(self, s: Statement) -> None: ...
    def iter_statements(self, run_id: str | None = None) -> Iterator[Statement]: ...
    def put_analysis_result(self, r: AnalysisResult) -> None: ...
    def bulk_export(self, path: Path, fmt: str) -> Path: ...   # parquet/jsonl/csv
```

Implementations ship in 2.0:

1. **`SqliteRepo`** — today's `store.py` wrapped in the protocol. The
   canonical zero-dependency path: works on Roihu login/compute nodes,
   laptop, anywhere. Parquet/JSONL/CSV bulk export unchanged.
2. **`ArangoRepo`** — primary for Laskin and Pouta where the server
   already runs. Mapping:
   - collections: `documents`, `actors`, `concepts`, `annotations`,
     `statements`, `relations` (edge collection), `analysis_runs`,
     `analysis_results`
   - graph `laclaugpt_graph`: edges `statements → concepts` (stance
     qualifies the edge), `relations` as native edges, `annotations →
     documents`
   - **Context Memory mirror**: codebook objects (entities, topics,
     signifiers, actors, formations) live as vertices with
     `_key = obj_id` (E001, S017, F003…), so the resolution loop's
     canonical glossary is queryable with AQL and the alias edges
     (`alias_of`, `merged_into`, `supersedes`) are traversable —
     this IS the GraphRAG layer, below.
3. **`MongoRepo`** — for scraper fleets that already write MongoDB
   (Zeeschuimer/4CAT exports land there on some deployments). Same
   protocol; the dedup index on `url` is a Mongo unique index.
4. **`RemoteRepo`** — a thin HTTP/REST façade (FastAPI, stdlib client)
   so a Roihu compute job talks to the Laskin/Pouta ArangoDB without
   installing `python-arango` in the Roihu venv: `RemoteRepo(base_url,
   token)` speaks the same Repo protocol over HTTPS. Fallback ladder
   on Roihu: RemoteRepo → SqliteRepo(local scratch) → CSV files.

**Config (`run_config.py` extension):**

```yaml
storage:
  profile: roihu          # roihu | laskin | pouta | laptop
  backend: sqlite         # sqlite | arango | mongo | remote
  sqlite_path: /scratch/${SLURM_JOB_ID}/laclaugpt.db
  arango_url: https://laskin.example:8529
  arango_db: laclaugpt
  mongo_url: mongodb://pouta.example:27017
  dedup:
    strategy: url_first   # url_first | content_hash | both
```

### 1.2 Unique source URL + dedup (maintainer requirement)

- `Document.url` is the **primary natural key**: `find_by_url` checked
  on ingest; UNIQUE index in SQLite; unique index in Mongo/Arango.
- URL canonicalization before comparison: lowercase scheme+host, strip
  `utm_*`/`fbclid`-class params, strip fragments, normalize trailing
  slash. Platform ID dedup rides in `metadata.platform_id`
  (TikTok item id, X tweet id) — **both** are checked; either hit
  dedups.
- Content-hash fallback (`content_hash()` already exists) for
  URL-less documents (podcast transcripts, PDFs): sha1 of
  (platform, author, timestamp, first 4096 chars).
- Ingest order per row: canonicalize → url lookup → platform_id
  lookup → content-hash lookup → insert with `ingest_run_id`.

### 1.3 Variable platform metadata (maintainer requirement)

`Document.metadata: dict[str, Any]` stays schema-free, but 2.0 adds a
documented **metadata profile registry** (`metadata_profiles.py`):

- `tiktok_profile`, `x_profile`, `blog_profile`, `rss_profile`,
  `parliamentary_profile` — each lists: required keys, optional keys,
  types, and which keys are *analysis-relevant* (language, country,
  engagement metrics are NOT analysis-relevant but ARE provenance).
- Validation is **advisory**: missing keys are recorded in the
  document's `metadata._profile_gaps` list, never rejected (TikTok
  mobile recordings have almost nothing; blogs have RSS-only fields).
- The `analysis_run.parameters` records which profile was in force —
  so a run that happened without platform metadata is knowable
  afterwards. (Paper §4.1: "Reports should document duplication,
  missing material, uneven actor visibility".)

## 2. Context Memory as GraphRAG — decision and design

**Maintainer question: "Analyysiin pitää tosiaan laittaa Context Memory
(Graph Rag). Vai onko parempaa?"** Answer: **yes — Context Memory IS the
right mechanism; pure vector-RAG would be the worse one.** Reasons,
from the 2.0 memory module's own history:

1. The problem stage 2–5 face is **controlled-vocabulary drift within
   a run** ("Musk" vs "Elon Musk" vs "Elon Musk (Twitter owner)") —
   that is a canonical-glossary problem, not a corpus-recall problem.
2. Political meaning is **relational** (Laclau: value through
   difference): "AI_SAFETY" means something different in 2023 than in
   2025 (temporal table already handles this). Vector similarity
   flattens exactly the differences the theory cares about.
3. Evidence-quotes must remain **exact spans** (paper: mechanical
   `evidence_is_in_source` check). A vector store returns chunks, not
   spans.

So 2.0 implements **GraphRAG = Context Memory + graph projection**:

```text
Stage 2 (describe)  → retrieves: codebook objects relevant to the doc
                      (exact/alias/fuzzy/embedding — existing ladder)
Stage 3 (theoretical codes) → every candidate carries codebook obj_id
                      references; NEW votes create PROVISIONAL objects
Stage 4 (resolve)   → resolution loop unchanged; merges recorded
Stage 6 (corpus synthesis) → the memory graph is PROJECTED (not the
                      source of truth): signifier co-occurrence over
                      statements, formation articulation counts
```

GraphRAG materialization (new, `laclaugpt_model/graphrag.py`):

- **Store of truth stays relational/SQLite/Parquet** (already the
  design rule: Neo4j-style graphs are projections, never storage).
- `build_context_graph(run_id)`: NetworkX graph whose vertices are
  codebook objects (canonical + provisional) with
  `state`, `usage_count`, `first_seen`, `last_seen`; edges:
  `alias_of`, `merged_into`, `co_occurs_in_doc`, `temporal_relation`
  (with period attributes). Persisted as GEXF + reused by textnets.
- **Retrieval for LLM prompts**: `context_for(doc_text, k) -> str` —
  exact/alias matches first (deterministic), then embedding-neighbor
  codebook entries with their state + definition + last temporal
  relation. Injected into stage prompts as a compact context block.
  This kills entity/topic/sentiment duplication at the SOURCE: the
  model is shown the canonical labels before it invents variants.
- **Misconception suppression** (maintainer's "päästään eroon
  entity/topic/sentiment-monistumisesta ja väärinkäsityksistä"):
  - `is_sentiment_target` flag on codebook C-kind objects; the
    legacy `sentiment_target` value maps to them, never duplicated.
  - The prompt context block states the canonical set explicitly and
    the pipeline validates returned labels against it (unknown labels
    → PROVISIONAL + flagged, never silently merged).

## 3. Theory schema — Laclau concepts + Palonen's Formula

The canonical model is theory-light **by design** (anti
theory-forcing, paper §3.4). 2.0 adds a **theory vocabulary layer**
that lives in `laclaugpt_model/laclau.py` — typed *labels and
validation*, not new storage types:

### 3.1 Concept vocabulary (validated against the codebook)

```python
LaclauRole = Literal[
    "nodal_point",            # partial fixation within a discourse
    "floating_signifier",     # contested between projects
    "empty_signifier",        # represents an equivalential chain
    "master_signifier",
]
RelationRole = Literal[
    "equivalence", "difference", "antagonism",
    "articulation",           # the productive practice itself
]
```

Rules carried forward from the paper (and enforced in tests):

- nodal/floating/empty are **roles a signifier plays**, recorded as
  `AnalysisResult(classification=...)` with evidence — never node
  subtypes, never inferred from ambiguity alone (§3.1: "Mere breadth,
  vagueness, or multiple meanings establishes none of these
  functions").
- `equivalence` ≠ `difference` ≠ `antagonism`: antagonism requires a
  **constitutive limit** (a represented preventer), not just
  negativity; policy disagreement is not antagonism (§3.1).
- Affect polarity is NEVER inferred from Us/Frontier side membership
  (the `Affect` interchange rule; `from_memory_results` bug class).
- Hegemony is a corpus-level `AnalysisResult` requiring uptake/
  stabilisation evidence — never a per-document label (§3.1).

### 3.2 Palonen's Formula of Populism — first-class structure

```python
class FormulaOfPopulism(BaseModel):
    """Populism = Us^{Affects_1} + Frontier^{Affects_2}
    Interpretive device (paper §3.1), not a numerical model."""
    us_elements: list[str]        # codebook/actor obj_ids
    frontier_elements: list[str]  # obj_ids forming the constitutive boundary
    us_affects: list[str]         # affect obj_ids (C-kind)
    frontier_affects: list[str]   # affect obj_ids
    applicable: bool              # False = document supports no populist reading
    non_populist_reason: str = "" # why not (policy disagreement etc.)
    evidence_ids: list[str]       # statements/annotations backing it
    analysis_run_id: str | None
    confidence: float = 0.0       # model self-report, evaluated separately
```

- Stored in SQLite (`formulas` table) and in the interchange schema
  (v1.3 field `formula_of_populism`), so legacy consumers see
  `us/frontier/affects` exactly as before (compat below).
- **Affect-side vs polarity stays orthogonal**: `side ∈ {us, frontier}`
  and `polarity ∈ {positive, negative, neutral, ""}` (legacy) — never
  derived from each other (existing rule, now tested at the schema
  level).
- `applicable=False` with a reason is the honest abstention the paper
  requires ("finding an in-group and an opponent initiates assessment;
  it does not mechanically establish populism").

## 4. Legacy compatibility (maintainer requirement: "PIDETÄÄN vanhat")

The old v1 fields remain **first-class, mapped**:

| Legacy field | 2.0 home | Notes |
|---|---|---|
| `sentiment_target` (positive/negative/neutral) | `Statement.stance` + `stance_score` AND `Annotation(type=SENTIMENT)` | kept verbatim in `attributes.legacy.sentiment_target`; the three-way value is coarse-bucketed from `stance`/`polarity` when missing |
| `topic` | codebook T-objects + `Annotation(type=CONCEPT)` | canonical topics, not free strings |
| `entity` | codebook E-objects + `Annotation(type=PERSON/ORG/…)` | resolution loop assigns E-ids |
| `sentiment` scalar | `polarity` (−1..1) | legacy three-way = bucket of polarity |
| Legacy CSV columns (v1 collections) | `metadata_profiles.x_profile/tiktok_profile` | mapped at ingest, originals kept in `metadata.raw` |

Rule: **nothing from v1 is dropped**; legacy fields ride in
`attributes.legacy.*` on the new types, and adapters can re-export
them losslessly. The old `sentiment_target positive/negative/neutral`
vocabulary is preserved exactly as a `Literal` type.

## 5. spaCy entities: Place/Event with coordinates and dates

spaCy NER produces types the model should keep typed, not flattened to
"entity". 2.0 adds:

```python
class GeoAnnotated(BaseModel):      # mixin
    lat: float | None = None
    lon: float | None = None
    geo_confidence: float | None = None
    geocoded_by: str | None = None  # profile name / geocoder id

class EventDetails(BaseModel):
    start_date: str | None = None   # ISO; spaCy DATE + normalization
    end_date: str | None = None
    location_ref: str | None = None # Place concept obj_id
```

- `AnnotationType.PLACE` and `AnnotationType.EVENT` added to the enum;
  their `attributes` carry the details above.
- **Geocoding is opt-in and provenance-stamped** (`geocoded_by`,
  `geo_confidence`); coordinates may come from spaCy+Wikidata lookup,
  an external geocoder, or platform metadata (TikTok location tags).
  Never silently merged with the surface form.
- Event annotations normalize spaCy DATE/_TIME mentions into ISO dates
  where the context allows (published_at as anchor), keep raw text
  otherwise. Uncertainty is recorded, never guessed.
- These feed the **Place/Event** projections: `place_event_graph()`
  (events at places over time) — a new lens, next to ANT/ValueFlows,
  useful for data-centre protests and physical AI mobilisation
  (paper §2.3 "data-centre development" arena).

## 6. Library integration — installed INTO LaclauGPT

All of these become direct model dependencies (`pyproject.toml`
extras), each wrapped by a thin adapter in the model package — no
LaclauGPT code touches their native APIs directly:

| Library | Adapter | Feeds |
|---|---|---|
| **spaCy** (+ en_core_web_sm, fi_core_web_sm) | `spacy_adapter.py`: doc → Annotations (PERSON/ORG/PLACE/EVENT/DATE) with spans | stage 1–2 enrichment; Place/Event details (§5) |
| **textnets** | `textnets_adapter.py`: tidy-text from documents → Corpus → Textnet → clusters/modularity/birank; **API notes: Corpus(pd.Series), Textnet(c.tokenized()), clusters/modularity/top_degree are attributes** | signifier co-occurrence networks + communities; GEXF out |
| **NetworkX** | already the projection engine (`projections.py`) — stays | all lenses |
| **PathPy** | `pathpy_adapter.py`: statements over time → temporal paths (actor→concept adoption cascades, signifier diffusion) | temporal_slices extension; diffusion analysis for how articulations TRAVEL across arenas (paper §4.1) |
| **minet** | `minet_adapter.py` already exists in the repo — moves under the model package, gains scrape/fetch CLI passthrough with provenance rows | collection side (URL dedup uses §1.2) |

Install profile (single command, per machine):

```bash
# laptop / Roihu (CPU ok)
pip install -e ".[analysis]"        # spacy+models, textnets, networkx, pathpy, minet, pandas<3
# Laskin / Pouta (GPU + servers)
pip install -e ".[analysis,server]" # + python-arango, pymongo, fastapi
```

PathPy note: optional extra; the temporal-projection adapter degrades
to NetworkX-only when absent (same optional-deps pattern as
`laclaugpt_primitives` — Slurm jobs never die on an optional library).

## 7. DNA compatibility (maintainer requirement)

`dna_adapter/` already round-trips documents/statements with
char-offset anchors. 2.0 wiring:

- **Export**: `Statement` → DNA statement (actor × concept × time,
  evidence quote with Start/Stop offsets); `AnalysisResult
  (classification in {nodal_point, empty_signifier_candidate,
  floating_signifier})` → DNA **concept descriptions** (NOT DNA node
  types — DNA has no such types; roles live in concept notes, same
  anti-reification rule).
- **Import**: DNA documents → Documents; DNA coder concepts →
  PROVISIONAL Concepts; DNA statements → Statements with
  `attributes.legacy.dna_statement_id`.
- **Agreement/congruence**: DNA's US/FRONTIER/AGREEMENT variables map
  to the FormulaOfPopulism `us/frontier` sides — export writes the
  mapping; import reads it back.
- New: **round-trip test** (`tests/test_dna_roundtrip.py`): canonical
  → DNA → canonical yields identical statements modulo ids.

## 8. Argdown compatibility (maintainer requirement)

Argdown = structured argument maps (claims, attacks/supports,
statements-references). Natural fit for Laclaudian frontiers:

- `argdown_adapter.py` — **export**:
  - each `Statement(actor, concept, stance)` → Argdown proposition
    `[claim-id]: text (actor, date)` with evidence reference
  - `Relation(type in {opposes, supports, agrees_with, antagonism})`
    → `+`/`-` relations (attacks/supports)
  - FormulaOfPopulism → an Argdown **argument** block:
    `<populist-reading>: Us-element + frontier-element ⇒ populist
    articulation` with premises = evidence statements
  - equivalences → `+` chains; the frontier's antagonism → `-` at the
    frontier boundary
- **Import**: Argdown propositions → PROVISIONAL Statements
  (actor = source reference, concept = resolved codebook entry),
  attack/support edges → Relations. Loses: affective investment
  (not an Argdown primitive) — recorded as `attributes.argdown.losses`.
- Round-trip test: canonical → Argdown → parse → canonical (structural
  identity on statements/edges; formatting ignored).

## 9. 4CAT / Zeeschuimer compatibility (maintainer requirement)

Already working (`fourcat-processor/`, `z4sync`); 2.0 formalizes:

- **Import**: 4CAT NDJSON dataset → Documents with
  `metadata_profiles.<platform>_profile` applied; `platform_id`
  extracted for §1.2 dedup; thread structure (`parent_id`) from
  4CAT's `thread` fields.
- **Export**: interchange JSONL → 4CAT-compatible NDJSON (the
  processor's output format), so results can be browsed IN 4CAT with
  LaclauGPT annotations attached.
- Zeeschuimer raw captures (`metadata.raw`) preserved untouched —
  provenance rule: derived representations are labelled, never
  overwrite the capture (paper §4.3).

## 10. DATS compatibility (maintainer requirement; ANT "antaa olla")

`dats_adapter/` already imports DATS documents and exports
concept-over-time. 2.0 notes:

- DATS study/distribution metadata maps to `AnalysisRun` +
  `Document.metadata.dats` (study-level provenance rides with the
  dataset, not the model).
- **ANT**: already implemented as the `ant_actant_graph` lens
  (actants incl. datasets/GPUs/prompts — the "SNA ja ANT livahti
  jo" note). Stays a **lens, not an ontology** — no new storage.
  Maintainer: "DATS-yhteensopivuus ja tuonti/vienti. Siinä on ANT!
  Mutta antaa olla." → confirmed: keep as-is, no ANT-driven schema
  changes.

## 11. ValueFlows for the political-economy layer (maintainer requirement)

`lenses.py` already has `vf_economic_graph`. 2.0 ties it to Lindgren's
Political Economy of AI level (paper §2.1 "ideologies shaping AI"):

- `vf_role` assignments (agent / resource / process) gain a small
  **type vocabulary**: `human_labour, data, compute, model, capital,
  infrastructure, attention` — documented against VF's
  EconomicResource/Process/Agent classes.
- Data-centre example ships as a worked lens: OpenAI (agent) →
  `consumes` → electricity (resource); worker → `performs` →
  labelling (process) → `produces` → training-data (resource) →
  `inputs_to` → model. This is the concrete bridge from discourse
  statements ("AI requires massive compute") to political economy
  (who owns the compute).
- Stored as Relations with `properties.vf = {...}`; projected on
  demand; never mixed into the discourse graph (separate lens view).

## 12. Multimodal + text documents (maintainer requirement)

`Document.type ∈ {post, article, comment, transcript, video, image,
manifesto, speech, other}` already covers both. 2.0 adds explicit
**modality provenance** (paper §4.3: transformed material must stay
labelled):

```python
class Transformation(BaseModel):
    kind: Literal["asr", "ocr", "frame_description", "translation",
                  "keyframe", "metadata_extraction"]
    tool: str            # faster-whisper large-v3, PaddleOCR, gemma4…
    tool_version: str | None
    produced: str        # artifact id (document/annotation/transcript)
    input_document_id: str
    created_at: datetime
    notes: str = ""
```

- A TikTok video document has child documents (transcript via ASR,
  frame descriptions via VLM) linked by `derived_from` Relations +
  `Transformation` records; the analysis_run that consumed the
  transcript records WHICH representation it used.
- Text-only sources (X, blogs) simply have zero transformations.
- The `transformations` table (new) enables the paper §4.3 validation
  design: "A validation sample should compare transformed material
  with the original media".

## 13. New/changed tables summary (SQLite DDL delta)

```sql
CREATE TABLE formulas (            -- Palonen Formula instances
  id TEXT PRIMARY KEY, document_id TEXT, us_elements TEXT,
  frontier_elements TEXT, us_affects TEXT, frontier_affects TEXT,
  applicable INTEGER, non_populist_reason TEXT,
  evidence_ids TEXT, analysis_run_id TEXT, confidence REAL);
CREATE TABLE transformations (     -- multimodal provenance (§12)
  id TEXT PRIMARY KEY, kind TEXT, tool TEXT, tool_version TEXT,
  produced TEXT, input_document_id TEXT, created_at TEXT, notes TEXT);
-- indexes:
CREATE UNIQUE INDEX idx_documents_url ON documents(url);
CREATE INDEX idx_documents_platform_id ON documents(metadata→'$.platform_id');
CREATE INDEX idx_statements_run ON statements(analysis_run_id);
```

(Parquet/Mongo/Arango mirrors carry the same shapes; `metadata`
platform-id index is a generated column in SQLite 3.38+.)

## 14. Interoperability matrix (maintainer requirement)

| Target | Direction | Via | Status |
|---|---|---|---|
| DNA 3.1.x (.dna SQLite) | import + export | `dna_adapter/` | exists; 2.0 adds round-trip test + Formula↔US/FRONTIER mapping |
| ATLAS.ti (.qdpx + CSV) | export | `dna_adapter` (REFI-QDA) | exists; CSV fallback guaranteed |
| Argdown (.ad) | import + export | `argdown_adapter.py` | **new in 2.0** |
| 4CAT / Zeeschuimer | import (+ processor output) | `fourcat-processor/`, `z4sync` | exists; profile registry formalizes metadata |
| DATS | import + concept-over-time export | `dats_adapter/` | exists; ANT stays a lens |
| INCEpTION (UIMA XMI) | export + corrections import | `inception_adapter/` | exists |
| minet | import + CSV export | `minet_adapter/` | exists; moves under model package |
| textnets | import (tidy-text) + GEXF out | `textnets_adapter.py` | **new in 2.0** |
| NetworkX / PathPy | native projections | `projections.py`, `pathpy_adapter.py` | NX exists; PathPy new |
| ValueFlows (REA) | lens export | `lenses.vf_economic_graph` | exists; §11 vocabulary added |
| GraphML/GEXF/GraphML+spans | export | projections | exists |

**InfraNodus**: excluded by maintainer ruling (not open source) — no
adapter, no dependency.

## 15. Paper alignment check (Revised version, 2026-09-06)

Every 2.0 feature maps to a paper commitment:

| Paper (Revised) section | Requirement | 2.0 answer |
|---|---|---|
| §3.4 workflow 6 stages | evidence-linked stages | existing pipeline; §2 context injection at 2–5 |
| §3.1 concepts | nodal/floating/empty as functions, evidence | §3 vocabulary + AnalysisResult-only rule |
| §3.1 Formula of Populism | conditional component, interpretive device | §3.2 `FormulaOfPopulism` with `applicable=False` abstention |
| §3.4 traceability | model+prompt+uncertainty+review on every code | existing `analysis_runs` + interchange v1.2; unchanged |
| §4.1 arenas + metadata variability | declared observation period, missing material documented | §1.3 profiles + `_profile_gaps` |
| §4.1 dedup/duplication | "Reports should document duplication" | §1.2 url/platform-id/content-hash dedup + counts in run report |
| §4.2 abstention evaluation | coverage vs error trade-off | FormulaOfPopulism.applicable + codebook abstentions, per-run coverage stats |
| §4.3 multimodal provenance | transformations labelled | §12 `Transformation` records |
| §4.4 data stewardship | infrastructure-appropriate processing | §1 profiles: Roihu scratch + remote-DB tokens, no third-party cloud |
| §2.1 political economy | ValueFlows/Lindgren layer | §11 |

## 16. Implementation roadmap (staged, each with tests)

```text
Stage A  repo.py protocol + SqliteRepo wrap + url/platform dedup +      [small]
         profiles registry                       tests: test_repo_dedup.py
Stage B  laclau.py vocabulary + FormulaOfPopulism + formulas table +    [small]
         interchange v1.3 field                  tests: test_formula.py
Stage C  spacy_adapter (incl. PLACE/EVENT geocoding hooks) +            [medium]
         transformations table                   tests: test_spacy_adapter.py
Stage D  graphrag.py: context_for() + build_context_graph() +           [medium]
         codebook mirroring                      tests: test_graphrag.py
Stage E  ArangoRepo + RemoteRepo + config profiles                      [medium]
                                                 tests: test_repo_backends.py (mock server)
Stage F  textnets_adapter + pathpy_adapter (optional degrade) +         [medium]
         GEXF outputs                            tests: test_textnets.py
Stage G  argdown_adapter import/export + round-trip                     [small]
                                                 tests: test_argdown.py
Stage H  dna round-trip hardening + DATS/4CAT field wiring +            [small]
         minet move                              tests: test_dna_roundtrip.py
Stage I  pyproject extras + install docs per machine (laptop/Laskin/    [small]
         Pouta/Roihu)                            docs: INSTALL.md
```

Order note: A+B unblock everything else; D is the heart (Context
Memory → analysis); E is the only networked piece and is mock-tested
first, real-server-tested on Laskin afterwards.

## 17. Open questions (maintainer input welcome, not blocking)

1. **ArangoDB graph vs relational truth**: my recommendation is
   relational/SQLite stays the store of truth and Arango is a
   *queryable mirror* — agree? (Paper's rule: graphs are projections.)
2. **MongoDB**: needed only if a scraper fleet really writes it — keep
   MongoRepo dormant until a real source exists?
3. **Geocoder choice** for Place coordinates: Wikidata (open, no key)
   vs Nominatim (OSM, usage policy) vs platform metadata only?
4. **PathPy version pin**: 2.x API differs from 1.x — pin 2.x?
5. **Formula of Populism in ATLAS.ti export**: as coded segments on
   Us/Frontier elements (current dna-style) or as a document-level
   comment? Current: segments; reviewer-friendly either way.
```

Tämä suunnitelma on kirjoitettu tiedostoon:
`laclaugpt/laclaugpt-2.0/laclaugpt-discourse-analysis-AI/docs/DATA_MODEL_2_0_PLAN.md`