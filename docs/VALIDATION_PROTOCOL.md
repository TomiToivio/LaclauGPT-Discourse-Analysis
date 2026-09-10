# LaclauGPT Validation Protocol

Version: 0.1-draft
Status: reviewable research protocol, not completed empirical validation
Scope: LaclauGPT discourse coding for *Ideological contestation over AI*

This protocol operationalises the validation commitments described in paper §4.2. It defines a reproducible study design for evaluating bounded LLM-assisted coding tasks while preserving the distinction between document-level coding and corpus-level interpretive judgement. It does not report validation results and does not create or imply a paper deadline.

## 1. Validation questions

The validation study evaluates whether LaclauGPT can reliably support human researchers in proposing evidence-linked document-level codings without silently converting provisional interpretations into findings.

The bounded tasks are evaluated separately:

1. applicability and abstention;
2. signifier-role proposals;
3. articulation relation coding;
4. claim status and speaker attribution;
5. sociotechnical-imaginary candidates;
6. ideological-formation candidates;
7. Palonen Formula of Populism elements and verdict support;
8. evidence-span localisation.

Corpus-level judgements such as hegemony, stable ideological formations, floating-signifier status, tendential emptiness, persistent polarisation, or sedimented imaginaries are not treated as ordinary classification targets. They require comparative human interpretation across sources and are evaluated through case-based adjudication rather than document-level accuracy scores.

## 2. Corpus definition and eligibility

The validation corpus MUST be frozen before final evaluation.

### Inclusion

Include documents that:

- belong to the AI/AGI ideological-contestation research domain;
- come from one of the declared empirical arenas: AI elites, grassroots mobilisation, or parliamentary/electoral politics;
- contain enough recoverable source material for a human coder to inspect the relevant claim or to make a justified abstention;
- fall inside the declared observation period for the validation study;
- use a language included in the registered validation manifest.

### Exclusion

Exclude or separately flag documents that:

- cannot be inspected because the underlying source is unavailable;
- contain only corrupted or empty extracted text;
- are exact duplicates or near-duplicates assigned to another split;
- consist solely of machine-generated summaries when the source representation is unavailable;
- contain private or restricted material that cannot be made available to the authorised validation coders.

Uncertain, zero-code, irrelevant and model-abstained documents MUST remain eligible when they otherwise meet the inclusion rules. They are necessary for measuring overcoding and abstention behaviour.

### Observation period, languages and source types

These are registered study decisions and MUST be fixed before the evaluation sample is drawn.

UNRESOLVED STUDY DECISION:
- exact observation start/end dates;
- final language set;
- exact platform/source mix within each arena.

The initial pilot SHOULD use English plus one additional project language if coder capacity permits. If only English is feasible for the first reproducible study, multilingual generalisation must be reported as unevaluated rather than inferred.

## 3. Sampling design

### Development set

Recommended: 60 documents.

Purpose:
- codebook training;
- prompt debugging;
- coder calibration;
- identification of ambiguous categories;
- checking that the annotation interface and export format work.

The development set is not used for final performance reporting.

### Held-out evaluation set

Recommended minimum: 180 documents, allocated as approximately 60 documents per arena.

Within each arena, sampling SHOULD be stratified so the held-out set contains:

- documents with expected substantive coding;
- uncertain/borderline documents;
- zero-code or non-applicable documents;
- cases containing quotation, reported speech, rejection or parody where available;
- documents likely to trigger model abstention.

This size is a feasibility target rather than a power-derived optimum. It is large enough to expose recurrent errors across three arenas while remaining realistically double-coded and adjudicated. The final registered sample size SHOULD be justified against coder capacity before annotation starts.

### Sampling manifest

The restricted sampling manifest MUST record at least:

- validation_case_id;
- source document identifier;
- arena;
- language;
- source type/platform;
- source timestamp;
- parent/thread identifier where available;
- duplicate-group identifier;
- inclusion/exclusion status and reason;
- split: development or held-out evaluation;
- collector identifier and collector commit/version;
- matcher/parser identifier where relevant;
- preprocessing/transformation versions;
- corpus snapshot identifier.

The manifest MUST NOT be committed to the public repository if it contains restricted row-level research data.

## 4. Leakage prevention

Leakage controls are mandatory.

