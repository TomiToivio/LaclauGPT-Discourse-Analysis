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
- `docs/HERMES_INTEGRATION.md`
- relevant implementation/interoperability/visualization documentation

## Findings by invariant

### INV_EVIDENCE: aligned

Theory-facing prompt schemas require evidence quotes for substantive document-level codings. The pipeline verifies whether proposed evidence occurs in the source and propagates evidence/evidence-source fields into interchange output. Canonical domain classes such as `Articulation`, `DiscursiveRelation`, `DiscursiveRoleAssignment`, `CollectiveSubject`, `AntagonisticFrontier`, `AffectiveInvestment`, `PopulistConfiguration`, and `HegemonyAssessment` require evidence IDs.

Important boundary: mechanical quote presence is not interpretive validation. Human researchers still decide whether a passage supports the proposed coding.

### INV_ABSTAIN: aligned

`prompts/populism.py` explicitly supports `populist=false` and requires a reason when the Formula of Populism is not evidenced. Empty lists are valid outputs. The discourse prompt likewise states that an empty list is a valid result.

### INV_RELATIONAL: aligned

`prompts/discourse.py` defines articulation/equivalence/difference/antagonism relationally rather than as keyword classes. The descriptive analysis package explicitly states that NER/topics/similarity and related computational layers generate descriptive features or candidates, not Laclaudian judgements. Canonical model code also separates `DiscursiveRelationType` from `ComputationalRelationType`.

### INV_FLOAT_CORPUS: aligned

Document-level output uses `floating_candidate`, not a final floating-signifier finding. The Pydantic validator forces `needs_corpus_validation=true` for floating candidates. Corpus synthesis aggregates evidence but labels floating status a human adjudication.

### INV_EMPTY_CHAIN: aligned

The discourse and populism prompts explicitly reject polysemy/vagueness as sufficient evidence for an empty signifier. Document-level output is `empty_candidate`; the discourse schema forces corpus validation. Final emptiness remains a corpus/human judgement.

### INV_HEGEMONY_CORPUS: aligned

The discourse prompt says hegemony cannot be inferred from frequency in a single document. Corpus synthesis produces descriptive candidate evidence only and states explicitly that hegemony is a human adjudication. `HegemonyAssessment` supports separate frequency, actor coverage, institutional uptake, stability and contestation metrics rather than collapsing hegemony into one count.

### INV_ANTAGONISM: aligned

Both theory-facing prompts distinguish constitutive antagonistic frontier construction from ordinary criticism, policy disagreement, negativity, opponent mention or sentiment.

### INV_AFFECT: aligned (UI gate fixed)

The Formula of Populism prompt does not map Us to positive affect or Frontier to negative affect. The interchange schema keeps affect and optional sentiment polarity separate, and the source contains an explicit warning that polarity is not inferred from side membership.

