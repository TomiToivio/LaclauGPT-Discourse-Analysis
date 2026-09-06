"""Tests for the public LaclauGPT core. Synthetic text only — the public
repository never contains research data (paper §4: evaluation runs on
project datasets governed elsewhere)."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from laclaugpt import (AnalysisResult, Articulation, ArticulationType,
                       AffectiveInvestment, CollectiveSubject, EvidenceLink,
                       LaclauGPTAnalyzer, PopulistConfiguration, Provenance,
                       ReviewStatus, SourceDocument, analyze, evidence_span,
                       strip_reviewed, verify_evidence_links)

SYNTHETIC_TEXT = (
    "The town council debate about the new data centre was heated. "
    "Mayor Kivi said: 'The data centre will bring jobs and prosperity to "
    "our community — we cannot let the enemies of progress stop it.' "
    "Councillor Aho disagreed: 'This is not about progress, it is about "
    "our lake being drained and our electricity bills rising.'"
)

# A stub "model call" — the reference implementation takes any callable
# (system, user) -> str. This stub returns a fixed valid analysis.
_STUB_RESPONSE = {
    "summary": "A town council debate about a data centre.",
    "entities": [
        {"canonical_name": "Mayor Kivi", "entity_type": "person"},
        {"canonical_name": "Councillor Aho", "entity_type": "person"},
    ],
    "topics": [{"canonical_label": "data centre jobs"}],
    "sentiment_targets": [
        {"target_text": "data centre", "sentiment_type": "positive"},
        {"target_text": "data centre", "sentiment_type": "negative"},
    ],
    "concepts": [
        {"canonical_label": "prosperity"},
        {"canonical_label": "drained lake"},
    ],
    "articulations": [
        {"source_concept": "data centre", "target_concept": "prosperity",
         "relation_type": "equivalence",
         "evidence": "The data centre will bring jobs and prosperity to "
                     "our community",
         "confidence": 0.8, "uncertainty": "quoted speech, not author voice"},
        {"source_concept": "data centre", "target_concept": "drained lake",
         "relation_type": "antagonism",
         "evidence": "it is about our lake being drained",
         "confidence": 0.7},
    ],
    "signifier_roles": [
        {"signifier": "progress", "role": "floating_signifier_candidate",
         "rationale": "used by both sides with different meanings",
         "evidence": "enemies of progress", "confidence": 0.6},
    ],
    "collective_subjects": [
        {"label": "our community", "evidence": "prosperity to our community"},
    ],
    "antagonistic_frontiers": [
        {"us_label": "our community", "them_label": "enemies of progress",
         "rationale": "constitutive obstacle framing",
         "evidence": "we cannot let the enemies of progress stop it"},
    ],
    "affective_investments": [
        {"affect_label": "anger", "target_label": "enemies of progress",
         "evidence": "we cannot let the enemies of progress stop it",
         "confidence": 0.5},
    ],
    "populist_configuration": {
        "populist": True, "non_populist_reason": None,
        "us_label": "our community", "frontier_label": "enemies of progress",
        "us_affects": ["hope"], "frontier_affects": ["anger"],
        "evidence": "we cannot let the enemies of progress stop it"},
    "discourses": [
        {"label": "progress discourse", "description": "growth framing",
         "evidence": "bring jobs and prosperity"},
    ],
    "uncertainties": ["both quotes are attributed speech, not author voice"],
    "not_detected": ["empty signifier: no equivalential chain evidence"],
}


def _stub_model_call(system: str, user: str) -> str:
    assert "evidence" in system.lower()       # the method's core rule is in the prompt
    return json.dumps(_STUB_RESPONSE)


# ── schema validation ────────────────────────────────────────────────

def test_analysis_result_schema_validates():
    result = analyze(SYNTHETIC_TEXT, model_call=_stub_model_call, model="stub-1")
    assert isinstance(result, AnalysisResult)
    assert result.summary.startswith("A town council debate")
    assert result.entities[0].entity_type == "person"
    assert result.provenance.model == "stub-1"
    assert result.provenance.method == "llm"
    assert result.provenance.prompt_version and result.provenance.run_id


def test_unknown_relation_types_are_dropped_not_guessed():
    bad = dict(_STUB_RESPONSE)
    bad["articulations"] = [
        {"source_concept": "x", "target_concept": "y",
         "relation_type": "co_occurrence", "evidence": "x and y appear"}]
    result = analyze(SYNTHETIC_TEXT, model_call=lambda s, u: json.dumps(bad))
    assert result.articulations == []     # co-occurrence is never an articulation


def test_review_status_starts_as_proposed():
    result = analyze(SYNTHETIC_TEXT, model_call=_stub_model_call)
    assert result.articulations[0].review_status == ReviewStatus.PROPOSED


# ── evidence linkage ─────────────────────────────────────────────────

def test_every_interpretation_carries_exact_evidence():
    result = analyze(SYNTHETIC_TEXT, model_call=_stub_model_call)
    for interpretation in (result.articulations + result.antagonistic_frontiers
                           + result.collective_subjects):
        assert interpretation.evidence in SYNTHETIC_TEXT
        assert interpretation.document_id
        assert interpretation.provenance_id is not None


def test_verify_evidence_links_separates_verified_from_fabricated():
    result = analyze(SYNTHETIC_TEXT, model_call=_stub_model_call)
    fabricated = Articulation(
        document_id=result.document_id, evidence="quote that never appears",
        provenance_id="p", source_concept="a", target_concept="b",
        relation_type=ArticulationType.EQUIVALENCE)
    verified, unverified = verify_evidence_links(
        result.articulations + [fabricated], SYNTHETIC_TEXT)
    assert len(verified) == 2 and unverified == [fabricated]


def test_evidence_span_offsets():
    span = evidence_span("doc1", SYNTHETIC_TEXT, "enemies of progress")
    assert span.start_offset == SYNTHETIC_TEXT.find("enemies of progress")
    assert evidence_span("doc1", SYNTHETIC_TEXT, "not in the text") is None


# ── abstention & empty results ───────────────────────────────────────

def test_explicit_abstention_and_not_detected():
    result = analyze(SYNTHETIC_TEXT, model_call=_stub_model_call)
    assert "empty signifier: no equivalential chain evidence" in result.not_detected
    assert result.uncertainties


def test_empty_analysis_is_valid():
    empty = {**_STUB_RESPONSE, "entities": [], "articulations": [],
             "populist_configuration": None, "summary": None,
             "not_detected": ["nothing fitting the framework"]}
    result = analyze(SYNTHETIC_TEXT, model_call=lambda s, u: json.dumps(empty))
    assert result.articulations == [] and result.populist_configuration is None
    assert result.not_detected == ["nothing fitting the framework"]


def test_populism_may_be_absent_with_reason():
    absent = {**_STUB_RESPONSE, "populist_configuration": {
        "populist": False, "non_populist_reason":
            "policy disagreement without a constructed people",
        "us_label": None, "frontier_label": None,
        "us_affects": [], "frontier_affects": [], "evidence": ""}}
    result = analyze(SYNTHETIC_TEXT, model_call=lambda s, u: json.dumps(absent))
    assert result.populist_configuration.populist is False
    assert "constructed people" in result.populist_configuration.non_populist_reason


# ── multiple candidates & theoretical distinctions ───────────────────

def test_multiple_candidate_articulations_and_signifier_roles():
    result = analyze(SYNTHETIC_TEXT, model_call=_stub_model_call)
    relations = {a.relation_type for a in result.articulations}
    assert relations == {ArticulationType.EQUIVALENCE, ArticulationType.ANTAGONISM}
    roles = result.signifier_roles
    assert roles[0].role == "floating_signifier_candidate"
    assert roles[0].needs_corpus_validation is True   # one document cannot fix a role


def test_populist_configuration_is_interpretive_not_numerical():
    result = analyze(SYNTHETIC_TEXT, model_call=_stub_model_call)
    pop = result.populist_configuration
    assert isinstance(pop, PopulistConfiguration)
    assert pop.us_affects == ["hope"] and pop.frontier_affects == ["anger"]
    # affects are not polarity-locked: anger on the frontier side carries
    # no 'negative=True' field anywhere in the model
    assert not any("polarity" in field for field in pop.model_fields)


def test_model_proposal_is_not_accepted_interpretation():
    reviewed = analyze(SYNTHETIC_TEXT, model_call=_stub_model_call)
    proposed = Articulation(**reviewed.articulations[0].__dict__)
    assert proposed.review_status != ReviewStatus.ACCEPTED
    stripped = strip_reviewed(reviewed.articulations)
    assert stripped == []               # nothing is reviewed yet
    accepted = proposed.model_copy(update={"review_status": ReviewStatus.ACCEPTED})
    assert strip_reviewed([accepted]) == [accepted]


def test_document_provenance_is_required_for_theoretical_codes():
    with pytest.raises(ValidationError):
        EvidenceLink(document_id="d", evidence="q")  # provenance_id required
    with pytest.raises(ValidationError):
        Provenance()  # method is required