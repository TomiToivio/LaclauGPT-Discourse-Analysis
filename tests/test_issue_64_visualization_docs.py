"""Regression tests for issue #64 display-layer and documentation alignment."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_surfaces_claim_status_and_corpus_validation() -> None:
    source = (ROOT / "laclaugpt" / "visualization" / "app.py").read_text(encoding="utf-8")
    assert '"claim_status": item.claim_status' in source
    assert '"needs_corpus_validation": item.needs_corpus_validation' in source
    assert "Counter-evidence" in source
    assert "non_populist_reason" in source


def test_dashboard_uses_candidate_language_and_frequency_warning() -> None:
    source = (ROOT / "laclaugpt" / "visualization" / "app.py").read_text(encoding="utf-8")
    assert "Sociotechnical-imaginary candidates" in source
    assert "Frequency is not theoretical importance" in source
    assert "does not establish theoretical importance" in source


def test_interoperability_spec_preserves_context_and_abstention() -> None:
    source = (ROOT / "docs" / "INTEROPERABILITY_SPEC.md").read_text(encoding="utf-8")
    assert '"claim_status": "asserted"' in source
    assert '"populist": true' in source
    assert '"populist": false' in source
    assert '"detected": true' not in source
    assert '"label": "anger",\n      "side": "us"' in source
    assert '"label": "admiration",\n      "side": "frontier"' in source
    assert "Affective investment MUST NOT be mechanically mapped" in source


def test_layered_configuration_points_to_canonical_chain() -> None:
    source = (ROOT / "docs" / "LAYERED_CONFIGURATION_AND_IMAGINARIES.md").read_text(
        encoding="utf-8"
    )
    assert "config/arenas/<arena>.yaml" in source
    assert "CANONICAL_CONFIGURATION.md" in source
    assert "older pre-arena four-input description has been retired" in source
