# Research-data publication audit

Audit scope: public repository content on the default branch, publication-related configuration/documentation, selected repository searches for research-data indicators, and historical issue context. This is a repository-level screening, not a substitute for institutional legal/data-protection review or a forensic secret scan of every historical Git object.

## Executive assessment

The repository already has a strong core boundary:

- `/data/*` is ignored except `data/README.md`;
- `/sources/*` is ignored except documentation;
- historical EP24 artefacts are retained locally and excluded from public Git;
- `data/README.md` describes runtime/working research data as non-versioned;
- issue #73 explicitly requires research/generated data and secrets to stay outside Git.

The main gaps were policy/documentation rather than a visible committed raw corpus. The project needed an explicit publication matrix, a lifecycle policy, clearer codebook rules, stronger ignore patterns for additional restricted roots/file types, and a lightweight automated guard.

## Publication matrix summary

| Class | Examples | Decision |
|---|---|---|
| Raw / collected data | posts, comments, video, image, audio, screenshots, user metadata | RESTRICTED |
| Derived document-level data | ASR/OCR, keyframes, LLM summaries, row-level annotations, per-document embeddings | RESTRICTED |
| Aggregate results | distributions, trends, aggregate network statistics, evaluation tables | PUBLIC AFTER DISCLOSURE REVIEW |
| Research metadata/provenance | methods, run/version metadata, non-identifying dataset descriptions | PUBLIC |
| Conceptual schemas/codebooks | Laclau/Mouffe/Palonen concepts, schemas, category definitions | PUBLIC |
| Public institutional dictionaries | parties/institutions/factual context | PUBLIC AFTER SOURCE/LICENCE REVIEW |
| Named-person analytical mappings | person -> ideology/sentiment/discourse position | RESTRICTED BY DEFAULT |
| Software/prompts/config templates | pipeline, collectors, prompts, safe templates | PUBLIC |
| Synthetic fixtures | fictional records and fake/example URLs | PUBLIC |

Detailed rules are in `docs/DATA_PUBLICATION_POLICY.md`.

## Historical EP24 material

EP24 Finland and Poland artefacts were removed from public Git and retained
only in the restricted local checkout. This includes codebooks,
configurations, pipelines and tests. The public repository keeps only
high-level Markdown documentation needed to explain the historical boundary.

## Repository findings

### Existing safeguards worth keeping

- `.gitignore` uses directory-level exclusion for `/data/*` and `/sources/*` while re-including only tracked README/public codebook material.
- `data/README.md` already states that working research data and model-proposed records are not versioned research outputs.
- `sources/README.md` already keeps downloaded/copyrighted source texts outside Git.
- issue #73 establishes a useful architecture in which runtime research/generated data and secrets do not belong in the repository.

### Gap: real-world identifiers in examples/tests

Repository search found examples/test fixtures containing real public social-media account identifiers. These are not evidence of a raw research corpus, but they violate the stronger policy that public examples should be purpose-built synthetic fixtures whenever possible.

Recommendation: replace real account/profile examples with clearly fictional `example.org`/synthetic-user fixtures unless a real identifier is technically required by an integration test. Track this separately because changing parser fixtures can affect collector tests.

### Gap: production-service URL patterns

Historical EP24 fetch tests are retained locally and excluded from public Git. The publication guard should distinguish safe fixture/example URLs from production research URLs and flag suspicious Allas/Swift patterns for human review.

### Issue / discussion surface

Public GitHub issues can themselves leak paths, IDs, quotes or examples even when `.gitignore` is correct. Issue #73 contains operational data-location/provenance discussion. Future issue/PR reports should avoid pasting row-level records or identifiable social-media content and should report categories/paths instead.

## Git-history note

No automatic history rewrite was attempted. If a future audit confirms personal data, credentials, production research records or protected third-party content in Git history, treat it as an incident: stop redistribution, identify affected refs/releases/caches, obtain human approval, and use an explicit history-remediation procedure if required.

## Implemented controls in issue #76 branch

- `docs/DATA_PUBLICATION_POLICY.md`
- `docs/DATA_LIFECYCLE.md`
- `docs/DATA_PUBLICATION_AUDIT.md`
- stronger `.gitignore` patterns for restricted/private/scratch roots and common research database/media outputs
- a lightweight `scripts/check_publication_safety.py` guard
- an updated `data/README.md` stating that `data/` is never a publication directory

## Licensing recommendation

Do not apply CC0 to the repository wholesale.

- software: use the repository software licence;
- substantial project documentation: attribution-oriented licensing may be preferable;
- original simple metadata/schemas/synthetic fixtures: CC0 may be considered only after rights review;
- third-party social-media data: no project licence can erase the rights of data subjects, copyright/database rightsholders, or contractual platform restrictions.

## Open-science target state

The practical target is **open methods, open code, open semantics, open documentation, open provenance, synthetic examples and safe aggregates**, while raw/identifiable human data and row-level derived personal data remain controlled. This gives reproducibility without turning research participants into a downloadable dataset.