1. Exact duplicates and near-duplicates MUST be grouped before splitting.
2. Parent documents, quoted reposts, thread segments, or tightly coupled conversation items SHOULD remain in the same split unless the study explicitly tests cross-context generalisation.
3. No held-out document may be used for prompt development, codebook revision, Context Memory curation, threshold tuning, or manual debugging before the final evaluation run.
4. The seed codebook and Context Memory used for final evaluation MUST be frozen and identified by version/hash or immutable snapshot.
5. Prompt versions, schema version, runtime configuration and model identifiers/digests MUST be frozen before evaluation.
6. If the collector or preprocessing stack changes in a way that changes corpus membership or source representation, the evaluation corpus snapshot changes and MUST receive a new version.
7. Evaluation-set corrections after unblinding MUST be logged rather than silently replacing the original set.

## 5. Human coding procedure

### Initial coders

At least two independent human coders MUST code every held-out evaluation document before adjudication.

Coders receive:

- the original inspectable source representation;
- relevant source metadata needed for interpretation;
- the frozen coding instructions;
- definitions grounded in Laclau, Mouffe and Palonen;
- explicit permission to abstain, mark uncertainty, and assign zero codes.

They MUST NOT see LaclauGPT output for the document before completing their independent coding.

### Training

Coders first train on the development set. Training may include discussion and revision of coding instructions. Changes made during training MUST be frozen before held-out coding starts.

### Blinding

For held-out coding:

- coders are blinded to LaclauGPT outputs;
- where practical, coders are blinded to each other's coding until both initial annotations are complete;
- final adjudicators SHOULD compare human and model interpretations without being told which candidate came from which source when the task format permits meaningful blinding.

### Adjudication

Adjudication does not overwrite the original annotations.

For each disagreement, preserve:

- coder A decision;
- coder B decision;
- LaclauGPT decision;
- evidence spans selected by each;
- adjudicated interpretation, if one is reached;
- unresolved-disagreement flag;
- short adjudication rationale.

Where a single authoritative code would falsely erase genuine interpretive plurality, the outcome SHOULD remain unresolved or multi-valued.

## 6. Evaluation measures

No single agreement statistic establishes validity.

### 6.1 Applicability, categories and prevalence

For bounded categorical tasks report:

- raw agreement;
- per-category precision, recall and F1 against the adjudicated reference where a reference judgement is defensible;
- category prevalence;
- confusion matrices where useful;
- inter-human agreement separately from human-model agreement.

Cohen's kappa or another chance-corrected statistic MAY be reported where its assumptions are reasonable, but never without prevalence and raw counts.

Denominator: all eligible cases for the specific coding task, including explicit zero-code/abstention cases unless the metric definition states otherwise.

### 6.2 Evidence-span matching

Evaluate whether the proposed evidence is actually present and whether it supports the coding.

Report separately:

- mechanical verbatim-presence rate;
- exact span match where applicable;
- token-level or character-level overlap for partially overlapping spans;
- blinded human judgement of whether the span substantively supports the code.

Mechanical quotation verification is not substantive validity.

### 6.3 Relation coding

For articulation/equivalence/difference/antagonism evaluate:

- source concept;
- target concept;
- relation type;
- supporting evidence;
- claim status where relevant.

A relation counts as a full match only when its endpoints and relation type match the declared reference under the study's matching rules. Partial matches SHOULD be reported separately rather than silently promoted to correct.

### 6.4 Speaker attribution and claim status

Evaluate asserted, quoted, reported, rejected, parodied and uncertain status separately.

Report:

- attribution-type agreement;
- attributed-speaker accuracy where an attributable speaker exists;
- false-author-endorsement rate, especially for quoted/rejected/parodied material;
- uncertain-attribution coverage.

Denominator for speaker accuracy: cases where the source and human adjudication support a determinate speaker attribution.

### 6.5 Abstention and coverage

Report:

- model coding coverage;
- abstention rate;
- error rate among coded cases;
- false-positive coding rate among human zero-code/non-applicable cases;
- false-abstention rate where humans agree that a supported code exists.

Coverage and error MUST be interpreted together. A system is not better merely because it codes more documents.

### 6.6 Uncertainty reporting

Model-reported confidence is uncalibrated unless empirical calibration is performed against a declared reference task.

