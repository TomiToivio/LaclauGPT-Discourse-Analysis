# Paper-implementation audit

Original audit date: 2026-09-04

Documentation reconciliation: 2026-09-07, re-audited against `main` commit
`a96ca67b887135d08c6d02b5a6c58a684450c887` (merge of PR #38, immediately
before the issue #36 documentation-reconciliation branch).

Current manuscript: [`paper/PAPER.md`](../paper/PAPER.md)

## Overall finding

The repository now contains a runnable, evidence-first document-level
pre-analysis pipeline aligned with the methodological claims of the manuscript,
plus a separate social-media collector subsystem. Corpus-level discourse
interpretation and human validation remain research activities and are not
represented as automated findings.

The codebase is in an architectural transition: `laclaugpt/` is the canonical
package surface for new code and orchestration, while the lower-level paper
pipeline still uses `pipeline.py`, `run_config.py`, `laclaugpt_memory/` and
`laclaugpt_interchange/`. Older packages such as `laclaugpt_model/` remain for
compatibility/migration and must not be confused with the canonical package
model under `laclaugpt/model/`.

## Current architecture

| Concern | Current implementation | Boundary/status |
|---|---|---|
| Public entry point | `python -m laclaugpt.cli` | Canonical CLI |
| Run orchestration | `laclaugpt/canonical_pipeline.py` + `laclaugpt/execution/` | Canonical dispatcher/checkpoint layer |
| Paper analysis | root `pipeline.py` | Current evidence-linked analysis implementation |
| Domain model for new package code | `laclaugpt/model/` | Canonical storage-neutral model |
| Persistent Context Memory used by paper pipeline | `laclaugpt_memory/` | Current codebook/resolution store |
| Batch interchange | `laclaugpt_interchange/` | Current schema **1.3** |
| Collector | `collector/` | Preferred systematic path: Firefox extension + Python backend |
| Older observation/graph model | `laclaugpt_model/` | Transitional compatibility layer |
| 4CAT processor | root `laclaugpt_processor.py` | Shipped compatibility processor; canonical pipeline parity remains separate work |

## Traceability matrix

| Paper or revised-method claim | Previous state | Current state | Remaining boundary |
|---|---|---|---|
| Three empirical arenas | YAML files existed but `pipeline.py` did not load them | Arena YAML configs are validated and executable through `--run-config`; package CLI accepts an explicit pipeline config | Final sampling frames and study-specific collection decisions remain researcher-controlled |
| AI-specific contextualisation | Arena configs reused a prior-election prompt | Separate AI elites, grassroots, parliamentary and general contestation backgrounds exist | Context/version registration should remain part of the study record |
| Source-grounded analysis | CSV source text was not read into analysis context | Common text/transcript/OCR/fieldnote columns are ingested; empty rows fail fast | Parent-thread reconstruction is stored but not automatically fetched |
| Stable document identity | Generic rows could collide on an empty TikTok-style key | Common durable IDs/URLs are used; otherwise a stable content hash is generated | Upstream collectors should still supply durable native IDs where possible |
| Articulation | No dedicated structured code | Source-target relations include articulation/equivalence/difference/antagonism with evidence | Relation validity requires human review |
| Nodal/floating/empty distinctions | AI could be pre-imposed as a fixed empty signifier | Situated role candidates carry rationale, evidence, confidence and corpus-validation flags | Floating/empty status requires comparative corpus evidence |
| Sociotechnical imaginaries | Seed labels only | Structured future, present diagnosis, technology role, human agency and evidence | Cross-document stabilisation remains a corpus/human task |
| Ideological formations | Fixed seed list encouraged direct classification | Formation candidates require supporting features, counter-evidence, evidence quote and confidence | Formation boundaries remain interpretive |
| Formula of Populism | Political items could be forced into Us/Frontier with predetermined affect polarity | Explicit non-populist outcome is possible; both sides require evidence; affect polarity is not inferred from side | Human validation decides borderline cases |
| Authorial position | Prompt warning only | Articulations/imaginaries distinguish asserted, quoted, reported, rejected, parodied and uncertain claims | Automatic speech-role accuracy must be evaluated |
| Evidence | Requested informally | Evidence quotation is structured and mechanically checked against source material | Paraphrased and multimodal evidence need specialised validation |
| Human validation | Repeated model uses could promote codes | Model repetition never promotes by itself; outputs remain PROVISIONAL until explicit review | Independent double coding/adjudication workflow remains research work |
| Entity/topic multiplication | Resolve-first memory existed | Persistent Context Memory keeps stable IDs, aliases, open-world states and reviewable merge history | Semantic merges still require review |
| Prompt reproducibility | Stage cache ignored prompt/config versions | Cache fingerprint covers document, prompt text/version, model, options and run config; actual model provenance is recorded after fallback | Serving-runtime/container versioning can be strengthened further |
| Standard output | Interchange fields existed but pipeline did not export complete annotations | One provisional schema-1.3 JSONL annotation per document includes relations, imaginaries, populism, provenance and versions | Schema migration policy should remain explicit |
| Local inference | Ollama wrapper existed | Local/external/cloud routing records actual endpoint/model and honors fallback policy | Real runs require the configured service/model |
| Multimodality | Pipeline had an empty placeholder | Prepared transcript/OCR/frame-analysis fields are accepted as source material | Automatic media-to-text orchestration remains separate |
| Hegemony | Risk of equating labels/frequency with hegemony | Output is limited to document-level hegemonic evidence/candidates | Institutional, temporal and cross-arena inference remains human/corpus work |
| Failure semantics | Memory could stay open and success artifacts could be confused with partial work after exceptions | Context Memory and stage SQLite stores close deterministically; result artifacts stage as `.partial` and final annotation JSONL is published only after successful cleanup | Hard process termination may leave visibly marked `.partial` files |

## Collector status at this audit

The collector now lives entirely under `collector/`; there is no current root
`scraper/` subsystem.

Three capture paths are present:

1. `collector/firefox/extension/` + `collector/firefox/firefox_backend.py` is the
   preferred systematic path. Network and embedded TikTok/Instagram payloads
   are forwarded to the shared Python parser/normalisation/store pipeline.
2. `collector/browser.py` provides Chromium/CDP capture with HAR fallback and
   explicit zero-run diagnostics.
3. `collector/browser/` is a standalone LaclauGPT-native JavaScript extension
   useful for development/manual capture; it is not the preferred systematic
   Store-backed path.

Collector outputs keep raw captures separate from normalized records, preserve
provenance, deduplicate normalized items and optionally download media. The
collector does not perform ideological analysis.

## Defects corrected during execution/debug testing

Core/pipeline corrections include:

- missing memory APIs and ignored YAML arena configs were repaired;
- source text is passed to the model and generic document identity is stable;
- model repetition no longer auto-promotes codebook entries;
- near-duplicate consolidation defaults to suggestions rather than automatic
  semantic merge;
- stage cache keys include prompt/config/model provenance;
- actual cloud fallback responses are not mislabeled/cached as local model
  outputs;
- RunStore claims are atomic across SQLite connections and ownership-aware;
- Context Memory and all stage SQLite connections close on success and failure;
- final annotations/corpus/review artifacts are staged and published only after
  successful run completion/cleanup.

Collector corrections include:

- Firefox response streams preserve the original bytes returned to the page;
- embedded TikTok/Instagram page-state capture is supported on the preferred
  Firefox path;
- CDP network events are collected during navigation rather than drained only
  after scrolling;
- zero-item runs expose request/body diagnostics instead of silently appearing
  successful;
- scheduler compatibility code delegates to the current collector runner rather
  than removed helper scripts.

## Verification

The canonical public entry point remains the package CLI:

```bash
python -m laclaugpt.cli --help
python -m laclaugpt.cli profiles
```

The public test tree at the audited commit contains:

- `tests/collectors/` for collector parsing/storage/browser/backend behaviour;
- `tests/test_llm_routing.py` for routing/provenance behaviour;
- `tests/test_run_store_claims.py` for claim exclusivity, stale recovery and
  ownership-aware checkpointing;
- `tests/test_pipeline_failure_cleanup.py` for deterministic cleanup and failed
  run/checkpoint semantics.

The issue #37 pipeline-failure workflow passed before merge of commit
`a96ca67b887135d08c6d02b5a6c58a684450c887`. Full repository-wide CI and
reproducible packaging are tracked separately; the existence of targeted CI must
not be described as complete core CI coverage.

This checkout still does **not** contain a public synthetic end-to-end corpus
fixture that exercises a full successful mocked annotation export. Real
inference also requires a configured Ollama-compatible service and
researcher-supplied source data.

## Adapter and integration implementation status

**Shipped implementation code:**

- `dna_adapter/`
- `dats_adapter/`
- `inception_adapter/`
- `minet_adapter/`
- `laclaugpt/adapters/` legacy/interchange adapters
- `laclaugpt/integrations/fourcat.py` for 4CAT/Zeeschuimer file interchange
- `laclaugpt/integrations/argdown.py`
- root `laclaugpt_processor.py` as a 4CAT compatibility processor

The broader targets in `docs/INTEROPERABILITY_SPEC.md` are design targets unless
a concrete module is present. In particular, QDPX/REFI-QDA application targets
such as ATLAS.ti, MAXQDA, NVivo and QualCoder must not be described as shipped
adapters solely because they appear in the specification.

## Honest scope statement

The code corresponds to the paper's **LLM-assisted pre-analysis methodology** at
the document level. It does not, and should not, claim to automate final
Laclaudian interpretation, establish hegemony from single documents, validate
itself, or replace comparative human analysis.

The next methodological frontier remains empirical validation: a governed coded
sample, independent annotators, adjudication records and reported error metrics.
Architectural cleanup, packaging and adapter parity can improve the software,
but they are not substitutes for that validation.
