# LaclauGPT research-data publication policy

> **As open as possible, as closed as necessary.**

This document defines the default publication boundary for LaclauGPT research artifacts. It is an operational project policy, not legal advice. Ambiguous cases involving personal data, special-category data, platform agreements, copyright/database rights, or research ethics must be escalated to the University of Helsinki Data Support / DPO or other responsible institutional review before publication.

## Why the boundary exists

LaclauGPT processes political social-media material. Public visibility on a platform does **not** by itself make redistribution safe or lawful. Social-media records can contain personal data and political opinions, and exact quotations can often be reverse-identified with phrase search even after usernames are removed. Derived LLM outputs can still be personal data when they retain, infer, or remain linkable to identifiable people.

The repository therefore publishes the **research machinery and semantics** rather than the underlying human corpus: code, methods, schemas, prompts, public codebooks, reproducible configuration, provenance models, synthetic examples, and disclosure-reviewed aggregate outputs.

Relevant guidance:

- University of Helsinki / HSSH Research Data Guide: Social Media Data: https://www.helsinki.fi/en/helsinki-institute-social-sciences-and-humanities/research-data-guide-social-media-data
- CSC Data Policy and FAIR principle: https://csc.fi/en/security-privacy-data-policy-and-open-source-policy/data-policy/
- GDPR, especially Articles 5, 9 and 89: https://eur-lex.europa.eu/eli/reg/2016/679
- ELIXIR RDMkit data lifecycle: https://rdmkit.elixir-europe.org/data_life_cycle
- CC0 1.0 deed: https://creativecommons.org/publicdomain/zero/1.0/deed.en

Note: Finnish AI Region / FAIR EDIH is not the same thing as the FAIR research-data principles (Findable, Accessible, Interoperable, Reusable).

## Publication classes

### PUBLIC

May normally be committed to the public repository after ordinary code/research review:

- source code, collectors, importers, adapters and validators
- prompts and structured-output definitions
- conceptual/theoretical codebooks
- schemas and data dictionaries
- model/runtime configuration templates that contain no secrets or private infrastructure details
- sampling, filtering, preprocessing and validation methods
- provenance models and workflow documentation
- synthetic test/demo fixtures
- collection metadata that does not identify research subjects
- aggregate results that have passed disclosure review

### PUBLIC AFTER REVIEW / AGGREGATION

May be released only after explicit disclosure, legal/ethical and licensing review:

- aggregate topic, ideology, sentiment or discourse distributions
- temporal summaries
- aggregate network statistics
- aggregate co-occurrence matrices
- public-figure factual dictionaries
- aggregate entity frequencies
- model-performance measures, confusion matrices and inter-coder agreement
- aggregate embedding centroids/visualisations
- dataset metadata records for restricted datasets
- identifiers where current platform rules and data-protection implications have been checked

Aggregation is **not automatically anonymisation**. Review small cells, rare actors/locations, narrow time windows, sparse networks, unique combinations and joinability back to public records. A project suppression threshold may be used as a conservative disclosure-control heuristic, but it is not a universal or legally guaranteed "GDPR-safe k".

### RESTRICTED

Do not publish openly by default:

- downloaded posts, comments, videos, images, audio or screenshots
- usernames, handles, account IDs, profile URLs and user-level histories
- full post URLs when they identify or enable linkage to a person
- direct quotations from ordinary social-media users
- Whisper/ASR transcripts, OCR, keyframes and visual descriptions from user content
- document-level LLM summaries retaining identifiable content
- document-level political, ideological, sentiment or discourse classifications linked to identifiable people
- row-level annotations derived from personal data
- embeddings for individual users/posts when linkage or reconstruction is plausible
- identifiable network edge lists and geolocation
- researcher notes containing identifiable observations
- pseudonymisation keys
- private Allas/CSC paths, credentials, tokens, SSH material, `.env` files and machine-specific secrets
- database dumps, caches and logs containing research records

A deterministic hash of a username, account ID, URL or post ID is normally **pseudonymisation, not anonymisation**. Removing a name while retaining a searchable exact quote is likewise insufficient.

## Artifact matrix

| Artifact | Default | Conditions | Recommended location |
|---|---|---|---|
| Raw social-media posts/comments | RESTRICTED | No open redistribution by default | CSC / controlled storage |
| Videos/images/audio/screenshots | RESTRICTED | Subject to privacy, copyright and platform constraints | CSC / controlled storage |
| ASR transcripts / OCR / keyframes | RESTRICTED | Derived record may remain personal data | CSC / controlled storage |
| User/profile metadata | RESTRICTED | Identifiers and linkable attributes excluded from public repo | CSC / controlled storage |
| Post/profile URLs and IDs | RESTRICTED | Only publish after platform + data-protection review | CSC / controlled storage |
| Document-level annotations | RESTRICTED | Includes inferred political attributes and row-level findings | CSC / controlled storage |
| LLM summaries | RESTRICTED | Unless independently anonymised and disclosure-reviewed | CSC / controlled storage |
| Per-document embeddings | RESTRICTED | Linkability/reconstruction risk | CSC / controlled storage |
| Identifiable network edges | RESTRICTED | Aggregate only after disclosure review | CSC / controlled storage |
| Researcher notes | RESTRICTED | Can contain contextual identifiers | CSC / controlled storage |
| Conceptual codebooks | PUBLIC | Own work, no subject-level sensitive mappings | GitHub |
| Institutional dictionaries | PUBLIC AFTER REVIEW | Factual provenance/licensing documented | GitHub |
| Named public-figure dictionaries | PUBLIC AFTER REVIEW | Factual public metadata only; no inferred sensitive attributes | GitHub or controlled storage depending on use |
| Schemas / interchange formats | PUBLIC | No embedded production examples | GitHub |
| Prompts / methodology | PUBLIC | Replace real examples with synthetic examples | GitHub |
| Source code | PUBLIC | Secrets and private paths excluded | GitHub |
| Synthetic fixtures | PUBLIC | Clearly fictional, no copied production records | GitHub |
| Aggregate tables/figures | PUBLIC AFTER REVIEW | Disclosure-control and licensing check | GitHub / Zenodo / publication supplement |
| Collection/process metadata | PUBLIC | No identifiable subjects or private storage paths | GitHub / metadata repository |
| Provenance model | PUBLIC | Describe workflow without exposing protected records | GitHub |

