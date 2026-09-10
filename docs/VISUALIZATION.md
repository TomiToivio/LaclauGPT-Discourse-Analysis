# LaclauGPT visualization

LaclauGPT ships an optional Streamlit visualization layer for exploring canonical
interchange output. It is inspired by the older EP2024 video dashboard, but it is
not tied to one election, country, platform, classifier or database table.

## Runtime boundary

**Do not run the visualization on CSC Roihu.** Roihu is the batch-analysis side of
the architecture. The interactive dashboard is designed for:

- a local workstation or laptop; or
- a persistent Linux web server / virtual machine such as CSC Pouta.

The launcher rejects Roihu markers and active Slurm allocations. A normal pattern
is therefore:

1. run LaclauGPT analysis on Roihu;
2. copy/sync the resulting canonical `.jsonl`/`.ndjson` file to the local machine
   or Pouta VM;
3. launch the dashboard there.

This separation is deliberate. Streamlit is a persistent interactive web process,
not a batch/HPC workload.

## Installation

Visualization dependencies are optional:

```bash
python -m pip install -e ".[visualization]"
```

This adds Streamlit and Plotly. NetworkX and pandas are already core dependencies.

## Launch locally

```bash
laclaugpt dashboard data/annotations.jsonl \
  --project ai26 \
  --arena elites
```

The equivalent standalone command is:

```bash
laclaugpt-dashboard data/annotations.jsonl \
  --project ai26 \
  --arena elites
```

The default bind address is `127.0.0.1:8501`.

For researcher coding, use a stable local pseudonym rather than a personal name:

```bash
laclaugpt-dashboard data/annotations.jsonl \
  --project ai26 \
  --arena elites \
  --reviewer reviewer-a \
  --blind-initial
```

`--blind-initial` hides model-derived analytical output and other reviewers'
assessment records until the researcher explicitly reveals the selected document
for comparison/adjudication.

## Launch on a Pouta/Linux web server

After copying the analysis output to the server:

```bash
laclaugpt dashboard /srv/laclaugpt/annotations.jsonl \
  --project ai26 \
  --arena elites \
  --host 0.0.0.0 \
  --port 8501 \
  --review-db /srv/laclaugpt/reviews.sqlite3
```

For an internet- or institution-facing deployment, put Streamlit behind the
server's normal HTTPS reverse proxy and authentication/access-control layer. Do
not expose research data or an unauthenticated Streamlit port directly to the
public internet. Keep project data, review databases, credentials and TLS keys
outside the repository.

A production Pouta deployment may run the command under `systemd` or another
service manager. The repository intentionally does not ship site-specific IPs,
credentials, firewall rules or authentication secrets.

## Project and profile awareness

The dashboard uses the same canonical configuration hierarchy as analysis:

- `config/projects/<project>.yaml` supplies the project title and authoritative
  `analysis` module switches;
- `config/arenas/<arena>.yaml` supplies the arena/profile identity and label;
- the stable dashboard profile identity is `<project>:<arena>`.

The visible analytical tabs are derived from those switches rather than being
hard-coded for AI26. For example:

- `entities: true` enables entity views;
- `topics: true` enables topic views;
- `laclau: true` enables signifier and articulation-network views;
- `palonen: true` enables Us/Frontier and Formula-of-Populism views;
- `sociotechnical_imaginaries: true` enables imaginary views;
- `palonen: true` enables the Affects view: affective investment is Laclaudian
  coding and follows the palonen stage, never the descriptive sentiment switch;
- `sentiment: true` enables only descriptive sentiment post-processing, which
  the dashboard keeps in its own family and never presents as affect;
- `temporal: true` enables time-series views when source timestamps exist.

A future project/profile therefore inherits the same visualization engine by
adding canonical project/arena profiles and producing standard interchange
annotations. It does not require a new dashboard function.

## Data contract

The dashboard consumes the current `laclaugpt_interchange.DocumentAnnotation`
JSONL/NDJSON output. It does not read a project-specific DuckDB table or make
project-specific MongoDB queries.

The flattened UI surface includes, when present:

- source platform, country, language, author, timestamp and URL;
- summary and provenance;
- entities and topics;
- signifiers and nodal-point candidates;
- signifier-role candidate confidence plus `needs_corpus_validation`;
- articulations and an aggregated articulation graph, including `claim_status`
  so quoted/reported/rejected/parodied material is visually distinguishable from
  asserted authorial speech;
- candidate discourses/formations;
- sociotechnical-imaginary **candidates**;
- Palonen Us/Frontier elements and classification/abstention, including
  `non_populist_reason` when a document is coded non-populist;
- affects;
- counter-evidence, evidence, uncertainty, prompt/model provenance and review
  status.

All aggregate frequency displays are descriptive. Frequency does **not** by
itself establish theoretical importance, nodal status, floating/empty status,
hegemony, or the corpus-level validity of an imaginary. The dashboard therefore
uses candidate language for theory-sensitive outputs and keeps corpus/human
adjudication visible as a separate requirement.

Filters are generic: free search, platform, language, country, author, model
review status, entity, topic and signifier. No country, party family, classifier
or platform is assumed.

