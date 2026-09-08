# THEORY.md implementation audit

Status: initial repository audit for issue #50.

Canonical semantic contract: [`THEORY.md`](../THEORY.md).

This audit separates machine-checkable constraints from interpretive validity. Passing tests can verify schema/prompt guardrails, but it cannot establish that a Laclaudian interpretation is substantively correct. LaclauGPT remains human-in-the-loop, human-verified research: model outputs are preliminary analysis to be checked against source evidence by a human researcher.

## Scope reviewed

The audit covered the theory-facing surfaces requested in issue #50:

- `prompts/discourse.py`
- `prompts/populism.py`
- root `pipeline.py`
- `laclaugpt_interchange/`
- canonical `laclaugpt/model/`
- Context Memory/codebook boundaries
- tests
- visualization labels/data contract
- collector/analysis boundary
- `README.md`
- `paper/PAPER.md`
- `HERMES.md`
- `CLAUDE.md`
- relevant implementation/interoperability/visualization documentation

## Findings by invariant

### INV_EVIDENCE: aligned

Theory-facing prompt schemas require evidence quotes for substantive document-level codings. The pipeline verifies whether proposed evidence occurs in the source and propagates evidence/evidence-source fields into interchange output. Canonical domain classes such as `Articulation`, `DiscursiveRelation`, `DiscursiveRoleAssignment`, `CollectiveSubject`, `AntagonisticFrontier`, `AffectiveInvestment`, `PopulistConfiguration`, and `HegemonyAssessment` carry evidence IDs.

Mechanical quote presence is not interpretive validation. Humans still decide whether the passage supports the coding.

### INV_ABSTAIN: aligned

`prompts/populism.py` supports `populist=false` and requires a reason when the Formula of Populism is not evidenced. Empty lists are valid outputs. The discourse prompt likewise permits empty output rather than forced interpretation.

### INV_RELATIONAL: aligned

`prompts/discourse.py` defines articulation/equivalence/difference/antagonism relationally rather than as keyword classes. The descriptive analysis package states that NER/topics/similarity and related computational layers generate descriptive features or candidates, not Laclaudian judgements. Canonical model code also separates `DiscursiveRelationType` from `ComputationalRelationType`.

### INV_FLOAT_CORPUS: aligned

Document-level output uses `floating_candidate`, not a final floating-signifier finding. The Pydantic validator forces corpus validation for floating candidates. Corpus synthesis aggregates evidence but leaves final floating status to human adjudication.

### INV_EMPTY_CHAIN: aligned

The discourse and populism prompts explicitly reject polysemy/vagueness as sufficient evidence for an empty signifier. Document-level output is an `empty_candidate`; final emptiness remains a corpus/human judgement.

### INV_HEGEMONY_CORPUS: aligned

The discourse prompt states that hegemony cannot be inferred from frequency in a single document. Corpus synthesis is explicitly descriptive and leaves hegemony to human adjudication. `HegemonyAssessment` supports separate frequency, actor coverage, institutional uptake, stability and contestation metrics rather than collapsing hegemony into a count.

### INV_ANTAGONISM: aligned

Both theory-facing prompts distinguish constitutive antagonistic frontier construction from ordinary criticism, policy disagreement, negativity, opponent mention or sentiment.

### INV_AFFECT: aligned

The Formula of Populism prompt does not map Us to positive affect or Frontier to negative affect. The interchange schema keeps affect and optional sentiment polarity separate. The visualization was corrected so the Affects view is gated by the Palonen analysis stage rather than the descriptive sentiment switch.

### INV_POPULISM: aligned

`prompts/populism.py` validates that `populist=true` requires both evidenced Us and Frontier elements. `populist=false` requires empty sides and a non-populist reason. `tests/test_theory_invariants.py` protects this behaviour.

### INV_DYNAMIC_LABELS: no violating runtime classifier found

The current public core does not assign Palonen's fringe/mainstream/competing dynamics as permanent actor types. `THEORY.md` defines them as corpus-level relational dynamics. If implemented later, they must remain time/relationship/arena dependent.

