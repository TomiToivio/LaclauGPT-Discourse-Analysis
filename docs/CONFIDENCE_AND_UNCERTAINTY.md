# Model-reported confidence and uncertainty

LaclauGPT preserves the existing `confidence` field for interchange and cache
compatibility, but its meaning must be stated precisely.

## Theory-facing LLM codings

For Laclaudian discourse and Formula-of-Populism outputs, `confidence` is a
**model-reported, uncalibrated self-report** on the interval 0–1. It can be used
as an uncertainty signal for inspection, ranking, sampling, or sensitivity
analysis. It is **not** automatically a probability that the coding is correct.

Calling a value calibrated requires a separate validation exercise against a
declared reference task. Such a protocol should identify at least the reference
annotations or adjudication procedure, sampling/split design, model and prompt
versions, the calibration/error metric, and coverage/abstention behaviour.
Calibration belongs to validation, not to the generation prompt.

## What confidence does not replace

Model-reported confidence is deliberately separate from:

- source evidence: substantive theoretical coding still requires evidence;
- mechanical quotation verification such as `evidence_verified`, which checks
  whether a proposed quotation is supported by the source representation;
- human review and adjudication, which remain authoritative research actions;
- corpus-level validation required for floating/empty signifiers, hegemony,
  ideological formations and other theory-sensitive claims;
- substantive theoretical validity: a high self-report does not establish that
  a Laclaudian or Palonen concept has been interpreted correctly.

A low self-report is likewise not proof that a coding is false. It is an input to
human and empirical evaluation.

## Thresholds

Unless a threshold has been validated against a declared reference task, any
rule such as `confidence >= 0.7` is an **operational selection rule**. It may be
useful for prioritising review, constructing a sensitivity slice, or deciding
which provisional items to display, but it must not be described as a 70%
probability-of-correctness cutoff.

Reports should name the threshold, its operational purpose, and any sensitivity
analysis using alternative thresholds.

## Other numeric scores

The repository also contains subsystem-specific scores such as classifier
probabilities, OCR confidence, embedding similarity, fuzzy-match scores and
clustering scores. Their semantics come from the producing method and must not be
silently reinterpreted as theory-facing LLM confidence. Conversely, the
`confidence` attached to a provisional discourse coding must not be presented as
an externally calibrated classifier probability merely because both happen to
use values between 0 and 1.

## Provenance and compatibility

The field name `confidence` remains unchanged in canonical/interchange records so
existing consumers continue to work. Prompt-version bumps distinguish outputs
produced under the clarified semantics from older cached generations. The
prompt version, model identity/digest, run provenance and human-review state
should travel with any confidence value used in analysis or export.
