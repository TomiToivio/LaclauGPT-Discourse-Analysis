from __future__ import annotations

from pipeline import corpus_synthesis
from laclaugpt_interchange import DocumentAnnotation, MemoryRef, SignifierRole


def _role(
    *,
    obj_id: str,
    label: str,
    role: str,
    evidence: str,
    confidence: float,
    needs_corpus_validation: bool,
    verified: bool = True,
) -> SignifierRole:
    return SignifierRole(
        signifier=MemoryRef(
            obj_id=obj_id,
            label=label,
            kind="signifier",
            raw=label,
        ),
        role=role,
        rationale="synthetic candidate for corpus-synthesis regression test",
        evidence=evidence,
        evidence_source="text",
        confidence=confidence,
        needs_corpus_validation=needs_corpus_validation,
        evidence_verified=verified,
    )


def test_candidate_families_preserve_comparable_evidence_fields() -> None:
    annotation = DocumentAnnotation(
        document_id="doc-1",
        signifier_roles=[
            _role(
                obj_id="S001",
                label="AI",
                role="floating_candidate",
                evidence="AI means freedom to us",
                confidence=0.61,
                needs_corpus_validation=True,
            ),
            _role(
                obj_id="S002",
                label="future",
                role="empty_candidate",
                evidence="the future stands for all our demands",
                confidence=0.72,
                needs_corpus_validation=True,
            ),
            _role(
                obj_id="S003",
                label="innovation",
                role="nodal_candidate",
                evidence="innovation organises the programme",
                confidence=0.83,
                needs_corpus_validation=False,
            ),
        ],
    )

    synthesis = corpus_synthesis([annotation])

    expected_keys = {
        "obj_id",
        "label",
        "document_id",
        "evidence",
        "evidence_source",
        "confidence",
        "needs_corpus_validation",
    }
    for family in (
        "floating_candidates",
        "empty_candidates",
        "nodal_candidates",
    ):
        assert len(synthesis[family]) == 1
        assert set(synthesis[family][0]) == expected_keys
        assert synthesis[family][0]["document_id"] == "doc-1"
        assert synthesis[family][0]["evidence_source"] == "text"

    assert synthesis["floating_candidates"][0]["confidence"] == 0.61
    assert synthesis["empty_candidates"][0]["confidence"] == 0.72
    assert synthesis["nodal_candidates"][0]["confidence"] == 0.83


def test_unverified_candidate_evidence_is_excluded_from_synthesis() -> None:
    annotation = DocumentAnnotation(
        document_id="doc-2",
        signifier_roles=[
            _role(
                obj_id="S004",
                label="prosperity",
                role="empty_candidate",
                evidence="fabricated quotation",
                confidence=0.99,
                needs_corpus_validation=True,
                verified=False,
            ),
            _role(
                obj_id="S005",
                label="technology",
                role="nodal_candidate",
                evidence="technology organises this source",
                confidence=0.77,
                needs_corpus_validation=False,
                verified=True,
            ),
        ],
    )

    synthesis = corpus_synthesis([annotation])

    assert synthesis["empty_candidates"] == []
    assert [row["obj_id"] for row in synthesis["nodal_candidates"]] == ["S005"]
    assert "S004" not in synthesis["signifier_frequency"]
    assert synthesis["signifier_frequency"]["S005"] == 1


def test_synthesis_artifact_states_frequency_is_not_hegemony() -> None:
    synthesis = corpus_synthesis([])
    note = synthesis["note"].lower()

    assert "frequency" in note
    assert "hegemony" in note
    assert "must not be interpreted as hegemony" in note
    assert "inv_hegemony_corpus" in note
