# LaclauGPT DNA Adapter

`dna_adapter/` — importer/exporter between LaclauGPT and the
**Discourse Network Analyzer** (DNA, leifeld-lab/dna, v3.1.x).

DNA's data model is the statement: an actor makes a statement about a
concept, optionally qualified, anchored to a character range in a
document. Networks are actor-concept matrices built from statements.
The adapter maps LaclauGPT's interchange annotations onto this model
and back.

## Mapping

| LaclauGPT interchange 1.2 | DNA 3.x |
|---|---|
| `document_id` | `DOCUMENTS` row (Title, Text, Date, Author, Source, Section, Type) |
| Us/Frontier elements (`PopulismElementAssessment`) | statements: actor + concept `ENTITIES`, side as `relation`, `agreement` qualifier (us→1, frontier→0) |
| `evidence` quote | `DATALONGTEXT` variable `evidence` + statement `Start/Stop` offsets in the document text |
| `source_platform`, metadata | `Source`, `Section`, `Type` columns |

The exported `.dna` file is a plain SQLite database using the exact
schema of the official leifeld-lab/dna `sample.dna` (v3.0.7 on-disk
format, still current in 3.1.x) — DNA opens it directly with
File → Open. Statement type: `LaclauGPT Statement`.

## Export (LaclauGPT → DNA)

```python
from dna_adapter import export_for_dna, export_statements_csv

export_for_dna("annotations.jsonl", "project.dna")          # full database
export_statements_csv("annotations.jsonl", "statements.csv") # CSV fallback
```

- `.dna`: one statement per evidence-bearing Us/Frontier element.
  Actor and concept become entities; relation (`us`/`frontier`) and the
  evidence quote ride along; agreement qualifier is 1 for Us, 0 for
  Frontier. DNA's coder can then recode, merge, or extend inside DNA.
- `.csv`: one statement per row for DNA's CSV importer and rDNA.

Only annotations with evidence-bearing `populism_elements` are
exported; evidence quotes anchor statements so human coders find them.

## Import (DNA → LaclauGPT)

```python
from dna_adapter import import_dna_documents, import_dna_concepts

rows = import_dna_documents("human_project.dna")   # pipeline-ready CSV rows
ids  = import_dna_concepts("human_project.dna", memory)  # → provisional signifiers
```

- `import_dna_documents`: documents → the same row shape the LaclauGPT
  pipeline reads (`id`, `text`, metadata columns; dates from DNA's
  unix-epoch `Date`).
- `import_dna_concepts`: coder-defined `concept` entities →
  PROVISIONAL signifiers in `laclaugpt_memory` (same pattern as
  `dats_adapter.import_dats_concepts`). Human DNA coding seeds the
  codebook; model runs reuse the same stable IDs.

## Verification

`tests/test_interop.py` round-trips synthetic annotations through the
DNA export (schema check, anchor integrity, evidence counts), the CSV
fallback, the DNA re-import, and the DATS adapter — all green. The
exported file was additionally read with DNA's own join logic
(statements → actor/concept/agreement) to confirm matrix compatibility.

## Design notes

- LaclauGPT does not run inside DNA; DNA is a human coding and network
  export workbench, same division of labor as with DATS.
- `agreement` is a *mapping choice*: Laclau's equivalence/difference
  logic is not DNA's agreement/qualification semantics. Coders should
  treat exported agreement values as the model's Us/Frontier side, not
  as a substantive agreement claim.
- Statement anchoring falls back to the full document when the evidence
  quote is not found verbatim (paraphrase, translation, modality).