### INV_HUMAN_REVIEW: aligned

The interchange defaults to `requires_human_review=true` and `review_status="PROVISIONAL"`. The dashboard stores researcher review in a separate sidecar instead of overwriting model output. The README carries a prominent human-in-the-loop warning. Agent instruction files now require the theory contract before theory-facing work.

### INV_CONTEXT: aligned

`prompts/discourse.py` supports `asserted`, `quoted`, `reported`, `rejected`, `parodied`, and `uncertain` claim statuses. `pipeline.py` propagates claim status into interchange output so downstream analysis can distinguish authorial assertion from quoted/reported/rejected material.

## Component audit

### `prompts/discourse.py`

Strong alignment. Evidence-first; candidate terminology for corpus-level concepts; explicit claim context; uncertainty and abstention retained.

### `prompts/populism.py`

Strong alignment. Formula treated as diagnostic heuristic; Us + Frontier required; abstention valid; affects evidenced and not polarity-mapped from side membership.

### `pipeline.py`

Strong alignment. Quote verification, provenance, Context Memory resolution and descriptive corpus synthesis all preserve the theory boundary. Floating/empty/hegemony outputs remain candidates/evidence for later human adjudication.

### Interchange and canonical model

Human review is explicit/provisional. Affect and sentiment remain distinct. Theory-facing relation/role classes preserve evidence. Compatibility fields such as `nodal_points` should be understood as candidate document-level readings until corpus/human validation.

### Context Memory/codebook

Retrieved codebook candidates are hints, not evidence. Current prompts explicitly say source material must support them, satisfying the Context Memory boundary.

### Visualization

The dashboard exposes source evidence, uncertainty, provenance, model review status and a separate researcher-review sidecar. Nodal output is presented as candidate output in aggregate views. The Affects view is no longer gated by descriptive sentiment.

### Collector boundary

The collector performs acquisition/normalisation, not discourse-theoretical classification. Theory-guided interpretation remains in the analysis pipeline. This separation should be preserved.

### Paper and README

`paper/PAPER.md` already distinguishes frequency from hegemony, ambiguity from emptiness, criticism from antagonism, and sentiment from affective investment. The README makes the human-verification requirement prominent and points readers to the theory contract.

### Agent instructions

The main gap motivating issue #50 was agent context. The repository now has theory-contract instructions for Hermes and Claude, plus framework-neutral [`AGENTS.md`](../AGENTS.md). Agents are required to read `THEORY.md` before theory-facing changes, identify relevant invariants, preserve evidence/uncertainty/abstention/human review, and verify theoretical changes against the original books.

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

## Round 2 audit: full invariant sweep (2026-09-08, issue #50)

A second, deeper audit pass re-checked every theory-facing surface against the
§14 concept registry and §15 invariants, reading `prompts/`, root `pipeline.py`,
`laclaugpt_interchange/`, `laclaugpt/model/`, `laclaugpt_memory/`,
`laclaugpt/memory/`, `laclaugpt/adapters/`, `inception_adapter/`, the
visualization layer, collector/analysis boundaries and the documentation. This
round found residual **schema-level and publication-level** mismatches that the
prompt-level audit had missed; they are fixed in the same change as this audit:

