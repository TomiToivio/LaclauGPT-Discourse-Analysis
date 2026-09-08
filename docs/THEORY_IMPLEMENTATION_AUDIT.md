# THEORY.md implementation audit

Status: initial repository audit for issue #50, updated for issue #48.

Canonical semantic contract: [`THEORY.md`](../THEORY.md).

This audit separates machine-checkable constraints from interpretive validity. Passing unit tests can verify schema/prompt guardrails, but it cannot establish that a Laclaudian interpretation is substantively correct. LaclauGPT remains human-in-the-loop, human-verified research: model outputs are preliminary analysis to be checked against source evidence by a human researcher.

## Scope reviewed

The audit covers the theory-facing surfaces requested in issue #50 and the module-switch/provenance surfaces corrected in issue #48:

- `prompts/discourse.py`
- `prompts/populism.py`
- `prompts/postprocess.py`
- root `pipeline.py`
- `run_config.py`
- `laclaugpt/canonical_pipeline.py`
- `laclaugpt_interchange/`
- canonical `laclaugpt/model/`
- Context Memory/codebook boundaries
- corpus synthesis
- tests
- visualization labels/data contract
- collector/analysis boundary
- `README.md`
- `paper/PAPER.md`
- `HERMES.md`
- `CLAUDE.md`
- `docs/HERMES_INTEGRATION.md`
- relevant implementation/interoperability/visualization documentation

## Findings by invariant

### INV_EVIDENCE: aligned

Theory-facing prompt schemas require evidence quotes for substantive document-level codings. The pipeline verifies whether proposed evidence occurs in the source and propagates evidence/evidence-source fields into interchange output. Canonical domain classes such as `Articulation`, `DiscursiveRelation`, `DiscursiveRoleAssignment`, `CollectiveSubject`, `AntagonisticFrontier`, `AffectiveInvestment`, `PopulistConfiguration`, and `HegemonyAssessment` carry evidence IDs.

Descriptive sentiment is not a Laclaudian coding family, but schema 1.4 now preserves its target, polarity, source/evidence marker, uncertainty, actual postprocess model, prompt version and provisional review state rather than silently discarding the reading.

Mechanical quote/source presence is not interpretive validation. Humans still decide whether the passage supports the coding.

### INV_ABSTAIN: aligned

`prompts/populism.py` supports `populist=false` and requires a reason when the Formula of Populism is not evidenced. Empty lists are valid outputs. The discourse prompt likewise permits empty output rather than forced interpretation. Descriptive sentiment may also abstain by returning no reading when polarity is not source-supported.

### INV_RELATIONAL: aligned

`prompts/discourse.py` defines articulation/equivalence/difference/antagonism relationally rather than as keyword classes. The descriptive analysis package explicitly states that NER/topics/similarity and related computational layers generate descriptive features or candidates, not Laclaudian judgements. Canonical model code also separates `DiscursiveRelationType` from `ComputationalRelationType`.

### INV_FLOAT_CORPUS: aligned

Document-level output uses `floating_candidate`, not a final floating-signifier finding. The Pydantic validator forces `needs_corpus_validation=true` for floating candidates. Corpus synthesis aggregates evidence but leaves final floating status to human adjudication.

### INV_EMPTY_CHAIN: aligned

The discourse and populism prompts explicitly reject polysemy/vagueness as sufficient evidence for an empty signifier. Document-level output is an `empty_candidate`; final emptiness remains a corpus/human judgement.

### INV_HEGEMONY_CORPUS: aligned

The discourse prompt states that hegemony cannot be inferred from frequency in a single document. Corpus synthesis is explicitly descriptive, labels signifier frequency as non-hegemonic evidence, and leaves hegemony to human adjudication. `HegemonyAssessment` supports separate frequency, actor coverage, institutional uptake, stability and contestation metrics rather than collapsing hegemony into a count.

### INV_ANTAGONISM: aligned

Both theory-facing prompts distinguish constitutive antagonistic frontier construction from ordinary criticism, policy disagreement, negativity, opponent mention or sentiment.

### INV_AFFECT: aligned (UI gate fixed)

The Formula of Populism prompt does not map Us to positive affect or Frontier to negative affect. The interchange schema keeps `Affect` and schema-1.4 `SentimentObservation` as separate record families. The postprocess prompt explicitly says descriptive polarity is not affective investment. The visualization Affects view is gated by Palonen analysis rather than the descriptive sentiment switch.

### INV_POPULISM: aligned

`prompts/populism.py` validates that `populist=true` requires both evidenced Us and Frontier elements. `populist=false` requires empty sides and a non-populist reason. The theory-contract regression tests protect this behaviour.

### INV_DYNAMIC_LABELS: no violating runtime classifier found

