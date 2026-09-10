# LaclauGPT: LLM-assisted discourse analysis for political research

[![Tests](https://img.shields.io/github/actions/workflow/status/TomiToivio/LaclauGPT-Discourse-Analysis/ci.yml?branch=main&label=tests)](https://github.com/TomiToivio/LaclauGPT-Discourse-Analysis/actions/workflows/ci.yml)

> **There is no AI but a CYBORG = HUMAN + LLM + LANGUAGE + INTERNET**

**LaclauGPT** is a political-science data collection and discourse-analysis pipeline for studying large textual and multimodal corpora with LLM assistance, while keeping interpretation traceable to source evidence and subject to human review.

The current version is being developed primarily for my research plan and paper, **[LaclauGPT: Ideological contestation over AI](paper/PAPER.md)**. That study uses Ernesto Laclau and Chantal Mouffe's discourse theory, Emilia Palonen's Formula of Populism, Critical AI Studies and sociotechnical imaginaries to analyse competing ideological articulations of artificial intelligence.

The repository is not, however, an AI-ideology application hard-wired into code. The current research paper is the main development case for a **new general version of LaclauGPT**: a reusable framework in which theory, datasets, arenas, machine profiles and execution profiles can be changed without rebuilding the whole pipeline. The same infrastructure is also used, or intended to be used, in other political and social-science projects such as election research, populism and grievance politics, social-media research, and future comparative discourse-analysis projects.

In short:

- **Current research focus:** ideological contestation over AI and the development of the methodology described in `paper/PAPER.md`.
- **General software goal:** a reusable LLM-assisted computational discourse-analysis framework rather than a single-purpose AI classifier.
- **Theoretical core:** Laclau and Mouffe, with Palonen's Formula of Populism and project-specific theoretical extensions.
- **Methodological principle:** models propose interpretations; evidence, uncertainty, provenance and human review remain visible.
- **Data principle:** open code and methods, but no publication of restricted research corpora or identifiable row-level research data.

> [!WARNING]
> **Human-in-the-loop research only.** LaclauGPT's machine-generated summaries,
> classifications, discourse-theoretical codes, populism analyses, signifier roles,
> ideological formations, affects, and other interpretations are **preliminary
> analysis to be verified by a human researcher**. They must not be treated as
> final research findings, ground truth, or autonomous scholarly judgement.
> Human verification of the source evidence and interpretation is required before
> results are used, reported, published, or cited as research conclusions.

## Current research programme: Ideological contestation over AI

The current manuscript, [`paper/PAPER.md`](paper/PAPER.md), is the main theoretical and methodological driver of this version of LaclauGPT. It asks how competing political projects articulate AI, how those formations construct collective subjects and frontiers, and under what conditions AI functions as a nodal, floating or tendentially empty signifier.

The paper treats accelerationism, existential-risk discourse, critical AI perspectives, opposition to AI and left-wing techno-optimism as starting points for inquiry rather than fixed ideological labels. The corresponding software therefore tries to identify and compare **claims, articulations, signifier roles, collective subjects, antagonisms, affects and candidate ideological formations**, rather than simply sorting documents into predefined political boxes.

The AI project is also a test case for a broader methodological question: how far can computational and LLM-assisted methods extend interpretive discourse analysis without pretending that political meaning is self-evident, fully automatable or reducible to sentiment/topic labels?

## A reusable platform for other research projects

LaclauGPT predates the current AI paper and remains multi-project by design. The canonical configuration chain separates:

`project -> arena/dataset -> machine -> execution -> effective run config -> run`

That separation is deliberate. A project can define its theoretical modules and codebooks, an arena can define a dataset or source environment, a machine profile can define infrastructure, and an execution profile can define how the run is scheduled. The AI-ideology project is therefore the **current flagship research case**, not the only permissible use of the software.

Other current or historical uses include multimodal election research, CO3 social-contract research, ENDURE post-pandemic research, PLEDGE grievance-politics research, social-media collection and reusable interoperability with other discourse-analysis and annotation tools.

Project-specific theories, codebooks and relevance policies can be added on top of the same evidence-linked analytical core. The repository should therefore evolve in two directions at once: **deeper theoretical fidelity for the current paper, and cleaner modularity for other research projects**.

## Public repository and research-data boundary

This repository is the **sanitized public development version** of LaclauGPT. It contains the software, methodological documentation, theory contracts, public codebooks, schemas, synthetic fixtures and reproducible configuration needed to understand and reuse the framework.

It deliberately contains:

- **no restricted research corpus**: raw captures, row-level derived research data and run outputs remain outside Git;
- **collection software, not deployed collection infrastructure**: the reusable collector under `collector/` is public, while credentials and private operations remain external;
- **portable profiles, no secrets**: public machine/configuration templates are shipped, while endpoints, hosts and credentials come from environment variables or controlled infrastructure;
- **synthetic examples for tests and documentation** instead of copied research records.

See [`docs/DATA_PUBLICATION_POLICY.md`](docs/DATA_PUBLICATION_POLICY.md) for the publication boundary and [`docs/DATA_LIFECYCLE.md`](docs/DATA_LIFECYCLE.md) for the research-data lifecycle.

## History and predecessor repositories

Active development happens in this repository. It supersedes the archival [LaclauGPT-Multimodal-Analysis](https://github.com/TomiToivio/LaclauGPT-Multimodal-Analysis) and [LaclauGPT-TikTok-Scraper](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper) repositories while preserving useful compatibility paths. The EP2024 development history, earlier research-project context and predecessor architecture are documented separately in [`docs/HISTORY.md`](docs/HISTORY.md).

## Architecture and canonical APIs

There is one canonical domain-model import path and one public Context Memory
entry point for new code:

```python
from laclaugpt.model import SourceItem, Statement, Concept, Articulation
from laclaugpt.memory import Memory, MemoryRef, ContextBuilder
```

The internal memory implementation is layered deliberately: persistent stable-ID
codebook/entity resolution lives in `laclaugpt_memory/`, while
`laclaugpt/memory/context.py` provides repository-aware context orchestration.
`laclaugpt.memory` is the public facade over both responsibilities. New callers
therefore do not need to choose between memory generations.

| Concern | Current path | Status |
|---|---|---|
| Public CLI | `python -m laclaugpt.cli` / `laclaugpt` | **Canonical entry point** |
| Configuration chain | `config/projects/` -> `config/arenas/` -> `config/machines/` -> `config/execution/` | **Single runtime configuration chain** |
| Execution/orchestration | `laclaugpt/canonical_pipeline.py`, `laclaugpt/execution/` | **Canonical orchestration layer** |
| Evidence-linked paper analysis | root `pipeline.py` | **Current analysis implementation**, called by the canonical dispatcher |
| Domain model | `laclaugpt/model/` | **Canonical storage-neutral domain model for new code** |
| Context Memory public API | `laclaugpt/memory/` | **Canonical memory/entity-resolution facade** |
| Persistent Context Memory implementation | `laclaugpt_memory/` | **Supported implementation/compatibility layer**, used by the paper pipeline |
| Batch interchange | `laclaugpt_interchange/` | **Current JSONL/Pydantic interchange**; version lives in `laclaugpt_interchange.SCHEMA_VERSION` and should not be hard-coded in docs |
| Visualization | `laclaugpt/visualization/` | **Optional project/profile-aware Streamlit dashboard**, local/Pouta only; not Roihu |
| Collection | `collector/` | **Current collector subsystem**; preferred path is Firefox extension + Python backend |
| Hermes Agent integration | [`HERMES.md`](HERMES.md), [`docs/HERMES_INTEGRATION.md`](docs/HERMES_INTEGRATION.md) | **Optional agent-caller conventions**, zero runtime dependency |
| Claude Code integration | [`CLAUDE.md`](CLAUDE.md), [`docs/CLAUDE_INTEGRATION.md`](docs/CLAUDE_INTEGRATION.md) | **Optional agent-caller conventions**, zero runtime dependency; both agents route analysis to local Ollama open-source models only |
| Theory contract | [`THEORY.md`](THEORY.md) | **Canonical theory/methodology contract for humans and agents**; required reading before theory-facing changes |
| Format adapters | `dna_adapter/`, `dats_adapter/`, `inception_adapter/`, `minet_adapter/` | **Shipped implementations** |
| Package adapters/integrations | `laclaugpt/adapters/`, `laclaugpt/integrations/` | **Shipped implementations**, using `laclaugpt.model` for canonical package objects |
| Older model package | `laclaugpt_model/` | **Frozen compatibility model**; emits a deprecation warning and is not extended |
| Root memory shim | `memory.py` | **Legacy compatibility only**; replacement is `laclaugpt.memory` |
| Root run-config adapter | `run_config.py` | **Pipeline adapter + legacy YAML compatibility**, not a second configuration authority |

Project profiles own the authoritative analysis-module switches and any optional relevance policy. Arena profiles own dataset/source metadata, analytic hints, model options and data-boundary policy. Machine profiles own infrastructure and execution profiles own scheduler, retry and checkpoint policy. See [`docs/CANONICAL_CONFIGURATION.md`](docs/CANONICAL_CONFIGURATION.md).

The default relevance policy is conservative: documents without substantive codes remain unjudged rather than being silently excluded. A project such as EP24 may explicitly opt into a project-owned keyword scope gate. This keeps election-specific vocabulary out of the generic analysis implementation and preserves zero-code/borderline documents for validation-oriented projects such as AI26.

The older `laclaugpt_model/` store/projection helpers remain because they do not
yet have exact tested canonical replacements. Historical data and scripts stay
readable, but new adapters must not add dependencies on that model generation.
Current interchange should be lifted into the canonical model through
`laclaugpt.adapters.interchange.interchange_to_v2()`.

The root `laclaugpt_processor.py` is the shipped 4CAT processor and delegates
analysis to the same canonical execution path as the CLI; 4CAT-specific code is
limited to dataset/result adaptation.

`docs/INTEROPERABILITY_SPEC.md` is a **design specification**, not a statement
that every listed binding exists. QDPX/REFI-QDA targets such as ATLAS.ti,
MAXQDA, NVivo and QualCoder remain specification targets unless a concrete
adapter module is present in this tree.

## What is here

```text
pyproject.toml          package metadata, base dependencies and optional extras
pipeline.py             lower-level evidence-linked analysis pipeline
laclaugpt/              canonical package: model, memory facade, config,
                        adapters, execution, integrations, visualization and CLI
run_config.py           adapter from EffectiveRunConfig to the root pipeline;
                        also loads historical/custom YAML for compatibility
projects.py             compatibility project-preset helper; canonical project
                        YAML lives in config/projects/
llm.py                  machine-tier LLM routing (local / cloud / external)
memory.py               legacy shim; replacement is laclaugpt.memory
seed_codebook.py        AI-ideology codebook seeds
laclaugpt_interchange/  interchange schema (JSONL, Pydantic); version lives in
                        laclaugpt_interchange.SCHEMA_VERSION
laclaugpt_memory/       persistent Context Memory implementation
laclaugpt_model/        frozen older model/store/projection compatibility package
prompts/                theory-guided prompt modules
run_configs/            deprecated AI arena YAML aliases + historical compatibility
config/                 canonical project, arena, machine and execution profiles
collector/              social-media collection subsystem and browser extensions
dats_adapter/
dna_adapter/
inception_adapter/
minet_adapter/          shipped format-specific adapter modules
tests/                  public offline regression tests + synthetic fixtures
docs/                   implementation audit, data policy, config/interop/visualization docs and design plans
paper/PAPER.md          current research manuscript and main development case
LICENSE                 repository license
README.md               this file
```

## The method in one paragraph

Each document is processed through a six-stage, evidence-linked
workflow: prepare/preserve sources, describe the document, propose theoretical
codes (articulations, signifier roles, collective subjects, frontiers and
affects, always with exact evidence quotes, uncertainty, counter-evidence and
explicit abstention), resolve entities through persistent Context Memory,
compare across the corpus, and submit results to human review. Every theoretical
code carries document identity, evidence, model/prompt provenance, uncertainty
and review status. Model output is PROVISIONAL by construction: mechanical
checks establish whether a quotation occurs in the source; humans assess whether
it supports the interpretation.

## Theory in the schema

Laclaudian concepts are **roles supported by evidence**, not ontology types.
Nodal, floating and empty-signifier readings are stored as versioned analytical
claims over ordinary concepts/signifiers. In the canonical model,
`DiscursiveRoleAssignment` requires evidence IDs, so a theoretical role cannot
become a bare node classification without an evidentiary link.

Palonen's **Formula of Populism**
(`Populism = Us^Affects₁ + Frontier^Affects₂`) is represented structurally with
honest abstention when the necessary political subject/frontier evidence is not
present. Affect polarity is never inferred from Us/Frontier side membership.

## Interoperability

The interchange schema is the batch-exchange pivot. This public tree ships:

- DNA 3.1.x import/export code under `dna_adapter/`;
- DATS integration under `dats_adapter/`;
- INCEpTION/UIMA integration under `inception_adapter/`;
- minet integration under `minet_adapter/`;
- package-level legacy/interchange adapters under `laclaugpt/adapters/`;
- 4CAT/Zeeschuimer file interchange and Argdown integrations under
  `laclaugpt/integrations/`;
- the standalone `laclaugpt_processor.py` 4CAT processor.

The shipped package adapters/integrations use `laclaugpt.model` domain objects;
`laclaugpt_model` is not an alternative adapter target.

Broader bindings described in
[`docs/INTEROPERABILITY_SPEC.md`](docs/INTEROPERABILITY_SPEC.md), including
QDPX/REFI-QDA application compatibility, are specifications until a matching
implementation is present in the repository.

## Collector

Collection lives under [`collector/`](collector/). The preferred systematic
capture path is `collector/firefox/extension/` plus
`collector/firefox/firefox_backend.py`; Chromium/CDP and a standalone
LaclauGPT-native browser extension remain alternative capture paths. See
[`collector/README.md`](collector/README.md) for the current status and research
constraints.

For basic source ingestion (RSS feeds, plain web pages, Hermes Agent
submissions, manual researcher submissions and Telegram via the
Vasama-OSINT adapter), see [`docs/DATA_COLLECTION.md`](docs/DATA_COLLECTION.md)
— all channels converge into the same canonical corpus, and collection
settings stay in gitignored `collection-data/`.

For **digital ethnography based on TikTok or Instagram feed screen recordings**,
`laclaugpt-split` can split a continuous recording into inspectable post-level
clips using visible identity/text changes and feed-scroll motion. This is
**descriptive preprocessing, not discourse analysis**: researchers should inspect
the proposed clips and provenance manifest before treating them as analytical
documents. See [`docs/DIGITAL_ETHNOGRAPHY_SPLITTING.md`](docs/DIGITAL_ETHNOGRAPHY_SPLITTING.md)
for installation, usage and validation guidance.

## Installation and running

Python 3.11+ is supported; CI tests Python 3.11, 3.12 and 3.13. From a fresh checkout, install the repository itself rather than maintaining a separate manual dependency list:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python -m laclaugpt.cli --help
python -m laclaugpt.cli profiles
```

The install also exposes the equivalent console command:

```bash
laclaugpt --help
laclaugpt profiles
```

Optional dependency groups are deliberately separate from the core research
pipeline:

```bash
python -m pip install -e ".[collector]"       # websocket capture + timezone data
python -m pip install -e ".[test]"            # pytest and test-runner support
python -m pip install -e ".[dev]"             # build tools + ruff static checks
python -m pip install -e ".[nlp]"             # spaCy / sklearn / gensim / ST / statsmodels
python -m pip install -e ".[services]"        # MongoDB / ArangoDB / Redis / DuckDB / Chroma
python -m pip install -e ".[visualization]"   # Streamlit + Plotly dashboard
python -m pip install -e ".[parquet]"         # pyarrow bulk export
python -m pip install -e ".[inception]"       # DKPro Cassis / UIMA XMI support
```

Optional libraries are imported only when their feature/backend is selected.
The base install therefore does not require GPU libraries or live database
clients. Backend selection raises an explicit configuration/import error when a
requested optional service is unavailable rather than failing during an
unrelated import.

Run an analysis after configuring Ollama and supplying your own CSV plus an
explicit arena:

```bash
python -m laclaugpt.cli analyze my_corpus.csv \
  --project ai26 --arena elites --machine roihu --execution cli
```

Inspect the fully composed configuration without changing the chain:

```bash
python -m laclaugpt.cli analyze my_corpus.csv \
  --project ai26 --arena grassroots --machine roihu --execution cli --show-config
```

The three historical `run_configs/arena_*.yaml` paths remain accepted through
`--pipeline-config` as deprecated compatibility aliases, but new runs should use
`--arena` directly. The root `pipeline.py` implementation remains available for
compatibility and direct development; canonical execution reaches it through an
adapter built from the same `EffectiveRunConfig` used by CLI and schedulers.

## Visualization

The optional visualization consumes canonical annotation JSONL/NDJSON and derives
its tabs from the selected project's analysis-module switches. It is therefore
shared across projects and arena/profile definitions rather than hard-coded to
AI26 or an election dataset.

**Visualization is not a Roihu workload.** Run the analysis on Roihu if desired,
then visualize the resulting interchange file locally or on a persistent Linux
web server such as CSC Pouta. The launcher rejects Roihu markers and active Slurm
allocations.

```bash
python -m pip install -e ".[visualization]"
laclaugpt dashboard data/annotations.jsonl --project ai26 --arena elites
```

For Pouta, copy the output to the VM and bind the service explicitly, for example
`--host 0.0.0.0 --port 8501`, then put it behind the site's normal HTTPS and
access-control layer. Researcher review notes are stored in a separate SQLite
sidecar and never rewrite canonical model output. See
[`docs/VISUALIZATION.md`](docs/VISUALIZATION.md).

## Tests and CI

The public test suite is offline: it makes no real LLM, GPU, browser-platform,
or external-database calls. To run the same core dependency surface used by CI:

```bash
python -m pip install -e ".[collector,collect,test,dev]"
LACLAUGPT_EMBED_BACKEND=none python -m pytest -q tests
ruff check --select E9,F63,F7,F82 .
```

The regression suite covers the main public contracts of the repository, including:

- canonical API consolidation, configuration composition and execution profiles;
- theory-contract validation, discourse roles, populism structures and corpus-level synthesis candidates;
- Context Memory, review state, evidence/provenance handling and interchange round-trips;
- LLM routing and agent integration policy without making live model calls;
- discourse-graph construction and visualization-facing data contracts;
- source collection, minet/Zeeschuimer ingestion, collector parsers, media handling and runner behaviour;
- EP24 ASR/media compatibility and other historical/public regression paths;
- failure cleanup, CLI smoke paths, deployment profiles and compatibility shims.

Useful focused runs include:

```bash
python -m pytest -q tests/test_theory_contract.py
python -m pytest -q tests/test_config_chain.py tests/test_canonical_config_execution.py
python -m pytest -q tests/test_context_memory_review.py
python -m pytest -q tests/test_relevance_policy.py
python -m pytest -q tests/test_discourse_graph.py
python -m pytest -q tests/collectors
python -m pytest -q tests/test_pipeline_failure_cleanup.py -k name
```

`tests/fixtures/synthetic_ai.csv` is a small public synthetic corpus. The mocked
end-to-end tests run the real pipeline I/O, canonical configuration adapter,
Context Memory and success-artifact publication path while replacing only model
calls, then round-trip the emitted current-schema annotation JSONL. Collector
tests use synthetic fixtures under `tests/fixtures/` and `tests/collectors/`.

`.github/workflows/ci.yml` runs on every pull request and every push to `main`.
Its core job runs the full offline suite against Python 3.11, 3.12 and 3.13,
checks publication safety, runs targeted Ruff hard-error checks, compiles the
shipped Python surface and exercises CLI smoke paths. The collector job runs on
Python 3.12 with Node 22, tests the collector and validates both browser-extension
JavaScript surfaces and manifests.

## Compatibility policy

The consolidation is intentionally non-destructive:

- interchange JSONL files remain readable across schema versions
  (`schema_version` is a plain field with defaults, so older files load and
  keep their version);
- existing `laclaugpt_memory` SQLite stores keep their on-disk schema;
- existing RunStore databases are migrated in place with nullable
  `analysis_profile` and `arena_id` columns;
- the three `run_configs/arena_*.yaml` files map to canonical arena profiles;
- arbitrary historical/custom run YAML remains readable through `run_config.py`;
- `memory.py` remains a warning-emitting shim for legacy callers;
- `laclaugpt_model` remains frozen while its store/projection helpers are still
  needed for reproducibility;
- compatibility layers receive bug fixes, not new domain features.

## Documentation status

- [`paper/PAPER.md`](paper/PAPER.md) is the current research manuscript and principal development case for this version of LaclauGPT.
- [`THEORY.md`](THEORY.md) is the canonical theory/methodology contract (concept registry and invariants) that agents must read before theory-facing changes.
- [`docs/VALIDATION_PROTOCOL.md`](docs/VALIDATION_PROTOCOL.md) defines the reviewable validation design; it does not claim completed empirical validation.
- [`docs/CANONICAL_CONFIGURATION.md`](docs/CANONICAL_CONFIGURATION.md) defines the project/arena/machine/execution ownership boundaries and migration policy.
- [`docs/HISTORY.md`](docs/HISTORY.md) contains predecessor-repository and EP2024 development history moved out of this README.
- [`docs/VISUALIZATION.md`](docs/VISUALIZATION.md) defines the project/profile dashboard data contract and local/Pouta deployment boundary.
- [`docs/PAPER_IMPLEMENTATION_AUDIT.md`](docs/PAPER_IMPLEMENTATION_AUDIT.md) records what the current code actually implements and the commit audited.
- [`docs/INTEROPERABILITY_SPEC.md`](docs/INTEROPERABILITY_SPEC.md) is a design specification containing both shipped and future targets.
- [`docs/DATA_MODEL_2_0_PLAN.md`](docs/DATA_MODEL_2_0_PLAN.md) is a dated design plan; historical version references describe the state when it was written.
- [`docs/HERMES_INTEGRATION.md`](docs/HERMES_INTEGRATION.md) and [`docs/CLAUDE_INTEGRATION.md`](docs/CLAUDE_INTEGRATION.md) document optional agent-caller conventions. Both integrations are restricted to local Ollama open-source models by `laclaugpt.integrations.agent_policy`.
- [`docs/DATA_PUBLICATION_POLICY.md`](docs/DATA_PUBLICATION_POLICY.md) defines what may be published openly and what remains restricted research data.
- [`docs/DATA_LIFECYCLE.md`](docs/DATA_LIFECYCLE.md) maps LaclauGPT research data onto its lifecycle from collection through preservation/publication/disposal.

## Author

Tomi Toivio, Helsinki Hub on Emotions, Populism and Polarisation
(HEPPsinki), University of Helsinki.

## License

See [LICENSE](LICENSE).
