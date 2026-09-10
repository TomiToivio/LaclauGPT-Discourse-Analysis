# -*- coding: utf-8 -*-
"""Evidence-first Formula of Populism coding.

This stage is deliberately diagnostic: it can return ``populist=false``.
Populism is not a synonym for political conflict, negativity, or ideology.
"""
from __future__ import annotations

PROMPT_VERSION = "populism-v3.4"

SYSTEM_PROMPT_TEMPLATE = """You assist a University of Helsinki researcher
with PROVISIONAL coding using Laclau's theory and Emilia Palonen's Formula of
Populism.

{topic_background}

{source_metadata}

Retrieved codebook candidates (use only when the source supports them):
{context_memory}

Populism = Us^(affects) + Frontier^(affects)

Code a populist articulation only when the material constructs both (1) a
collective political subject/Us through a chain of equivalence and (2) a
constitutive antagonistic frontier.  Policy disagreement, criticism, sentiment,
or a list of allies and opponents is not sufficient.  If either side is absent,
return ``populist=false`` and name the absent side in ``non_populist_reason``.
Partial evidence is not discarded: keep the evidenced side's elements in its
list as document-level candidates (only ``populist=true`` requires both
sides; never return both sides fully evidenced with ``populist=false``).

For every Us/Frontier element provide a short verbatim source quote, an affect
only if affect is evidenced, and a model-reported confidence value from 0 to 1.
Treat confidence as an uncalibrated self-report of model uncertainty unless it
has been separately evaluated against a declared reference task; it is not a
probability that the coding is correct. Do not force Us affects to be positive
or Frontier affects to be negative: anger can invest an Us and admiration can
qualify an opponent. Distinguish the author's articulation from speech that is
quoted, reported, parodied, or rejected by recording it in ``claim_status``
(asserted|quoted|reported|rejected|parodied|uncertain), which defaults to
``uncertain`` — set ``asserted`` explicitly only when the author themself makes
the claim (issue #63: omission never asserts authorship); a quoted or rejected
politician's articulation must not become the author's position.

Use ``nodal_candidate`` only for a privileged signifier that visibly organises
the chain.  Use ``empty_candidate`` only when a partial demand appears to stand
for a heterogeneous totality or absent fullness; polysemy is insufficient.
Every ``empty_candidate=true`` is a document-level candidate and MUST carry
``needs_corpus_validation=true``. It is not a final empty-signifier finding.

Model-reported confidence is separate from mechanical quotation verification,
human review, and substantive theoretical validity. Any downstream threshold on
this confidence value is an operational selection rule, not an empirical
probability-of-correctness cutoff.

Return a single JSON object matching the schema.  The prose analysis must state
counter-evidence and uncertainty and must not exceed what the source supports.
"""


def build_system_prompt(topic_background: str, source_metadata: str,
                        glossary_block: str = "") -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        topic_background=topic_background,
        source_metadata=source_metadata,
        context_memory=glossary_block or "(none)",
    )


def pydantic_models():
    from typing import Literal

    from pydantic import BaseModel, Field, model_validator, field_validator

    def _null_to_empty(v):
        return "" if v is None else v

    def confidence_field():
        return Field(
            ge=0.0,
            le=1.0,
            description=(
                "Model-reported uncalibrated confidence/self-reported uncertainty. "
                "Not a probability of correctness unless separately calibrated "
                "against a declared reference task."
            ),
        )

    class PopulismElement(BaseModel):
        populism_element: str
        populism_affect: str = ""
        evidence_quote: str = Field(min_length=1)
        confidence: float = confidence_field()
        claim_status: Literal["asserted", "quoted", "reported", "rejected",
                              "parodied", "uncertain"] = "uncertain"
        nodal_candidate: bool = False
        empty_candidate: bool = False
        needs_corpus_validation: bool = False

        _affect_null = field_validator("populism_affect", mode="before")(
            staticmethod(_null_to_empty))

        @model_validator(mode="after")
        def empty_candidates_require_corpus_validation(self):
            if self.empty_candidate:
                self.needs_corpus_validation = True
            return self

    class FormulaOfPopulism(BaseModel):
        populist: bool
        non_populist_reason: str = ""
        populism_analysis: str
        populism_us: list[PopulismElement] = []
        populism_frontier: list[PopulismElement] = []
        counter_evidence: list[str] = []
        uncertainties: list[str] = []

        _reason_null = field_validator("non_populist_reason", mode="before")(
            staticmethod(_null_to_empty))

        @model_validator(mode="after")
        def formula_requires_both_sides_or_abstention(self):
            if self.populist and not (self.populism_us and self.populism_frontier):
                raise ValueError("populist=true requires evidenced Us and Frontier elements")
            if not self.populist and self.populism_us and self.populism_frontier:
                raise ValueError(
                    "populist=false cannot carry both evidenced Us and Frontier "
                    "lists; either set populist=true or drop the weaker side")
            if not self.populist and not self.non_populist_reason.strip():
                raise ValueError("populist=false requires a non_populist_reason")
            return self

    return PopulismElement, FormulaOfPopulism