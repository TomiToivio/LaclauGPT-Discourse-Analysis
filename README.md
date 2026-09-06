# LaclauGPT-Discourse-Analysis — AI26 minimal public core

**LaclauGPT** is an LLM-assisted discourse-analysis pipeline that applies
Ernesto Laclau and Chantal Mouffe's discourse theory (articulation,
nodal/floating/empty signifiers, equivalence/difference/antagonism,
Palonen's Formula of Populism) to large text corpora — with every
interpretation traceable to source evidence and open to human rejection.

This repository is the **sanitized, AI-project-only public core**.
It contains the minimum needed to understand and reproduce the
methodological design of the paper *LaclauGPT: Ideological contestation
over AI* (locked 2026-09-06). It deliberately contains:

- **no data** — raw captures, exports and run outputs stay out;
- **no scrapers** — collection happens via 4CAT/Zeeschuimer (separate
  infrastructure, see the paper §4.4 data stewardship);
- **no machine-specific configuration** — endpoints, hosts and
  credentials are environment variables, never files.

## What is here

```
pipeline.py            the analysis pipeline (6 stages, evidence-linked)
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
tests/                 test suite (paper-claim regression tests included)
docs/                  implementation audit, interop spec, data-model plan
paper/                 the locked paper (LaclauGPT-Ideological-
                       Contestation-over-AI-Revised.md)
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

The interchange schema is the pivot; adapters for **DNA 3.1.x**
(.dna SQLite), **ATLAS.ti** (.qdpx + CSV), **4CAT/Zeeschuimer**,
**DATS**, **INCEpTION** (UIMA XMI), **minet** and **Argdown** are
documented in `docs/INTEROPERABILITY_SPEC.md`. (Adapter code ships in
the working repository; this public core documents the binding spec.)

## Running

```bash
pip install pydantic pyyaml
# LLM access via Ollama (local or cloud models) — configure:
export OLLAMA_HOST=http://127.0.0.1:11434   # or a remote host
python seed_codebook.py                     # build the codebook
python pipeline.py --run-config run_configs/arena_elites.yaml \
                   --csv my_corpus.csv --output annotations.jsonl
```

Test suite: `python3 -m pytest tests/ -q`.

## Author

Tomi Toivio, Helsinki Hub on Emotions, Populism and Polarisation
(HEPPsinki), University of Helsinki.

## License

See [LICENSE](LICENSE).