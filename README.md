# LaclauGPT-Discourse-Analysis: AI26 minimal public core

**LaclauGPT** is an LLM-assisted discourse-analysis pipeline that applies
Ernesto Laclau and Chantal Mouffe's discourse theory (articulation,
nodal/floating/empty signifiers, equivalence/difference/antagonism,
Palonen's Formula of Populism) to large text corpora, with every
interpretation traceable to source evidence and open to human rejection.

This repository is the **sanitized, AI-project-only public core**.
It contains the minimum needed to understand and reproduce the
methodological design of the evolving manuscript *LaclauGPT: Ideological
contestation over AI*. The current manuscript is [`paper/PAPER.md`](paper/PAPER.md).
This public checkout deliberately contains:

- **no research data**: raw captures, exports and run outputs stay out;
- **collection software, not deployed collection infrastructure**: the reusable
  collector under `collector/` is public, while deployed services, credentials
  and private operations remain external;
- **portable profiles, no secrets**: the public `roihu` machine profile is
  shipped, but endpoints, hosts and credentials come from environment variables
  rather than committed files.

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
| Execution/orchestration | `laclaugpt/canonical_pipeline.py`, `laclaugpt/execution/` | **Canonical orchestration layer** |
| Evidence-linked paper analysis | root `pipeline.py` | **Current analysis implementation**, called by the canonical dispatcher |
| Domain model | `laclaugpt/model/` | **Canonical storage-neutral domain model for new code** |
| Context Memory public API | `laclaugpt/memory/` | **Canonical memory/entity-resolution facade** |
| Persistent Context Memory implementation | `laclaugpt_memory/` | **Supported implementation/compatibility layer**, used by the paper pipeline |
| Batch interchange | `laclaugpt_interchange/` | **Current JSONL/Pydantic interchange, schema 1.3** |
| Collection | `collector/` | **Current collector subsystem**; preferred path is Firefox extension + Python backend |
| Format adapters | `dna_adapter/`, `dats_adapter/`, `inception_adapter/`, `minet_adapter/` | **Shipped implementations** |
| Package adapters/integrations | `laclaugpt/adapters/`, `laclaugpt/integrations/` | **Shipped implementations**, using `laclaugpt.model` for canonical package objects |
| Older model package | `laclaugpt_model/` | **Frozen compatibility model**; emits a deprecation warning and is not extended |
| Root memory shim | `memory.py` | **Legacy compatibility only**; replacement is `laclaugpt.memory` |
| Other compatibility helpers | `projects.py`, `run_config.py` | Supported by the current paper pipeline, but not the primary package API |

The older `laclaugpt_model/` store/projection helpers remain because they do not
yet have exact tested canonical replacements. Historical data and scripts stay
readable, but new adapters must not add dependencies on that model generation.
Current schema-1.3 interchange should be lifted into the canonical model through
`laclaugpt.adapters.interchange.interchange_to_v2()`.

The root `laclaugpt_processor.py` is a shipped 4CAT compatibility processor, but
it currently has its own analysis implementation rather than exact parity with
the canonical pipeline. Canonical 4CAT pipeline parity is tracked separately.

`docs/INTEROPERABILITY_SPEC.md` is a **design specification**, not a statement
that every listed binding exists. QDPX/REFI-QDA targets such as ATLAS.ti,
MAXQDA, NVivo and QualCoder remain specification targets unless a concrete
adapter module is present in this tree.

## What is here