## Canonical discourse graph views

Issue #84 adds a graph projection layer shared by analysis exports and
visualization. The visualization package does not create its own graph ontology.
`laclaugpt.visualization.graph.graph_projection_data()` calls the canonical
`laclaugpt.graph` builder and returns JSON-ready nodes/edges for the UI.

Available visualization projections are:

- `actor_signifier`: DNA-style actor/signifier network;
- `signifier_field`: articulation, equivalence, difference, antagonism and
  contextual signifier-role assignments;
- `formation_map`: candidate discourse/formation evidence map;
- `populism`: Palonen Us + Frontier + affective-investment graph;
- `temporal`: canonical graph retaining timestamp metadata for slicing;
- `evidence_claim`: theory-sensitive claims and their supporting evidence.

`graph_projection_options()` derives the available views from the project's
`laclau`, `palonen` and `temporal` switches. A disabled analytical family must not
reappear through visualization.

The canonical analysis pipeline also writes `.graph.json`, `.graph.graphml` and
`.graph.gexf` sidecars. The JSON form is the richest web-facing representation;
GraphML/GEXF are interoperability exports for NetworkX, visone, Gephi, Cytoscape
and related tools.

Graph layout is a visual aid, not a theoretical measurement. Node centrality,
visual size, frequency and geometric position do not by themselves establish
nodal status, empty/floating status, antagonism or hegemony. Those remain
specific evidence-backed analytical claims. See
[`DISCOURSE_GRAPH_SCHEMA.md`](DISCOURSE_GRAPH_SCHEMA.md).

## Researcher assessment history

Human assessment state is stored separately from canonical model output in a
local SQLite sidecar, by default next to the input file:

```text
annotations.jsonl.reviews.sqlite3
```

Canonical JSONL remains immutable. The assessment sidecar is append-only: saving
a new decision does not overwrite an earlier decision.

Each new assessment records:

- project and corpus/profile identity;
- canonical source `document_id`;
- analysis `run_id`;
- a SHA-256 fingerprint of the exact `DocumentAnnotation` artifact;
- reviewer ID/pseudonym;
- assessment target type (`document`, `code`, or `claim`) and target identifier;
- status, note and tags;
- record type (`assessment`, `revision`, or `adjudication`);
- timestamp;
- blind-initial-coding flag;
- `supersedes_id` for revisions;
- linked prior assessment IDs for adjudication.

Canonical memory/codebook identifiers such as `E001`, `T001` and `S001` are
reused for code-level targets. Relational claims receive deterministic target
identifiers that include the participating canonical IDs (for example an
articulation target).

### Independent coding and disagreement

Reviewers are separate dimensions of the assessment key. Two researchers may
therefore assess the same document/run/code independently. Their records never
replace each other. If they disagree, both original assessments remain in the
history even after a revision or adjudication is added.

A revision is a new record linked through `supersedes_id`; it does not edit the
prior row. An adjudication is a separate record linked to the prior assessment
IDs being compared. This keeps disagreement and decision history auditable.

### Run safety

The dashboard looks up an assessment using the exact project, corpus, document,
run, artifact fingerprint, reviewer and target. A decision from another run or
from a changed annotation artifact is therefore not silently applied to the
current output, even when one SQLite sidecar is intentionally reused across
runs.

### Blind initial coding

Blind initial coding is available from the sidebar or with `--blind-initial`.
While active, aggregate model-derived analytical fields are redacted and the
document detail view hides model summary, proposed discourse/populism codings,
model provenance and other reviewers' decisions. The reviewer sees only their
own assessment history.

The selected document can later be explicitly revealed for comparison and
adjudication. This is a UI/research-workflow boundary, not a claim that the
SQLite file itself is access-controlled; filesystem and server permissions still
matter.

### Export

The Review tab exposes the complete provenance fields and provides a CSV download.
In normal/revealed mode the export contains the full append-only history. While
blind mode is active, the table and download are restricted to the current
reviewer's records so peer decisions are not leaked through export.

### Legacy sidecars

Older sidecars used a `dashboard_reviews` table keyed only by `document_id` and
overwrote status/note/tags. On first open, those rows are copied into the new
append-only `review_assessments` table without deleting or changing the legacy
table.

Historical metadata that did not exist in the old schema is recorded explicitly
as `unknown`: project, corpus, run, artifact fingerprint and reviewer are never
invented. The original status, note, tags and timestamp are preserved. Migration
is idempotent, so reopening the same database does not duplicate migrated rows.

## What was intentionally not copied from EP2024

The reusable interaction pattern was retained, but these old assumptions are not
part of the new architecture:

- a fixed `ep24_new` DuckDB table;
- Finland as the default country;
- fixed `Far right` / `Centre right` / `Red-green` categories;
- ManifestoBERTa-specific tabs and filters;
- Whisper/video columns as mandatory fields;
- one particular MongoDB notes collection;
- embedded database host/user/password configuration;
- project-specific logo/auth files.

If a future project needs a specialized view, add it as a profile-driven optional
view over the canonical schema rather than forking the dashboard into a new
project-specific application.