The current public core does not assign Palonen's fringe/mainstream/competing dynamics as permanent actor types. `THEORY.md` defines them as corpus-level relational dynamics. If implemented later, they must remain time/relationship/arena dependent.

### INV_HUMAN_REVIEW: aligned

The interchange defaults to `requires_human_review=true` and `review_status="PROVISIONAL"`; descriptive sentiment observations also default to `PROVISIONAL`. The dashboard stores researcher review in a separate sidecar instead of overwriting model output. The README carries a prominent human-in-the-loop warning. Agent instruction files require the theory contract before theory-facing work.

### INV_CONTEXT: aligned

`prompts/discourse.py` supports `asserted`, `quoted`, `reported`, `rejected`, `parodied`, and `uncertain` claim statuses. `pipeline.py` propagates claim status into interchange output so downstream analysis can distinguish authorial assertion from quoted/reported/rejected material.

## Module-switch alignment (issue #48)

The project `analysis` map is now authoritative beyond provenance labels:

- `sentiment:false` does not request sentiment extraction from the shared postprocess prompt and publishes no `sentiment_observations`; `sentiment:true` round-trips descriptive observations through schema 1.4;
- `context_memory:false` prevents codebook context from entering Summary, Discourse, Postprocess and Populism prompts. Stable-ID resolution remains enabled because it is canonical interchange/provenance infrastructure, not prompt context;
- `temporal:false` prevents Context Memory relation-history writes. Source timestamps remain source provenance and are not erased.

These semantics are covered by `tests/test_module_switches.py` and documented in `docs/CANONICAL_CONFIGURATION.md`.

## Component audit

### `prompts/discourse.py`

Strong alignment. It is evidence-first, distinguishes descriptive NLP from theoretical inference, uses candidate language for corpus-level concepts, preserves uncertainty, and records claim context. No clear theory correction was required.

### `prompts/populism.py`

Strong alignment. It operationalises the Formula as a diagnostic heuristic, requires Us + Frontier, permits abstention, requires evidence, and keeps affect independent of side polarity. No clear theory correction was required.

### `prompts/postprocess.py`

Descriptive only. Topics/entities/sentiment are requested only when their project switches are enabled. Sentiment is source-supported, uncertainty-bearing and explicitly separated from Laclaudian affect.

### `pipeline.py`

Strong alignment. Quote/source verification, provenance, Context Memory resolution and descriptive corpus synthesis preserve the theory boundary. Floating/empty/hegemony outputs remain candidates/evidence for later human adjudication. Project switches control Context Memory injection and temporal side effects.

### Interchange and canonical model

Human review is explicit/provisional. Affect and sentiment remain distinct. Theory-facing relation/role classes preserve evidence. Compatibility fields such as `nodal_points` should be understood as candidate document-level readings until corpus/human validation.

### Context Memory/codebook

Retrieved codebook candidates are hints, not evidence. When enabled, prompts explicitly say source material must support them. When `context_memory:false`, prompt injection is disabled while stable-ID resolution stays available for reproducible interchange.

### Visualization

The dashboard exposes source evidence, uncertainty, provenance, model review status and a separate researcher-review sidecar. Nodal output is presented as candidate output in aggregate views. The Affects view is not gated by descriptive sentiment.

### Collector boundary

The collector performs acquisition/normalisation, not discourse-theoretical classification. Theory-guided interpretation remains in the analysis pipeline. This separation should be preserved.

### Paper and README

`paper/PAPER.md` distinguishes frequency from hegemony, ambiguity from emptiness, criticism from antagonism, and sentiment from affective investment. The README makes the human-verification requirement prominent and points readers to the theory contract.

### Agent instructions

The repository has theory-contract instructions for Hermes and Claude, plus framework-neutral [`AGENTS.md`](../AGENTS.md). Agents are required to read `THEORY.md` before theory-facing changes, identify relevant invariants, preserve evidence/uncertainty/abstention/human review, and verify theoretical changes against the original books.

## Machine-checkable safeguards

`tests/test_theory_invariants.py` checks machine-verifiable parts of the theory contract. `tests/test_module_switches.py` separately checks configuration semantics relevant to issue #48, including descriptive sentiment round-trip, disabled-prompt behaviour, Context Memory ablation and temporal relation-history writes.

These tests are guardrails, not a validity test for discourse analysis.

## Remaining interpretive boundary

Corpus-level claims such as floating/empty signifier status, hegemony, polarisation, myths/imaginaries and ideological formations remain substantive human research judgements. The code can aggregate comparable evidence and candidates, but unit tests cannot decide whether those interpretations are valid.

## Conclusion

The current public core is substantially aligned with `THEORY.md`. Issue #48 closes an important reproducibility gap: module switches now describe actual prompt/output/state behaviour rather than merely appearing in provenance. Future theory-facing changes should treat `THEORY.md` as a semantic contract while keeping the original books authoritative.