```text
pyproject.toml          package metadata, base dependencies and optional extras
pipeline.py             lower-level evidence-linked analysis pipeline
laclaugpt/              canonical package: model, memory facade, config,
                        adapters, execution, integrations and CLI
run_config.py           compatibility YAML loader for paper arena runs
projects.py             compatibility project-preset helper; canonical project
                        YAML lives in config/projects/
llm.py                  machine-tier LLM routing (local / cloud / external)
memory.py               legacy shim; replacement is laclaugpt.memory
seed_codebook.py        AI-ideology codebook seeds
laclaugpt_interchange/  interchange schema (JSONL, Pydantic), schema 1.3
laclaugpt_memory/       persistent Context Memory implementation
laclaugpt_model/        frozen older model/store/projection compatibility package
prompts/                theory-guided prompt modules
run_configs/            paper arena YAMLs: elites / grassroots / parliamentary
config/                 canonical project, machine and execution profiles
collector/              social-media collection subsystem and browser extensions
dats_adapter/
dna_adapter/
inception_adapter/
minet_adapter/          shipped format-specific adapter modules
tests/                  public offline regression tests + synthetic fixture
docs/                   implementation audit, interop specification and design plans
paper/PAPER.md          current manuscript
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
- the standalone `laclaugpt_processor.py` 4CAT compatibility processor.

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

## Installation and running

Python 3.11+ is supported; CI uses Python 3.12. From a fresh checkout, install
the repository itself rather than maintaining a separate manual dependency
list:

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
python -m pip install -e ".[collector]"   # websocket capture + timezone data
python -m pip install -e ".[test]"        # public offline tests
python -m pip install -e ".[nlp]"         # spaCy / sklearn / gensim / ST / statsmodels
python -m pip install -e ".[services]"    # MongoDB / ArangoDB / Redis / DuckDB / Chroma
python -m pip install -e ".[parquet]"     # pyarrow bulk export
python -m pip install -e ".[inception]"   # DKPro Cassis / UIMA XMI support
```

Optional libraries are imported only when their feature/backend is selected.
The base install therefore does not require GPU libraries or live database
clients. Backend selection raises an explicit configuration/import error when a
requested optional service is unavailable rather than failing during an
unrelated import.

Run an analysis after configuring Ollama and supplying your own CSV:

```bash
python -m laclaugpt.cli analyze my_corpus.csv --project ai26 --machine roihu \
  --execution cli --pipeline-config run_configs/arena_elites.yaml
```

The root `pipeline.py` command remains available for compatibility and direct
paper-pipeline development, but new users should prefer `python -m laclaugpt.cli`.

## Tests and CI

The public test suite is offline: it makes no real LLM, GPU, browser-platform,
or external-database calls. Install the test extra and run the same Python suite
used by CI:

```bash
python -m pip install -e ".[test]"
python -m pytest -q tests
```

`tests/fixtures/synthetic_ai.csv` is a small public synthetic corpus. The mocked
end-to-end test runs the real pipeline I/O, Context Memory and success-artifact
publication path while replacing only model calls, then round-trips the emitted
current-schema annotation JSONL.

`.github/workflows/ci.yml` runs on every pull request and every push to `main`.
Its core job installs `.[test]`, compiles the shipped Python surface, runs CLI
smoke tests and executes the full Python test suite. Its collector job installs
`.[collector,test]`, runs collector tests and validates both Firefox/browser
JavaScript surfaces and extension manifests.

## Compatibility policy

The consolidation is intentionally non-destructive:

- schema-1.3 interchange files remain readable;
- existing `laclaugpt_memory` SQLite stores keep their on-disk schema;
- `memory.py` remains a warning-emitting shim for legacy callers;
- `laclaugpt_model` remains frozen while its store/projection helpers are still
  needed for reproducibility;
- compatibility layers receive bug fixes, not new domain features.

## Documentation status

- [`docs/PAPER_IMPLEMENTATION_AUDIT.md`](docs/PAPER_IMPLEMENTATION_AUDIT.md)
  records what the current code actually implements and the commit audited.
- [`docs/INTEROPERABILITY_SPEC.md`](docs/INTEROPERABILITY_SPEC.md) is a design
  specification containing both shipped and future targets.
- [`docs/DATA_MODEL_2_0_PLAN.md`](docs/DATA_MODEL_2_0_PLAN.md) is a dated design
  plan. Historical version references inside that plan describe the state when
  the plan was written; current canonical paths and schema versions are listed
  in this README and the implementation audit.

## Author

Tomi Toivio, Helsinki Hub on Emotions, Populism and Polarisation
(HEPPsinki), University of Helsinki.

## License

See [LICENSE](LICENSE).
