from __future__ import annotations

import tempfile
from pathlib import Path

from laclaugpt.visualization import (
    ReviewStore,
    articulation_edges,
    dashboard_runtime_violation,
    filter_frame,
    flatten_annotations,
    top_values,
)
from laclaugpt_interchange import (
    Affect,
    Articulation,
    DocumentAnnotation,
    HegemonicEvidenceSpan,
    MemoryRef,
    SentimentObservation,
    SociotechnicalImaginary,
)


def _ref(obj_id: str, label: str, kind: str = "signifier") -> MemoryRef:
    return MemoryRef(obj_id=obj_id, label=label, kind=kind, raw=label)


def _annotation(document_id: str, *, profile: str, topic: str) -> DocumentAnnotation:
    ai = _ref("S001", "AI")
    abundance = _ref("S002", "abundance")
    public = _ref("E001", "Public", "entity")
    policy = _ref("T001", topic, "topic")
    sentiment_target = _ref("C001", "AI policy", "target")
    return DocumentAnnotation(
        document_id=document_id,
        source_platform="web",
        source_country="FI",
        language="en",
        source_author="Researcher",
        source_timestamp="2026-09-07T12:00:00Z",
        source_url=f"https://example.test/{document_id}",
        source_modalities=["text"],
        run_id=f"run-{document_id}",
        summary=f"{topic} summary with AI and abundance",
        entities=[public],
        topics=[policy],
        signifiers=[ai, abundance],
        nodal_points=[ai],
        articulations=[Articulation(
            signifier=ai,
            related_to=[abundance],
            relation="equivalence",
            evidence="AI means abundance",
            evidence_verified=True,
            confidence=0.8,
        )],
        imaginaries=[SociotechnicalImaginary(label="abundant future")],
        affects=[Affect(target=ai, affect="hope", side="us", confidence=0.7)],
        us=[ai],
        frontier=[abundance],
        populist=False,
        relevance="relevant",
        relevance_reason="In-scope public AI discourse",
        discourse_applicable=True,
        discourse_applicability_reason="Contains an articulated signifying relation",
        hegemonic_evidence=[HegemonicEvidenceSpan(
            quote="AI means abundance",
            evidence_source="text",
            evidence_verified=True,
        )],
        sentiment_observations=[SentimentObservation(
            target=sentiment_target,
            polarity="positive",
            evidence_source="summary",
            uncertainty=0.2,
            model="test-model",
            prompt_version="sentiment-test",
        )],
        collection_provenance={
            "project": "ai26",
            "analysis_profile": profile,
            "arena_id": profile.split(":")[-1],
        },
    )


def test_flatten_filter_and_top_values_are_profile_aware() -> None:
    annotations = [
        _annotation("a", profile="ai26:elites", topic="AI policy"),
        _annotation("b", profile="ai26:grassroots", topic="jobs"),
    ]
    frame = flatten_annotations(annotations)
    filtered = filter_frame(
        frame,
        profiles=["ai26:elites"],
        search="abundance",
        entities=["Public"],
    )
    assert filtered["document_id"].tolist() == ["a"]
    assert top_values(filtered, "topics").to_dict("records") == [
        {"label": "AI policy", "count": 1}
    ]


def test_dashboard_flattens_current_schema_fields() -> None:
    frame = flatten_annotations([
        _annotation("a", profile="ai26:elites", topic="AI policy")
    ])
    row = frame.iloc[0]
    assert row["schema_version"] == "1.7"
    assert row["relevance_state"] == "relevant"
    assert row["discourse_applicability"] == "applicable"
    assert row["source_modalities"] == ["text"]
    assert row["sentiment_polarities"] == ["positive"]
    assert row["sentiment_targets"] == ["AI policy"]
    assert row["sentiments"][0]["target_id"] == "C001"
    assert row["evidence_count"] == 1
    assert "AI means abundance" in row["searchable_text"]


def test_dashboard_filters_current_schema_states() -> None:
    relevant = _annotation("a", profile="ai26:elites", topic="AI policy")
    irrelevant = _annotation("b", profile="ai26:elites", topic="jobs")
    irrelevant.relevance = "irrelevant"
    irrelevant.discourse_applicable = False
    irrelevant.discourse_applicability_reason = "No discourse-level material"
    irrelevant.sentiment_observations = []

    frame = flatten_annotations([relevant, irrelevant])
    filtered = filter_frame(
        frame,
        relevance_states=["relevant"],
        discourse_applicabilities=["applicable"],
        sentiment_polarities=["positive"],
        sentiment_targets=["AI policy"],
    )
    assert filtered["document_id"].tolist() == ["a"]


def test_dashboard_accepts_arena_compatibility_key() -> None:
    annotation = _annotation("a", profile="ai26:elites", topic="AI policy")
    annotation.collection_provenance = {
        "project": "ai26",
        "analysis_profile": "ai26:elites",
        "arena": "elites",
    }
    frame = flatten_annotations([annotation])
    assert frame.iloc[0]["arena_id"] == "elites"


def test_articulation_edges_are_aggregated() -> None:
    annotations = [
        _annotation("a", profile="ai26:elites", topic="AI policy"),
        _annotation("b", profile="ai26:elites", topic="AI policy"),
    ]
    edges = articulation_edges(annotations)
    row = edges.iloc[0]
    assert row["source"] == "AI"
    assert row["target"] == "abundance"
    assert row["relation"] == "equivalence"
    assert row["count"] == 2
    assert row["verified_count"] == 2


def test_dashboard_runtime_rejects_roihu_and_slurm() -> None:
    assert dashboard_runtime_violation({"SLURM_JOB_ID": "123"}, "worker") is not None
    assert dashboard_runtime_violation({"SLURM_CLUSTER_NAME": "roihu"}, "worker") is not None
    assert dashboard_runtime_violation({}, "roihu-login") is not None
    assert dashboard_runtime_violation({}, "pouta-vm") is None
    assert dashboard_runtime_violation({}, "laptop") is None


def test_review_store_is_separate_and_persistent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "reviews.sqlite3"
        store = ReviewStore(path)
        try:
            saved = store.save(
                "doc-1",
                review_status="accepted",
                note="Evidence supports the coding.",
                tags=["checked", "paper"],
            )
            assert saved["review_status"] == "accepted"
            assert saved["tags"] == ["checked", "paper"]
        finally:
            store.close()

        reopened = ReviewStore(path)
        try:
            loaded = reopened.get("doc-1")
            assert loaded["note"] == "Evidence supports the coding."
            assert loaded["review_status"] == "accepted"
        finally:
            reopened.close()