The visualization previously gated the Affects tab on `sentiment or palonen`. The tab displays stored `Affect` records rather than deriving affective investment from sentiment, so this was not an inference violation — but the gate wording could be misread as equating sentiment and affect. Resolved in this PR (issue #50 follow-up): the tab is now gated on `palonen` alone, the stage that produces the Affect records, so the view's visibility can no longer suggest that the descriptive sentiment switch controls affective investment.

### INV_POPULISM: aligned

`prompts/populism.py` has a model validator: `populist=true` requires both evidenced Us and Frontier elements; `populist=false` requires both lists empty and a non-populist reason. The new theory-contract regression tests preserve this behaviour.

### INV_DYNAMIC_LABELS: no violating runtime classifier found

The current public core does not appear to assign Palonen's fringe/mainstream/competing dynamics as permanent actor types. `THEORY.md` defines them as corpus-level relational dynamics. If these dynamics are implemented later, they must be time/relationship/arena dependent rather than actor attributes.

### INV_HUMAN_REVIEW: aligned and strengthened

The interchange defaults to `requires_human_review=true` and `review_status="PROVISIONAL"`. The dashboard stores researcher review in a separate sidecar rather than overwriting model output. The README now carries a prominent human-in-the-loop warning.

Issue #50 strengthens agent compliance further by adding `AGENTS.md`, requiring Hermes to read `THEORY.md`, and testing that agent-facing context files preserve this requirement.

### INV_CONTEXT: aligned

`prompts/discourse.py` supports `asserted`, `quoted`, `reported`, `rejected`, `parodied`, and `uncertain` claim statuses. `pipeline.py` propagates `claim_status` into interchange articulations/imaginaries rather than discarding it. This prevents quoted or rejected positions from being silently treated as asserted author claims when downstream consumers respect the field.

## Component audit

### `prompts/discourse.py`

Strong alignment. It is evidence-first, distinguishes descriptive NLP from theoretical inference, uses candidate language for corpus-level concepts, preserves uncertainty, and records claim context. No clear theory correction was required.

### `prompts/populism.py`

Strong alignment. It operationalises the Formula as a diagnostic heuristic, requires Us + Frontier, permits abstention, requires evidence, and keeps affect independent of side polarity. No clear theory correction was required.

### `pipeline.py`

Strong alignment. It verifies quote occurrence, preserves claim status and provenance, resolves stable Context Memory references, and keeps corpus synthesis descriptive. Floating/empty/hegemony outputs remain candidates/evidence for human adjudication.

### Interchange and canonical model

The interchange schema visibly marks human review as required/provisional and separates affect from sentiment polarity. Canonical theory-facing relation/role classes carry evidence IDs. Compatibility fields such as `nodal_points` should be interpreted as candidate document-level readings unless human/corpus validation has occurred; visualization already labels aggregate nodal output as candidates.

### Context Memory/codebook

Context Memory supplies stable references and candidate context. It must not turn retrieved codebook entries into ground truth. Current prompts explicitly say retrieved codebook candidates are suggestions/hints and must be supported by the source, which satisfies the theory boundary.

### Visualization

The dashboard exposes source evidence, uncertainty, provenance, model review status and a separate researcher-review sidecar. Aggregate signifier counts are displayed descriptively; nodal output is labelled as candidate output in the corpus view. The main caveat is the UI configuration wording around sentiment/affect noted above.

### Collector boundary

No evidence was found that the collector performs discourse-theoretical coding. Collection remains source acquisition/normalisation, while theory-guided interpretation occurs in the analysis pipeline. This separation should be preserved.

### Paper and README

`paper/PAPER.md` already states the central distinctions reflected in `THEORY.md`: frequency is not hegemony; ambiguity/polysemy is not emptiness; criticism is not antagonism; sentiment is not affective investment; model outputs are provisional and human-reviewable. The README now makes the human-verification requirement highly visible.

### Agent instructions

This was the clearest gap found by the audit. `THEORY.md` was canonical but repository agents were not uniformly instructed to load it before theory-facing work. This issue adds:

- root `AGENTS.md` as a framework-independent agent contract;
- an explicit `THEORY.md` requirement in `HERMES.md`;
- the same boundary in `docs/HERMES_INTEGRATION.md`;
- regression tests checking that agent-facing context references the theory contract.

## Machine-checkable tests added

`tests/test_theory_contract.py` checks:

- all normative invariant IDs remain present in `THEORY.md`;
- `AGENTS.md` and `HERMES.md` require `THEORY.md` before theory-facing work;
- `populist=true` cannot validate without both Us and Frontier;
- abstention/non-populist output retains the expected empty-side shape;
- floating and empty candidates are forced to corpus validation;
- theory-facing articulation output cannot omit evidence;
- quoted claim status remains representable;
- interchange defaults remain human-review-required and provisional;
- the README keeps the human-verified/preliminary-analysis warning.

These tests are guardrails, not a validity test for discourse analysis.

## Remaining interpretive issues

1. **Sentiment vs affect visualization wording.** Resolved for the tab gate (this PR: Affects tab follows `palonen` alone). A standalone follow-up remains open for richer UI documentation: enabling or displaying an affect view does not transform sentiment scores into affective investment (see #51 for the summary-stage side of this concern).
2. **Corpus-level adjudication remains human work.** The repository can aggregate candidate evidence for floating/empty signifiers, hegemony, polarisation, myths/imaginaries and ideological formations, but deciding those statuses cannot be made correct by a unit-test rule alone.
3. **Dynamic populist typology is not yet a runtime classifier.** If Palonen's fringe/mainstream/competing dynamics are added, implementation should model relations over time/arena/frontier, not permanent actor labels.

## Conclusion

The current public core is substantially aligned with `THEORY.md`. The main repository-level defect addressed by issue #50 was not a methodological error in the analysis prompts, but an **agent-context gap**: agents were not uniformly required to read the semantic contract before theory-facing changes. This PR closes that gap and adds executable regressions for the parts of the theory contract that can responsibly be machine-checked.
