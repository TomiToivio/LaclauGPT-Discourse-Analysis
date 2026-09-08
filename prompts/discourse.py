# -*- coding: utf-8 -*-
"""Evidence-first operationalisation of Laclaudian discourse analysis.

The model produces provisional document-level coding. Corpus-level claims
(especially floating and empty signifiers, imaginaries and hegemonic influence)
are marked as candidates for comparison and human validation.
"""
from __future__ import annotations

PROMPT_VERSION = "discourse-v1.2"

SYSTEM_PROMPT_TEMPLATE = """You assist a human political scientist with a
provisional Laclaudian discourse analysis. Analyse only the supplied source
material. Every substantive coding must include a short verbatim evidence
quote and calibrated confidence. An empty list is a valid result.

{topic_background}

{source_metadata}

Sensitising codebook hints (never ground truth):
{analytic_hints}

Retrieved codebook candidates (stable IDs are suggestions, not evidence):
{context_memory}

Operational distinctions:
- articulation: a relation that modifies the identity/meaning of its elements;
- equivalence: elements made substitutable or jointly constitutive in a chain;
  semantic similarity, co-occurrence or shared vocabulary is not equivalence;
- difference: elements differentiated without necessarily becoming enemies;
- antagonism/frontier: a limit or opposing outside constitutive of an identity;
  criticism, negative sentiment or a mentioned opponent is not by itself
  antagonism; the outside must be constitutive of an identity, and a list of
  disliked entities is not a frontier;
- nodal-point candidate: a privileged signifier organising nearby relations;
- floating-signifier candidate: a term whose meaning appears disputed. A
  document alone cannot establish floating status; mark corpus validation;
- empty-signifier candidate: a term that appears to represent a heterogeneous
  chain or absent social fullness. Polysemy alone is insufficient;
- sociotechnical-imaginary candidate: a publicly performed vision linking a
  desirable or feared social order to science and technology. Code its
  normative future, diagnosis of the present, role of technology, and human
  agency, but treat document-level output as a candidate requiring corpus and
  human validation;
- ideological formation: an inferred pattern, not a label assigned merely from
  speaker identity or keyword presence;
- hegemony cannot be inferred from frequency in a single document. Record only
  evidence relevant to later cross-arena/institutional analysis.

Do not assume the text is populist, ideological, about AI, or a member of a
seeded formation. Distinguish author claims from quoted/criticised claims.
Return one JSON object matching the schema and no prose outside it.
"""

USER_PROMPT_TEMPLATE = """Analyse this document-level source and summary.

SOURCE MATERIAL:
{source_text}

METADATA:
{metadata}

PRELIMINARY SUMMARY (may contain model error; source material prevails):
{summary}
"""


def build_system_prompt(topic_background: str, source_metadata: str,
                        analytic_hints: str = "", glossary_block: str = "") -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        topic_background=topic_background,
        source_metadata=source_metadata,
        analytic_hints=analytic_hints or "(none)",
        context_memory=glossary_block or "(none)",
    )


def build_user_prompt(source_text: str, metadata: str, summary: str) -> str:
    return USER_PROMPT_TEMPLATE.format(
        source_text=source_text or "(no source text)",
        metadata=metadata or "{}",
        summary=summary or "(no preliminary summary)",
    )


def pydantic_models():
    from typing import Literal
    from pydantic import BaseModel, Field, model_validator

    class SignifierCoding(BaseModel):
        term: str
        role: Literal[
            "element", "moment", "nodal_candidate", "floating_candidate",
            "empty_candidate", "frontier_element",
        ]
        rationale: str
        evidence_quote: str = Field(min_length=1)
        confidence: float = Field(ge=0.0, le=1.0)
        needs_corpus_validation: bool = False

        @model_validator(mode="after")
        def corpus_level_roles_require_validation(self):
            if self.role in {"floating_candidate", "empty_candidate"}:
                self.needs_corpus_validation = True
            return self

    class ArticulationCoding(BaseModel):
        source: str
        target: str
        relation: Literal["articulation", "equivalence", "difference", "antagonism"]
        rationale: str
        evidence_quote: str = Field(min_length=1)
        confidence: float = Field(ge=0.0, le=1.0)
        claim_status: Literal[
            "asserted", "quoted", "reported", "rejected", "parodied", "uncertain"
        ] = "uncertain"

    class ImaginaryCoding(BaseModel):
        label: str
        normative_future: str
        present_diagnosis: str
        technology_role: str
        human_agency: str
        evidence_quote: str = Field(min_length=1)
        confidence: float = Field(ge=0.0, le=1.0)
        claim_status: Literal[
            "asserted", "quoted", "reported", "rejected", "parodied", "uncertain"
        ] = "asserted"
        needs_corpus_validation: bool = True

        @model_validator(mode="after")
        def imaginary_requires_corpus_validation(self):
            self.needs_corpus_validation = True
            return self

    class FormationCandidate(BaseModel):
        label: str
        supporting_features: list[str] = Field(min_length=1)
        counter_evidence: list[str] = []
        evidence_quote: str = Field(min_length=1)
        confidence: float = Field(ge=0.0, le=1.0)

    class DiscourseAnalysis(BaseModel):
        applicable: bool
        applicability_reason: str
        signifiers: list[SignifierCoding] = []
        articulations: list[ArticulationCoding] = []
        imaginaries: list[ImaginaryCoding] = []
        formation_candidates: list[FormationCandidate] = []
        hegemonic_evidence: list[str] = []
        uncertainties: list[str] = []

    return DiscourseAnalysis