## Codebook policy

Codebooks are research artifacts, but not all codebooks have the same publication status.

### Conceptual codebooks: PUBLIC

Definitions and operationalisations of discourse, articulation, nodal points, empty/floating signifiers, equivalence/difference, antagonism/frontier, collective subject, hegemony, affective investment, sentiment categories, ideology categories, actor types, topic definitions, and inclusion/exclusion rules should normally be public because they are part of reproducible methodology.

### Institutional dictionaries: PUBLIC AFTER REVIEW

Party, government, company, NGO, country and supranational-organisation dictionaries may normally be public if they contain factual information from legitimate public sources and provenance/licensing is documented.

### Named-person codebooks: RESTRICTED BY DEFAULT FOR INFERENCES

Do not publish mappings such as `person -> ideology`, `person -> political preference`, `person -> sentiment`, `person -> radicalisation score` or `person -> discourse position` merely because the source material was public. Political-opinion inference is especially sensitive.

Public political figures may appear in a public codebook when the entries are limited to non-inferred factual public information needed for reproducibility. This is a narrow exception, not blanket permission to publish analytical labels about people.

### EP24 Finland and Poland seed codebooks

Current `sources/codebooks/ep24_finland.md` and `sources/codebooks/ep24_poland.md` contain:

- public party/institution names and legacy party-family buckets;
- public political figures with factual party/office context;
- conceptual seed signifiers;
- country/election context; and
- provenance references to legacy internal workbooks/research diaries without publishing those source records.

Assessment: **appropriate to remain public after human review**, provided they remain factual/sensitising metadata and are not presented as validated findings about individuals. The legacy party-family buckets must stay explicitly marked as legacy descriptive metadata, not model-validated ideology. Any future subject-level inference fields must live in restricted storage rather than these public files.

If future codebooks mix public concepts with subject-level inferred attributes, split them into public and private layers. Private codebooks must be stored outside Git and protected by the same access controls as the research data.

## FAIR without publishing the corpus

FAIR does not mean "put all data on GitHub". A restricted dataset can still be made more Findable, Accessible under controlled conditions, Interoperable and Reusable through safe metadata.

For restricted datasets, publish a metadata record where appropriate containing:

- title, description, project and responsible institution
- collection period, platforms, countries and sampling method
- collection and processing method
- software/schema versions and related Git commit/release
- record count/size and file types at a non-identifying level
- processing stages
- access status and reason for restriction
- legal/ethical constraints
- retention/disposal policy
- contact/access-request route
- related publications and persistent identifier if deposited later

## Platform-specific review

GDPR is only one layer. Before releasing any source-platform identifiers or content, review:

1. data protection and research ethics;
2. copyright/database rights;
3. current platform Terms of Service;
4. API/developer/commercial-provider agreements;
5. University of Helsinki and project-specific requirements.

Do not assume that historical practices such as "dehydrated" ID datasets remain valid for every platform or agreement.

## Licensing

Licensing is evaluated separately by artifact type.

- **Software:** retain the repository's software license unless deliberately changed.
- **Documentation:** consider CC BY where attribution is desirable.
- **Original schemas / simple metadata / synthetic datasets / original factual codebooks:** CC0 can be considered only where the project owns the relevant rights and a human review approves it.
- **Third-party social-media content:** never treat CC0 as a mechanism to erase copyright, privacy/data-protection, publicity or contractual restrictions.

CC0 waives the affirmer's copyright-related rights to the extent legally possible; it does not remove privacy/publicity rights or rights held by other people.

## Publication checklist

Before adding a research-related artifact to Git or a public release, answer all of the following:

- Does it contain or enable recovery of a real user's content, identity or profile?
- Does it reveal or infer political opinions or other special-category data about a person?
- Is an exact quote searchable back to its author?
- Can seemingly anonymous fields be joined back to public records?
- Is the artifact sufficiently aggregated, and have small/rare groups been reviewed?
- Does it contain a private path, production URL, token or credential?
- Is it copied from third-party copyrighted/database material?
- Do platform/API/provider terms allow this form of redistribution?
- Does the project own the rights needed for the proposed licence?
- Has a human researcher reviewed the release?

If any answer is uncertain, classify the artifact as **RESTRICTED** until reviewed.