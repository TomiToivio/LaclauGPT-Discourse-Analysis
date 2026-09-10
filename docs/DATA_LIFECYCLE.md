# LaclauGPT research-data lifecycle

This document maps LaclauGPT onto the ELIXIR RDMkit data lifecycle and the project's publication boundary. The lifecycle applies to social-media corpora, multimodal derivatives and model-generated analysis records.

## 1. PLAN

Define before collection:

- research questions and lawful/ethical basis;
- platforms, countries, time windows and sampling strategy;
- collection method and relevant platform/API/provider agreements;
- expected personal/special-category data;
- storage location and access-control group;
- retention/disposal plan;
- provenance requirements;
- which outputs are intended to be public, restricted or aggregate-only;
- data-protection notice / DPIA or other institutional review where required.

Public artifacts: data-management documentation, collection methodology, schemas, configuration templates and code.

## 2. COLLECT

Collect only material necessary for the research purpose and record collection provenance, including source/platform, collection time, collector version and relevant query/sampling parameters.

Raw posts, media, account metadata and direct URLs belong in controlled storage. They are not GitHub artifacts.

Preferred boundary:

`source platform -> collector -> controlled CSC storage`

Collectors and reproducible collection logic may be public; collected human data is restricted.

## 3. PROCESS

Processing includes format conversion, media download/fetch, ASR, OCR, keyframe extraction, normalization, deduplication and creation of canonical interchange records.

Derived artifacts can remain personal data even when the original media is not copied into the derivative. ASR transcripts, OCR, keyframes, visual descriptions, per-document embeddings and identifiers therefore stay restricted by default.

Record provenance for:

- software/module version;
- model/version;
- parameters;
- input identity within controlled storage;
- timestamps and run IDs;
- transformations and known losses.

Public artifacts: processing code, schemas, validators, parameter documentation and synthetic fixtures.

## 4. ANALYSE

LaclauGPT model outputs are provisional until human review. Analysis can include summaries, topics, named entities, sentiment, Laclau/Mouffe/Palonen discourse categories, ideology-related classifications, embeddings and network-derived structures.

Document-level outputs linked to people or posts remain restricted by default, especially political/ideological inference. Human review does not itself make a record anonymous.

Public artifacts: analysis prompts, operational definitions, structured-output schemas, uncertainty/abstention rules, evaluation methods and conceptual codebooks.

## 5. REVIEW / ADJUDICATE

Human researchers validate model proposals, resolve codebook changes and assess evidence/uncertainty.

Review databases, annotations and researcher notes remain restricted when they contain row-level or identifiable information.

Before any public release, perform a separate disclosure review for:

- direct/near-direct quotations;
- small cells and rare combinations;
- public figures vs ordinary users;
- narrow time/location slices;
- network singling-out risk;
- joinability to source-platform records;
- inferred special-category data;
- third-party licensing/platform restrictions.

## 6. PRESERVE

Preserve only what the research purpose, agreements and institutional requirements justify.

For restricted datasets:

- keep them in approved controlled infrastructure;
- preserve provenance, schema and software/version metadata;
- separate pseudonymisation keys from the data they unlock;
- document retention and responsibility;
- curate/delete records when required by platform rules, ethics, data-subject rights or project policy.

GitHub is not the preservation location for restricted research data.

## 7. SHARE / PUBLISH

The default public package is:

- code;
- methodology;
- schemas;
- prompts;
- public codebooks;
- reproducible safe configuration;
- workflow/provenance documentation;
- synthetic examples;
- disclosure-reviewed aggregate results;
- metadata records describing restricted datasets.

Potential publication repositories such as Zenodo may be used for tagged software releases, documentation, synthetic datasets, safe aggregate datasets and metadata records with persistent identifiers.

Restricted row-level data is not made public merely to satisfy Open Science or FAIR goals.

## 8. REUSE

Design public artifacts so another researcher can:

- understand the semantic contract;
- recreate the processing/analysis environment;
- run the pipeline on their own lawful data;
- compare model versions;
- reproduce aggregation logic;
- request controlled access where a future governance process permits it.

Reuse of source-platform data remains subject to the original legal, ethical and contractual constraints.

## 9. DELETE / DISPOSE

Deletion is a valid and sometimes required lifecycle outcome.

When restricted data reaches the end of its justified retention period or must be removed:

- delete from primary working storage;
- follow the relevant service procedure for snapshots/backups where applicable;
- remove cached/exported copies and derived files that remain identifying where required;
- document the disposal decision without retaining the protected content itself.

Do not rely on deleting a Git working-tree file after accidental publication. Git history may preserve it. Suspected accidental commits require incident review and, if needed, an explicitly approved history-remediation procedure.

## LaclauGPT storage/publication architecture

```text
PUBLIC GITHUB
  code
  theory + methodology
  prompts + schemas
  public codebooks
  configuration templates
  provenance/workflow docs
  synthetic fixtures
  safe aggregate outputs

CONTROLLED CSC / RESEARCH INFRASTRUCTURE
  raw social-media data
  media files
  ASR/OCR/keyframes
  document-level derived records
  identifiers/user metadata
  private codebooks
  embeddings / review databases
  researcher notes
  pseudonymisation material

PUBLICATION REPOSITORY (later, where appropriate)
  tagged software
  documentation
  synthetic datasets
  disclosure-reviewed aggregates
  metadata records for restricted datasets
  DOI-bearing research outputs
```

See also [`DATA_PUBLICATION_POLICY.md`](DATA_PUBLICATION_POLICY.md).