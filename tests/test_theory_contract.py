from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prompts.discourse import pydantic_models as discourse_models
from prompts.populism import pydantic_models as populism_models
from laclaugpt_interchange import DocumentAnnotation


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_INVARIANTS = {
    "INV_EVIDENCE",
    "INV_ABSTAIN",
    "INV_RELATIONAL",
    "INV_FLOAT_CORPUS",
    "INV_EMPTY_CHAIN",
    "INV_HEGEMONY_CORPUS",
    "INV_ANTAGONISM",
    "INV_AFFECT",
    "INV_POPULISM",
    "INV_DYNAMIC_LABELS",
    "INV_HUMAN_REVIEW",
    "INV_CONTEXT",
}


def test_theory_contract_declares_required_invariants() -> None:
    theory = (ROOT / "THEORY.md").read_text(encoding="utf-8")
    for invariant in REQUIRED_INVARIANTS:
        assert invariant in theory
    assert "normative_for_agents: true" in theory
    assert "human_review_required: true" in theory


def test_agent_contexts_require_theory_before_theory_facing_work() -> None:
    for filename in ("AGENTS.md", "HERMES.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        assert "THEORY.md" in text
        assert "before" in text.lower()
        assert "theory" in text.lower()


def test_formula_of_populism_rejects_missing_us_or_frontier() -> None:
    PopulismElement, FormulaOfPopulism = populism_models()
    us = PopulismElement(
        populism_element="people",
        evidence_quote="we the people demand change",
        confidence=0.8,
    )
    frontier = PopulismElement(
        populism_element="oligarchy",
        evidence_quote="the oligarchy blocks that change",
        confidence=0.8,
    )

    with pytest.raises(ValidationError):
        FormulaOfPopulism(
            populist=True,
            populism_analysis="invalid: no frontier",
            populism_us=[us],
            populism_frontier=[],
        )

    with pytest.raises(ValidationError):
        FormulaOfPopulism(
            populist=True,
            populism_analysis="invalid: no us",
            populism_us=[],
            populism_frontier=[frontier],
        )

    valid = FormulaOfPopulism(
        populist=True,
        populism_analysis="synthetic evidenced formula",
        populism_us=[us],
        populism_frontier=[frontier],
    )
    assert valid.populist is True


def test_non_populist_result_requires_abstention_shape() -> None:
    _, FormulaOfPopulism = populism_models()
    result = FormulaOfPopulism(
        populist=False,
        non_populist_reason="No constitutive collective Us is evidenced.",
        populism_analysis="The source contains criticism but not the full formula.",
        populism_us=[],
        populism_frontier=[],
    )
    assert result.populism_us == []
    assert result.populism_frontier == []


def test_floating_and_empty_candidates_are_forced_to_corpus_validation() -> None:
    DiscourseAnalysis = discourse_models()
    fields = DiscourseAnalysis.__annotations__
    signifier_model = fields["signifiers"].__args__[0]

    for role in ("floating_candidate", "empty_candidate"):
        candidate = signifier_model(
            term="AI",
            role=role,
            rationale="synthetic candidate",
            evidence_quote="AI will organise the future",
            confidence=0.7,
            needs_corpus_validation=False,
        )
        assert candidate.needs_corpus_validation is True


def test_theory_facing_prompt_requires_evidence_and_context_status() -> None:
    DiscourseAnalysis = discourse_models()
    fields = DiscourseAnalysis.__annotations__
    articulation_model = fields["articulations"].__args__[0]

    with pytest.raises(ValidationError):
        articulation_model(
            source="AI",
            target="prosperity",
            relation="articulation",
            rationale="unsupported synthetic relation",
            evidence_quote="",
            confidence=0.8,
        )

    quoted = articulation_model(
        source="AI",
        target="prosperity",
        relation="articulation",
        rationale="speaker is quoting an opponent",
        evidence_quote="They say AI guarantees prosperity",
        confidence=0.8,
        claim_status="quoted",
    )
    assert quoted.claim_status == "quoted"


def test_interchange_defaults_to_human_review() -> None:
    annotation = DocumentAnnotation(document_id="synthetic-doc")
    assert annotation.requires_human_review is True
    assert annotation.review_status == "PROVISIONAL"


def test_readme_states_human_verified_preliminary_analysis() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Human-in-the-loop research only" in readme
    assert "preliminary" in readme.lower()
    assert "verified by a human researcher" in readme
