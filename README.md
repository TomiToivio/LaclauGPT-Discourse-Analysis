# LaclauGPT-Discourse-Analysis — AI26 minimal public core

**LaclauGPT** is an LLM-assisted discourse-analysis pipeline that applies
Ernesto Laclau and Chantal Mouffe's discourse theory (articulation,
nodal/floating/empty signifiers, equivalence/difference/antagonism,
Palonen's Formula of Populism) to large text corpora — with every
interpretation traceable to source evidence and open to human rejection.

This repository is the **sanitized, AI-project-only public core**.
It contains the minimum needed to understand and reproduce the
methodological design of the evolving manuscript *LaclauGPT: Ideological
contestation over AI*. The current manuscript is [`paper/PAPER.md`](paper/PAPER.md).
This public checkout deliberately contains:

- **no research data** — raw captures, exports and run outputs stay out;
- **collection utilities, not collection infrastructure** — the Firefox/Node
  utilities under `scraper/` and 4CAT/Zeeschuimer integration code are public,
  while deployed collection services and private operations remain external;
- **portable profiles, no secrets** — the public `roihu` machine profile is
  shipped, but endpoints, hosts, and credentials come from environment
  variables rather than committed files.

## What is here

```
pipeline.py            the analysis pipeline (6 stages, evidence-linked)
laclaugpt/             canonical models, configuration, adapters, execution,
                       integrations, and package CLI
run_config.py          YAML run-config loader (per-project, per-arena)
projects.py            project preset (ai26)
llm.py                 machine-tier LLM routing (local / cloud / external)
memory.py              shim; see laclaugpt_memory/
seed_codebook.py       49 concept seeds for the AI-ideology codebook
laclaugpt_interchange/ the interchange schema (JSONL, Pydantic) — v1.3
laclaugpt_memory/      Context Memory: codebook + resolution loop +
                       temporal drift + provenance (the anti-
                       entity-explosion layer; paper §3.4 stage 3)
prompts/               theory-guided prompt modules (summary, discourse,
                       populism v3, postprocess, topic backgrounds)
run_configs/           arena YAML configs (elites / grassroots /
                       parliamentary) + projects/
config/                project, machine, and execution profiles for the CLI
dats_adapter/, dna_adapter/, inception_adapter/, minet_adapter/
                       shipped format-specific adapter modules
scraper/               public Firefox and Node collection utilities
tests/                 public regression tests for implemented behaviour
docs/                  implementation audit, interop spec, data-model plan
paper/PAPER.md         current manuscript
LICENSE                license
README.md              this file
```

## The method in one paragraph

Each document is processed through a six-stage, evidence-linked
workflow (paper §3.4): prepare/preserve sources → describe the document
→ propose theoretical codes (articulations, signifier roles, collective
subjects, frontiers, affects — always with exact evidence quotes,
uncertainty, counter-evidence and explicit abstention) → resolve
entities through a persistent Context Memory codebook (stable IDs,
open-world states CANONICAL/PROVISIONAL/MERGED, merge history) →
compare across the corpus → human review. Every theoretical code
carries the document id, evidence span, model+prompt version,
uncertainty and review status. Model output is PROVISIONAL by
construction: mechanical checks establish whether a quotation occurs
in the source; humans assess whether it supports the interpretation.

## Theory in the schema

Laclau's concepts are **roles supported by evidence**, never node types:
`nodal_point`, `floating_signifier` and `empty_signifier` are recorded
as versioned `AnalysisResult`s on plain concepts (protection against
theory-forcing). Palonen's **Formula of Populism**
(`Populism = Us^Affects₁ + Frontier^Affects₂`) is a first-class
structure with honest abstention (`applicable=False` + reason). Affect
polarity is never inferred from Us/Frontier side membership.

## Interoperability

The interchange schema is the pivot. This public tree ships adapter modules for
**DNA 3.1.x**, **DATS**, **INCEpTION**, and **minet**; legacy/interchange
adapters under `laclaugpt/adapters`; and **4CAT/Zeeschuimer** and **Argdown**
integrations under `laclaugpt/integrations`. The broader binding design,
including formats that are specification-only here such as **ATLAS.ti**, is
documented in [`docs/INTEROPERABILITY_SPEC.md`](docs/INTEROPERABILITY_SPEC.md).

## Running

The canonical entry point is the package CLI. It composes the project, machine,
and execution profiles, records run/checkpoint metadata, and dispatches to the
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

The root `pipeline.py` command is the lower-level, paper-oriented pipeline used
by the canonical dispatcher. It remains available for compatibility and direct
development, but new users should prefer `python -m laclaugpt.cli`.

The public tests make no real LLM, GPU, or external-database calls:

```bash
python -m pytest tests -q
```

This checkout currently has no public synthetic corpus fixture, so it does not
advertise a fixture-based dry run or mocked end-to-end annotation export. Raw
research data, private operational tests, and generated outputs are not shipped.

## Author

Tomi Toivio, Helsinki Hub on Emotions, Populism and Polarisation
(HEPPsinki), University of Helsinki.

## License

See [LICENSE](LICENSE).
