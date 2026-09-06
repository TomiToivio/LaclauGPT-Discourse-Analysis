# Paper–implementation audit

Audit date: 2026-09-04

Paper: `LaclauGPT_Ideological_contestation_over_AI.md`

Revised manuscript: `LaclauGPT_Ideological_contestation_over_AI_revised_commented.md`

## Overall finding

Before this revision, the repository contained useful memory, interchange, and
analysis components, but the advertised paper-driven pipeline was not runnable
as documented and did not operationalise the paper's main object: ideological
contestation over AI. It mainly summarised a row and forced a Formula of
Populism analysis. The revised code now implements a runnable, evidence-first
document-level pre-analysis pipeline. Corpus-level discourse interpretation and
human validation remain research activities and are not represented as
automated findings.

## Traceability matrix

| Paper or revised-method claim | Previous state | Current state | Remaining boundary |
|---|---|---|---|
| Three empirical arenas | YAML files existed but `pipeline.py` did not load them | YAML configs are validated and executable through `--run-config` | Final sampling frames and dates must be fixed by researchers |
| AI-specific contextualisation | Arena configs reused a single prior-election prompt | Separate AI elites, grassroots, parliamentary, and general contestation prompts | Context should be versioned with the registered study design |
| Source-grounded analysis | CSV source text was not read into the analysis context | Common text/transcript/OCR/fieldnote columns are ingested; empty rows fail fast | Parent-thread reconstruction is stored but not automatically fetched |
| Stable document identity | Web rows without TikTok IDs could all become `::` | Common IDs are used; otherwise a stable content hash is generated | Upstream collectors should still supply durable IDs |
| Articulation | No dedicated structured code | Source–target relations: articulation, equivalence, difference, antagonism | Relation validity requires human review |
| Nodal/floating/empty distinctions | AI was seeded as the study's “main empty signifier” | Situated role candidates, rationale, quote, confidence, corpus-validation flag | Floating/empty status must be established across a corpus |
| Sociotechnical imaginaries | Seed labels only | Structured future, present diagnosis, technology role, human agency, evidence | Cross-document stabilisation remains human/corpus work |
| Ideological formations | Fixed seed list encouraged direct classification | Formation candidates require supporting features, counter-evidence, quote, confidence | Formation boundaries remain interpretive |
| Formula of Populism | Every analysed political item was forced into Us/Frontier; affect polarity was predetermined | Explicit `populist=false`; both Us and Frontier required; affects are not polarity constrained | Human validation decides borderline cases |
| Authorial position | Prompt warning only | Articulations and imaginaries distinguish asserted, quoted, reported, rejected, parodied, uncertain claims | Automatic speech-role accuracy must be evaluated |
| Evidence | Requested informally in prose | Evidence quotation is a structured field and checked mechanically against source text | Paraphrased evidence and multimodal evidence need specialised validation |
| Human validation | Review CSV existed, but repeated model uses auto-promoted codes | Model repetition never promotes; explicit `promote()` is required; outputs say `PROVISIONAL` | Reviewer UI, independent double coding, and adjudication are not yet implemented |
| Entity/topic multiplication | Resolve-first memory and aliases existed | Preserved; only human-canonical entries are injected back into prompts | Semantic merges still require review |
| Consolidation | Near-duplicate strings auto-merged by default | Default consolidation produces suggestions without auto-merging | Reviewed migrations may opt into a threshold |
| Prompt reproducibility | Stage cache ignored prompt/config versions | Cache fingerprint covers document, prompt text/version, model, options, and run config | Record model digest and serving-runtime version in production manifests |
| Standard output | Interchange fields existed but pipeline did not export them | One provisional JSONL annotation per document with concepts, relations, imaginaries, populism, provenance, and versions | Schema migrations need an explicit versioning policy |
| Local inference | Ollama wrapper existed | Still used; default arena model follows repository default `gemma4:e4b`, temperature 0.0 | A real run requires the configured local model |
| Multimodality | ASR/OCR/keyframe modules existed; pipeline contained an empty placeholder | Prepared transcript/OCR/frame-analysis fields are accepted as source material | Automatic media-to-text orchestration remains separate and should not be claimed as complete |
| Hegemony | Risk of equating a model label with hegemony | Prompt limits output to document-level hegemonic evidence | Institutional, temporal, and cross-arena inference remains a human research task |

## Defects corrected during execution testing

- `pipeline.py` called memory APIs that did not exist.
- The documented `--run-config` command-line option did not exist.
- YAML arena configurations were ignored.
- Actual CSV text was not passed to the model.
- Generic web documents could collide on an empty TikTok-style key.
- Codebook entries became `CANONICAL` after repeated model matches without
  human approval.
- Similar strings could be auto-merged by default without human review.
- The embedding backend option was ignored and embedding backfill was
  unreachable.
- A positional-argument defect wrote the model name (for example
  `gemma4:e4b`) into the codebook `state` column, which then caused duplicate
  resolution and a SQLite uniqueness failure. Model provenance is now stored in
  the decision log.

## Verification

Run from this directory:

```bash
python pipeline.py --run-config run_configs/arena_elites.yaml \
  --csv tests/fixtures/ai_sample.csv --dry-run
python -m pytest -q
```

The dry run validates the arena, input columns, model settings, enabled stages,
and output location without invoking an LLM. The test suite includes a mocked
end-to-end run that writes and reloads an evidence-linked provisional
annotation.

## Honest scope statement

The code now corresponds to the revised paper's **pre-analysis methodology** at
the document level. It does not, and should not, claim to automate final
Laclaudian interpretation, establish hegemony from single documents, validate
itself, or replace the comparative human analysis described in the research
design. The next methodological milestone is not another prompt: it is a coded
validation sample, independent annotators, adjudication records, and reported
error metrics.
