# THEORY.md implementation audit

Status: initial repository audit for issue #50.

Canonical semantic contract: [`THEORY.md`](../THEORY.md).

This audit separates machine-checkable constraints from interpretive validity. Passing unit tests can verify schema/prompt guardrails, but it cannot establish that a Laclaudian interpretation is substantively correct. LaclauGPT remains human-in-the-loop, human-verified research: model outputs are preliminary analysis to be checked against source evidence by a human researcher.

## Scope reviewed

The audit covered the theory-facing surfaces requested in issue #50:

- `prompts/discourse.py`
- `prompts/populism.py`
- root `pipeline.py`
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

Important boundary: mechanical quote presence is not interpretive validation. Human researchers still decide whether a passage supports the proposed coding.

### INV_ABSTAIN: aligned

`prompts/populism.py` supports `populist=false` and requires a reason when the Formula of Populism is not evidenced. Empty lists are valid outputs. The discourse prompt likewise permits empty output rather than forced interpretation.

### INV_RELATIONAL: aligned

`prompts/discourse.py` defines articulation/equivalence/difference/antagonism relationally rather than as keyword classes. The descriptive analysis package explicitly states that NER/topics/similarity and related computational layers generate descriptive features or candidates, not Laclaudian judgements. Canonical model code also separates `DiscursiveRelationType` from `ComputationalRelationType`.

### INV_FLOAT_CORPUS: aligned

Document-level output uses `floating_candidate`, not a final floating-signifier finding. The Pydantic validator forces `needs_corpus_validation=true` for floating candidates. Corpus synthesis aggregates evidence but leaves final floating status to human adjudication.

### INV_EMPTY_CHAIN: aligned

The discourse and populism prompts explicitly reject polysemy/vagueness as sufficient evidence for an empty signifier. Document-level output is an `empty_candidate`; final emptiness remains a corpus/human judgement.

### INV_HEGEMONY_CORPUS: aligned

The discourse prompt states that hegemony cannot be inferred from frequency in a single document. Corpus synthesis is explicitly descriptive and leaves hegemony to human adjudication. `HegemonyAssessment` supports separate frequency, actor coverage, institutional uptake, stability and contestation metrics rather than collapsing hegemony into a count.

### INV_ANTAGONISM: aligned

Both theory-facing prompts distinguish constitutive antagonistic frontier construction from ordinary criticism, policy disagreement, negativity, opponent mention or sentiment.

### INV_AFFECT: aligned (UI gate fixed)

The Formula of Populism prompt does not map Us to positive affect or Frontier to negative affect. The interchange schema keeps affect and optional sentiment polarity separate, and the source contains an explicit warning that polarity is not inferred from side membership.

The visualization previously gated the Affects tab on `sentiment or palonen`. The tab displays stored `Affect` records rather than deriving affective investment from sentiment, so this was not an inference violation — but the gate wording could be misread as equating sentiment and affect. Resolved in this PR (issue #50 follow-up): the tab is now gated on `palonen` alone, the stage that produces the Affect records, so the view's visibility can no longer suggest that the descriptive sentiment switch controls affective investment.

### INV_POPULISM: aligned

`prompts/populism.py` validates that `populist=true` requires both evidenced Us and Frontier elements. `populist=false` requires empty sides and a non-populist reason. The theory-contract regression tests protect this behaviour.

### INV_DYNAMIC_LABELS: no violating runtime classifier found

The current public core does not assign Palonen's fringe/mainstream/competing dynamics as permanent actor types. `THEORY.md` defines them as corpus-level relational dynamics. If implemented later, they must remain time/relationship/arena dependent.

### INV_HUMAN_REVIEW: aligned

The interchange defaults to `requires_human_review=true` and `review_status="PROVISIONAL"`. The dashboard stores researcher review in a separate sidecar instead of overwriting model output. The README carries a prominent human-in-the-loop warning. Agent instruction files now require the theory contract before theory-facing work.

### INV_CONTEXT: aligned

`prompts/discourse.py` supports `asserted`, `quoted`, `reported`, `rejected`, `parodied`, and `uncertain` claim statuses. `pipeline.py` propagates claim status into interchange output so downstream analysis can distinguish authorial assertion from quoted/reported/rejected material.

## Component audit

### `prompts/discourse.py`

Strong alignment. It is evidence-first, distinguishes descriptive NLP from theoretical inference, uses candidate language for corpus-level concepts, preserves uncertainty, and records claim context. No clear theory correction was required.

### `prompts/populism.py`

Strong alignment. It operationalises the Formula as a diagnostic heuristic, requires Us + Frontier, permits abstention, requires evidence, and keeps affect independent of side polarity. No clear theory correction was required.

### `pipeline.py`

Strong alignment. It verifies quote occurrence, preserves claim status and provenance, resolves stable Context Memory references, and keeps corpus synthesis descriptive. Floating/empty/hegemony outputs remain candidates/evidence for human adjudication.

### Interchange and canonical model

Human review is explicit/provisional. Affect and sentiment remain distinct. Theory-facing relation/role classes preserve evidence. Compatibility fields such as `nodal_points` should be understood as candidate document-level readings until corpus/human validation.

### Context Memory/codebook

Retrieved codebook candidates are hints, not evidence. Current prompts explicitly say source material must support them, satisfying the Context Memory boundary.

### Visualization

The dashboard exposes source evidence, uncertainty, provenance, model review status and a separate researcher-review sidecar. Nodal output is presented as candidate output in aggregate views. The Affects view is no longer gated by descriptive sentiment.

### Collector boundary

The collector performs acquisition/normalisation, not discourse-theoretical classification. Theory-guided interpretation remains in the analysis pipeline. This separation should be preserved.

### Paper and README

`paper/PAPER.md` already states the central distinctions reflected in `THEORY.md`: frequency is not hegemony; ambiguity/polysemy is not emptiness; criticism is not antagonism; sentiment is not affective investment; model outputs are provisional and human-reviewable. The README now makes the human-verification requirement highly visible.

### Agent instructions

The main gap motivating issue #50 was agent context. The repository now has theory-contract instructions for Hermes and Claude, plus framework-neutral [`AGENTS.md`](AGENTS.md). Agents are required to read `THEORY.md` before theory-facing changes, identify relevant invariants, preserve evidence/uncertainty/abstention/human review, and verify theoretical changes against the original books.

## Machine-checkable safeguards

`tests/test_theory_invariants.py` checks machine-verifiable parts of the contract, including:

- Formula of Populism requires both Us and Frontier;
- abstention/non-populist output is valid;
- theory-facing schemas preserve evidence;
- floating/empty candidates require corpus validation;
- affect is not inferred from sentiment polarity or side membership;
- the visualization does not gate affect by the sentiment switch;
- agent-facing documentation references `THEORY.md`.

These tests are guardrails, not a validity test for discourse analysis.

## Remaining interpretive boundary

Corpus-level claims such as floating/empty signifier status, hegemony, polarisation, myths/imaginaries and ideological formations remain substantive human research judgements. The code can aggregate comparable evidence and candidates, but unit tests cannot decide whether those interpretations are valid.

## Conclusion

The current public core is substantially aligned with `THEORY.md`. Issue #50 primarily closes an **agent-context and regression-safety gap**, rather than correcting a major theoretical error in the existing prompts. Future theory-facing changes should treat `THEORY.md` as a semantic contract while keeping the original books authoritative.