| # | Invariant | Finding | Resolution |
|---|---|---|---|
| 1 | INV_POPULISM | Interchange schema accepted `populist=true` with empty `us`/`frontier` (enforcement existed only at the prompt stage); 4CAT/DNA/INCEpTION consume the interchange, not the prompt schema | `DocumentAnnotation` model validator rejects `populist=true` without both sides; `build_annotation` computes Us/Frontier refs before construction |
| 2 | INV_CONTEXT | `PopulismElement` had no `claim_status` field although the prompt instructs distinguishing quoted/reported/parodied/rejected speech — a quoted politician's articulation could silently become the author's `populist=true` | `claim_status` added to prompt schema (`populism-v3.1`), stage output, `PopulismElementAssessment` and `from_memory_results` |
| 3 | INV_CONTEXT | `interchange_to_v2()` flattened every articulation to `attribution_type="unclear"`, destroying the asserted/non-asserted distinction | `claim_status` maps to `AttributionType` (asserted→author, quoted→quoted, reported→reported, parodied→ironic; rejected/uncertain conservatively stay unclear) |
| 4 | INV_ABSTAIN | The discourse stage's `applicable`/`applicability_reason` abstention signal was captured then discarded — a "not applicable" document was indistinguishable from an empty coding | Published as `discourse_applicable` / `discourse_applicability_reason` (schema 1.5) |
| 5 | INV_RELATIONAL / INV_EVIDENCE | `ann.discourses` assigned **every** coded signifier to **every** formation candidate — a membership relation the model never asserted | Formation candidates are published as labels with their own evidence; membership is left to human/corpus adjudication |
| 6 | Config authority | `SentimentObservation.model` recorded the run-level aggregate (`"mixed"` for mixed-model runs), breaking per-reading auditability | Sentiment readings record the postprocess stage's actual model from stage provenance |
| 7 | INV_POPULISM | Human INCEpTION corrections could leave `populist=false` with both sides human-added (or `populist=true` after edits made a side unevidenced) — contradictory exports | `merge_inception_corrections` re-derives Formula-of-Populism coherence after merging |
| 8 | INV_ANTAGONISM / INV_RELATIONAL | `prompts/discourse.py` coded antagonism/equivalence without the THEORY §3 negations (criticism ≠ antagonism; similarity ≠ equivalence) | Negations added to the operational-distinctions block (`discourse-v1.1`) |
| 9 | INV_AFFECT | `docs/VISUALIZATION.md` still said `sentiment`/`palonen` enable affect views, contradicting the merged Affects-tab gate fix | Documentation corrected |

The interchange schema version is now **1.5** (version lives in
`laclaugpt_interchange.SCHEMA_VERSION`). New fields have defaults, so older
JSONL files remain readable, and the `populist` validator only rejects files
that violate the theory contract itself.

### Follow-up issues (interpretive / soft findings, not auto-fixed)

The audit also produced findings that require human research-methods decisions
rather than mechanical fixes; they are recorded as follow-up issues rather than
forced code changes:

- partial evidence is dropped when the Formula of Populism abstains
  (`populist=false` requires empty side lists, so an evidenced Us without a
  Frontier is narrated only in prose);
- `hegemonic_evidence` strings are not run through the verbatim evidence gate
  applied to every other coding family;
- seed-codebook definitions pre-assign roles and side-coded affects
  (priming; hints are demoted in the prompts but the definitions remain
  polarity-bearing);
- Context Memory: EXISTING-decision fallback binds to ≥0.60 fuzzy similarity
  without a human; `rejected_merges` is recorded but not consulted by
  `resolve()`; auto-reuse at 0.98 similarity; usage-ordered "Established
  candidates" priming;
- canonical `DiscursiveRole` enum allows settled floating/empty-signifier
  assignments (nothing constructs them yet; candidate discipline lives in the
  prompt layer and the interchange);
- interchange evidence fields are optional at schema level (pipeline always
  populates and verifies them; hard schema enforcement must respect the
  cross-version readability policy);
- `interchange_to_v2()` lifts only entities/topics/signifiers/articulations —
  populism, affects, signifier roles and review state are not yet lifted;
- visualization display gaps: `claim_status` column, `non_populist_reason`,
  `counter_evidence` and `needs_corpus_validation` are recorded but not shown;
- documentation drift: `INTEROPERABILITY_SPEC.md` Formula example says
  `"detected": true` and uses the mechanical Us→positive / Frontier→negative
  affect example; `LAYERED_CONFIGURATION_AND_IMAGINARIES.md` predates the
  arena layer;
- postprocess sentiment extraction does not distinguish quoted/reported
  speech from author voice (descriptive family, but attribution would help).
