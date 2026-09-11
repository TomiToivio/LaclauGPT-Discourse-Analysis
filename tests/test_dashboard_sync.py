"""Regression checks for the current Streamlit dashboard entry point."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "laclaugpt" / "visualization" / "dashboard.py"
LAUNCHER = ROOT / "laclaugpt" / "visualization" / "launcher.py"


def test_launcher_uses_current_dashboard_entry_point() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")
    assert 'with_name("dashboard.py")' in source


def test_dashboard_uses_project_switches_and_canonical_graphs() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "load_project(project_id)" in source
    assert "graph_projection_options" in source
    assert "graph_projection_data" in source
    assert 'modules.get("sentiment", False)' in source
    assert 'modules.get("temporal", False)' in source


def test_dashboard_surfaces_current_interchange_states() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert 'derived["relevance_states"]' in source
    assert 'derived["discourse_applicabilities"]' in source
    assert 'derived["sentiment_polarities"]' in source
    assert 'derived["sentiment_targets"]' in source
    assert "annotation.sentiment_observations" in source
    assert "annotation.relevance_reason" in source
    assert "annotation.discourse_applicability_reason" in source


def test_blind_mode_does_not_expose_model_aggregate_vocabularies() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "Model-derived search/filter vocabularies are hidden" in source
    assert "suppresses aggregate model-derived" in source
    assert "if blind_initial:" in source


def test_dashboard_preserves_theory_separations() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "Affective investments (not sentiment polarity)" in source
    assert "is not Laclaudian affective investment" in source
    assert "Sociotechnical-imaginary candidates" in source
    assert "does not establish theoretical importance" in source
    assert '"claim_status": item.claim_status' in source
    assert '"needs_corpus_validation": (' in source


def test_review_sidecar_name_preserves_input_suffix() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert 'Path(f"{data_path}.reviews.sqlite3")' in source


def test_dashboard_uses_current_streamlit_width_api() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert "use_container_width" not in source
    assert 'width="stretch"' in source
