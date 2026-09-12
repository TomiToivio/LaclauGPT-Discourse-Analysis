# sources/ — scientific source corpus

This directory holds the **scientific source corpus**: canonical texts,
downloaded papers and bibliographic metadata. It is deliberately
**gitignored** (copyrighted / large binary material is never committed).

## What lives here

- Canonical theory books used by the project (Laclau's *On Populist
  Reason*, Castells, Lévi-Strauss, Deleuze & Guattari, Hardt & Negri,
  Haraway, and related works referenced in [`THEORY.md`](../THEORY.md))
- Downloaded PDFs and page images from the collector
- Bibliographic exports (BibTeX/RIS) and literature notes

The books remain the **authoritative reference** for all theory-facing
work: every agent and human reviewer verifies theoretical changes against
the original sources, never against model outputs or summaries.

## Conventions

- `sources/papers/` — downloaded paper PDFs (collector output)
- `sources/books/` — canonical theory texts
- `sources/bibliography/` — BibTeX/RIS exports for the paper pipeline
- `sources/codebooks/` — reviewable codebooks (committed; these are research
  semantics, not collected data). They include the exploratory
  [`ai_spiralism.md`](codebooks/ai_spiralism.md) codebook for the
  `synthetic_spirituality` source family — a candidate category with explicit
  boundary rules, not an automatic classifier.
- Large binaries and copyrighted scans stay local; citations and stable
  identifiers (DOI, archive ID) go in the repo instead.
- Nothing here is committed except `README.md` and `codebooks/*.md`; if a source
  is genuinely redistributable, link it from the docs rather than vendoring it.