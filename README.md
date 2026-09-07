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

## Architecture and canonical paths

The repository contains a current package architecture plus a few compatibility
layers that are still used by the paper pipeline. For new work, use these paths:

| Concern | Current path | Status |
|---|---|---|
| Public CLI | `python -m laclaugpt.cli` | **Canonical entry point** |
| Execution/orchestration | `laclaugpt/canonical_pipeline.py`, `laclaugpt/execution/` | **Canonical orchestration layer** |
| Evidence-linked paper analysis | root `pipeline.py` | **Current analysis implementation**, called by the canonical dispatcher |
| Domain model for new package code | `laclaugpt/model/` | **Canonical storage-neutral domain model** |
| Persistent paper-pipeline Context Memory | `laclaugpt_memory/` | **Current persistent codebook/resolution layer** |
| Repository-oriented context helpers | `laclaugpt/memory/` | Current package layer; consolidation with `laclaugpt_memory/` is tracked separately |
| Batch interchange | `laclaugpt_interchange/` | **Current JSONL/Pydantic interchange, schema 1.3** |
| Collection | `collector/` | **Current collector subsystem**; preferred path is Firefox extension + Python backend |
| Format adapters | `dna_adapter/`, `dats_adapter/`, `inception_adapter/`, `minet_adapter/` | **Shipped implementations** |
| Package adapters/integrations | `laclaugpt/adapters/`, `laclaugpt/integrations/` | **Shipped implementations**, including 4CAT/Zeeschuimer interchange and Argdown |
| Older model package | `laclaugpt_model/` | **Transitional/legacy model generation**; do not treat it as the canonical import path for new code |
| Compatibility helpers | `memory.py`, `projects.py`, `run_config.py` | Supported by the current paper pipeline, but not the primary package API |

The root `laclaugpt_processor.py` is a shipped 4CAT compatibility processor, but
it currently has its own analysis implementation rather than exact parity with
the canonical pipeline. Canonical 4CAT pipeline parity is tracked separately.

`docs/INTEROPERABILITY_SPEC.md` is a **design specification**, not a statement
that every listed binding exists. QDPX/REFI-QDA targets such as ATLAS.ti,
MAXQDA, NVivo and QualCoder remain specification targets unless a concrete
adapter module is present in this tree.

## What is here

```text
pipeline.py             lower-level evidence-linked analysis pipeline
laclaugpt/              canonical package: model, config, adapters, execution,
                        integrations and CLI
run_config.py           compatibility YAML loader for paper arena runs
projects.py             compatibility project-preset helper; canonical project
                        YAML lives in config/projects/
llm.py                  machine-tier LLM routing (local / cloud / external)
memory.py               compatibility shim; see laclaugpt_memory/
seed_codebook.py        AI-ideology codebook seeds
laclaugpt_interchange/  interchange schema (JSONL, Pydantic), schema 1.3
laclaugpt_memory/       persistent Context Memory used by the paper pipeline
laclaugpt_model/        transitional older model/store/projection package
prompts/                theory-guided prompt modules
run_configs/            paper arena YAMLs: elites / grassroots / parliamentary
config/                 canonical project, machine and execution profiles
collector/              social-media collection subsystem and browser extensions
dats_adapter/
dna_adapter/
inception_adapter/
minet_adapter/          shipped format-specific adapter modules
tests/                  public regression tests for implemented behaviour
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
claims over ordinary concepts/signifiers. Palonen's **Formula of Populism**
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

Broader bindings described in
[`docs/INTEROPERABILITY_SPEC.md`](docs/INTEROPERABILITY_SPEC.md), including
QDPX/REFI-QDA application compatibility, are specifications until a matching
implementation is present in the repository.

## Collector

Collection now lives under [`collector/`](collector/). The preferred systematic
capture path is `collector/firefox/extension/` plus
`collector/firefox/firefox_backend.py`; Chromium/CDP and a standalone
LaclauGPT-native browser extension remain alternative capture paths. See
[`collector/README.md`](collector/README.md) for the current status and research
constraints.

## Running

The canonical entry point is the package CLI. It composes project, machine and
execution profiles, records run/checkpoint metadata and dispatches to the
evidence-linked pipeline. List the profiles available in this checkout:

```bash
python -m pip install pydantic pyyaml pandas ollama networkx pytest
python -m laclaugpt.cli --help
python -m laclaugpt.cli profiles
```

Run an analysis after configuring Ollama and supplying your own CSV:

```bash
python -m laclaugpt.cli analyze my_corpus.csv --project ai26 --machine roihu \
  --execution cli --pipeline-config run_configs/arena_elites.yaml
```

The root `pipeline.py` command remains available for compatibility and direct
paper-pipeline development, but new users should prefer `python -m laclaugpt.cli`.

The public tests make no real LLM, GPU or external-database calls:

```bash
python -m pytest tests -q
```

This checkout currently has no public synthetic end-to-end corpus fixture, so it
does not advertise a fixture-based full annotation run. Raw research data,
private operational tests and generated outputs are not shipped.

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