For each coding family report performance by confidence bands only as an exploratory diagnostic unless calibration has been separately evaluated. Operational thresholds MUST be described as selection rules, not probabilities of correctness.

Uncertainty intervals for proportions SHOULD be reported with a declared method, preferably bootstrap intervals or Wilson intervals depending on the statistic. The method and resampling unit MUST be fixed before final reporting.

UNRESOLVED STUDY DECISION:
- final interval method;
- whether hierarchical/bootstrap resampling is needed for clustered thread/source structures.

## 7. Robustness and ablation

The final protocol includes at least:

1. one alternative LLM configuration;
2. seed-label/codebook ablation;
3. Context Memory ablation or frozen-memory comparison;
4. prompt-version robustness on a declared subset;
5. order/format perturbation where practical for prompts or supplied candidate lists.

Each run MUST record:

- prompt versions;
- model name and digest/version;
- runtime/backend;
- generation parameters;
- seed-codebook snapshot;
- Context Memory snapshot;
- collector/corpus snapshot;
- schema version;
- effective configuration fingerprint;
- run identifier.

Robustness comparisons use the same frozen source cases unless the comparison explicitly studies collection differences.

## 8. Error taxonomy

At minimum distinguish:

- unsupported evidence / fabricated quotation;
- evidence present but interpretively insufficient;
- wrong relation type;
- wrong relation endpoints;
- false antagonism from criticism or negative sentiment;
- false equivalence from similarity/co-occurrence;
- false nodal/floating/empty-signifier inference;
- false ideological-formation attribution;
- quotation/reported-speech attribution error;
- rejected/parodied claim treated as endorsement;
- missed supported coding;
- overcoding of zero-code/non-applicable material;
- inappropriate abstention;
- codebook/Context Memory priming error;
- preprocessing or collector error;
- schema/adapter/software failure;
- genuine human interpretive disagreement.

Negative cases MUST be examined qualitatively. Software failures and missing/corrupted source material MUST NOT be counted as ordinary discourse-coding disagreements without separate reporting.

## 9. Corpus-level interpretation

Corpus-level theoretical claims require human comparative assessment.

For candidate floating signifiers, empty signifiers, ideological formations, imaginaries, polarisation and hegemony, the study SHOULD prepare evidence bundles across documents, actors, arenas and/or time. Human researchers then assess whether the corpus-level relation is supported.

Evaluation here focuses on whether LaclauGPT retrieves and structures relevant evidence without systematically omitting counter-evidence or fabricating coherence. It does not reduce hegemony or ideological formation to a document-level classifier score.

## 10. Storage, privacy and reproducibility

Restricted artifacts:

- raw social-media/research corpus where licensing or ethics require restriction;
- row-level validation manifest containing source identifiers;
- human annotations linked to restricted source material;
- private reviewer/coder metadata;
- adjudication records that would expose restricted data.

Shareable artifacts SHOULD include:

- this protocol;
- frozen coding instructions/codebook where publication is appropriate;
- prompt versions;
- schema definitions;
- aggregation/evaluation code;
- synthetic regression examples;
- de-identified aggregate metrics;
- provenance specifications;
- manifest schema without restricted rows.

No research data or private reviewer details should be committed solely to satisfy this protocol.

## 11. Validation freeze record

Before final held-out evaluation, create a restricted validation freeze record containing:

- protocol version;
- corpus snapshot identifier;
- collector commit(s) and matcher/parser identifiers;
- preprocessing versions;
- development/evaluation split manifest hash;
- prompt versions;
- schema version;
- codebook snapshot/hash;
- Context Memory snapshot/hash;
- primary model and alternative model identifiers/digests;
- runtime/configuration fingerprints;
- planned metrics and denominators;
- unresolved decisions that were settled before unblinding.

Any material change after the freeze creates a new validation version or is reported transparently as a deviation.

## 12. Completion criterion

Completion of issue #91 means that a reproducible and reviewable validation protocol exists and that unresolved empirical design choices are explicit.

It does NOT mean:

- LaclauGPT has been empirically validated;
- model outputs are ground truth;
- software tests establish interpretive validity;
- the AI-ideology mapping is complete;
- a new paper deadline exists.

The validation study remains a separate empirical task requiring human coders, adjudication and reported results.
