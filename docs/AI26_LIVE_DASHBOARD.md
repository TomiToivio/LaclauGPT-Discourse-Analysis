# AI26 live dashboard

The AI26 dashboard is a near-real-time research view over **canonical LaclauGPT
annotations**. It is intentionally data-agnostic and contains no research corpus,
credentials, private hostnames or project secrets.

## Architecture

```text
AI26 collectors
  -> MongoDB ai26_sources
  -> local-Ollama analysis worker
  -> MongoDB ai26_annotations
  -> atomic canonical JSONL export (per arena)
  -> Streamlit live dashboard
  -> local SQLite researcher-review sidecar
```

The visualization layer does **not** query MongoDB directly and does not repeat
analysis logic. `ai26_runtime/export_dashboard_jsonl.py` is the boundary between
operational storage and visualization. Each arena export is written to a temporary
file and moved into place atomically so a polling dashboard never reads a file
while it is being truncated or partially rewritten.

The supplied `ai26-export.timer` runs every 10 seconds. The dashboard polls the
canonical export every 30 seconds by default; both values are deployment settings,
not theoretical requirements.

## What the live UI provides

The default `laclaugpt dashboard ...` launcher now opens the live dashboard. It
keeps the existing document inspector and append-only human-review sidecar, and
adds live aggregate views for:

- corpus freshness and analysis status;
- source/platform and language composition;
- candidate ideological formations over time;
- signifier trajectories and provisional role claims;
- the canonical discourse graph projections;
- explicit equivalence, difference and antagonism relations;
- Palonen Frontier elements;
- actor/source-author exploration;
- first-observed signifiers and formation candidates;
- evidence-bearing relation tables with source document IDs.

The formation view is dynamic. No fixed list such as accelerationist, critical,
doomer or populist is required by the dashboard. Those labels can appear when
they are present in canonical analysis output, while new formation labels remain
visible automatically.

All counts are corpus counts. They must not be read as public opinion or as proof
of theoretical importance. Frequency, graph degree and model-reported confidence
do not establish nodal status, floating/empty signification, antagonism, affective
investment, polarisation or hegemony.

## Running locally

Install the normal visualization extra:

```bash
python -m pip install -e ".[visualization]"
```

Launch an existing canonical arena export:

```bash
laclaugpt dashboard collection-data/dashboard/elites.jsonl \
  --project ai26 \
  --arena elites
```

The dashboard can start with an empty JSONL file. With live polling enabled it
will show a waiting state and populate when canonical annotations are exported.
No synthetic corpus is required.

For researcher coding:

```bash
laclaugpt-dashboard collection-data/dashboard/elites.jsonl \
  --project ai26 \
  --arena elites \
  --reviewer reviewer-a
```

`--blind-initial` continues to suppress model-derived aggregate vocabularies and
codings. In blind mode the live dashboard exposes operational/source coverage but
not formation, signifier or graph views.

## AI26 runtime environment

The dashboard process itself only needs the canonical export path. The MongoDB
export process uses the existing AI26 runtime configuration:

- `AI26_CONFIG`: private AI26 YAML containing the MongoDB URI;
- `AI26_MONGO_DATABASE`: MongoDB database name, default `laclaugpt`;
- `AI26_DASHBOARD_EXPORT_ROOT`: export directory, default
  `collection-data/dashboard` under the repository;
- `LACLAUGPT_ROOT`: optional repository-root override.

Do not commit the private AI26 YAML or credentials.

## MongoDB indexes and migrations

No schema migration is required for the live dashboard.

For a growing deployment, these indexes are useful operationally and can be
created after checking the existing database for duplicates and local naming
constraints:

```javascript
db.ai26_annotations.createIndex({created_at: 1})
db.ai26_annotations.createIndex({document_id: 1, run_id: 1})
db.ai26_sources.createIndex({native_id: 1})
db.ai26_sources.createIndex({"metadata.arena": 1, analysis_status: 1, collected_at: 1})
```

They are performance recommendations, not prerequisites for correctness.

## Research safeguards

The live layer follows `THEORY.md` and the repository invariants:

- evidence remains attached to theoretical claims;
- document-level empty/floating/hegemonic claims stay provisional;
- negative sentiment is not antagonism;
- sentiment polarity is not affective investment;
- graph layout, centrality and frequency are descriptive only;
- actor/formation associations are observations in the filtered corpus, not fixed
  identities;
- machine analysis remains human-reviewable and rejectable.

The evidence/review section is deliberately **not** auto-refreshed while a
researcher is typing. Live aggregate panels poll independently; the evidence
snapshot reloads on a normal Streamlit rerun or the explicit reload button.

## Tests

Relevant regression coverage includes:

```bash
python -m pytest -q tests/test_live_visualization.py tests/test_dashboard_sync.py
python -m pytest -q tests
```

The helper tests use small in-memory synthetic rows only. They do not ship an AI26
research dataset.

## Current limitations

- The live dashboard polls canonical JSONL rather than MongoDB change streams.
- Sidebar option lists are built on the latest full Streamlit rerun, so a brand-new
  actor/signifier may appear in live charts before it appears in a sidebar filter.
- The Plotly/NetworkX graph remains intentionally bounded and descriptive rather
  than a full Cytoscape-style graph workstation.
- Equivalence components visualize explicitly coded equivalence edges; they do not
  automatically validate a Laclaudian chain of equivalence.
- Cross-filtering is shared through sidebar filters rather than click-to-filter
  events between every Plotly panel.

## Recommended next steps

1. Add a corpus-level validated-claim layer for floating/empty signifiers,
   persistent frontiers and hegemonic candidates once validation semantics are
   stable.
2. Add optional Cytoscape/Sigma rendering if graph interaction becomes more
   important than keeping dependencies minimal.
3. Add incremental server-side aggregate snapshots if corpus size makes full JSONL
   reloads expensive.
4. Add URL/deep-link state for reproducible filtered research views.
5. Add researcher adjudication views for competing model and human interpretations.
