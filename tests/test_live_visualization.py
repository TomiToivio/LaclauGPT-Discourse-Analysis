"""Tests for data-agnostic live visualization helpers."""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from laclaugpt.visualization.live import (
    actor_summary,
    apply_time_window,
    explode_timeline,
    first_seen,
    relation_rows,
    signifier_summary,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "document_id": "d1",
                "source_timestamp": pd.Timestamp("2026-09-10T12:00:00Z"),
                "source_author": "Actor A",
                "source_platform": "rss",
                "formations": ["formation-a"],
                "signifiers": ["AGI", "progress"],
            },
            {
                "document_id": "d2",
                "source_timestamp": pd.Timestamp("2026-09-11T11:30:00Z"),
                "source_author": "Actor B",
                "source_platform": "mastodon",
                "formations": ["formation-b"],
                "signifiers": ["AGI", "risk"],
            },
            {
                "document_id": "d3",
                "source_timestamp": pd.Timestamp("2026-09-11T11:45:00Z"),
                "source_author": "Actor A",
                "source_platform": "rss",
                "formations": ["formation-a", "formation-b"],
                "signifiers": ["safety"],
            },
        ]
    )


def test_time_window_is_rolling_and_data_agnostic() -> None:
    now = pd.Timestamp("2026-09-11T12:00:00Z")
    result = apply_time_window(_frame(), "Last hour", now=now)
    assert result["document_id"].tolist() == ["d2", "d3"]


def test_explode_timeline_keeps_emergent_labels() -> None:
    timeline = explode_timeline(_frame(), "formations", value_name="formation")
    assert set(timeline["formation"]) == {"formation-a", "formation-b"}
    assert timeline["documents"].sum() == 4


def test_actor_summary_does_not_require_fixed_ideology_taxonomy() -> None:
    summary = actor_summary(_frame())
    row = summary.loc[summary["actor"] == "Actor A"].iloc[0]
    assert row["documents"] == 2
    assert "formation-a" in row["candidate_formations"]
    assert "AGI" in row["signifiers"]


def test_signifier_summary_tracks_associations_without_claiming_theory() -> None:
    summary = signifier_summary(_frame())
    agi = summary.loc[summary["signifier"] == "AGI"].iloc[0]
    assert agi["documents"] == 2
    assert agi["actors"] == 2
    assert "formation-a" in agi["candidate_formations"]
    assert "formation-b" in agi["candidate_formations"]


def test_relation_rows_preserve_evidence_and_claim_context() -> None:
    articulation = SimpleNamespace(
        signifier=SimpleNamespace(label="innovation"),
        related_to=[SimpleNamespace(label="freedom")],
        relation="equivalence",
        claim_status="asserted",
        confidence=0.7,
        evidence_verified=True,
        evidence="Innovation is articulated with freedom in this source.",
    )
    annotation = SimpleNamespace(
        document_id="d1",
        source_timestamp="2026-09-11T10:00:00Z",
        source_author="Actor A",
        source_platform="rss",
        source_url="https://example.invalid/d1",
        articulations=[articulation],
    )
    result = relation_rows([annotation], relations=["equivalence"])
    assert result.iloc[0]["source"] == "innovation"
    assert result.iloc[0]["target"] == "freedom"
    assert result.iloc[0]["claim_status"] == "asserted"
    assert bool(result.iloc[0]["evidence_verified"]) is True
    assert "Innovation" in result.iloc[0]["evidence"]


def test_first_seen_means_first_observed_in_loaded_corpus() -> None:
    result = first_seen(_frame(), "signifiers", "signifier")
    risk = result.loc[result["signifier"] == "risk"].iloc[0]
    assert risk["first_seen"] == pd.Timestamp("2026-09-11T11:30:00Z")
    assert risk["documents"] == 1
