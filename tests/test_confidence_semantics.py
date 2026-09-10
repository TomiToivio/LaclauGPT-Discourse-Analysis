"""Regression coverage for issue #90 confidence/uncertainty semantics."""
from __future__ import annotations

from pathlib import Path
from typing import get_args

from prompts import discourse as discourse_prompt
from prompts import populism as populism_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]


def _list_item_model(field):
    """Return the model nested inside list[Model] for a Pydantic field."""
    annotation = field.annotation
    args = get_args(annotation)
    return args[0] if args else annotation


def _description(model, field_name: str) -> str:
    return str(model.model_fields[field_name].description or "").lower()


def test_discourse_prompt_uses_uncalibrated_model_reported_confidence() -> None:
    prompt = discourse_prompt.build_system_prompt("topic", "metadata")
    lowered = prompt.lower()
    assert discourse_prompt.PROMPT_VERSION == "discourse-v1.4"
    assert "calibrated confidence" not in lowered
    assert "model-reported confidence" in lowered
    assert "uncalibrated self-report" in lowered
    assert "not a probability" in lowered
    assert "mechanical quotation verification" in lowered
    assert "human review" in lowered
    assert "substantive theoretical validity" in lowered
    assert "operational selection rule" in lowered


def test_discourse_confidence_field_remains_compatible_but_is_described() -> None:
    analysis = discourse_prompt.pydantic_models()
    for family in ("signifiers", "articulations", "imaginaries", "formation_candidates"):
        model = _list_item_model(analysis.model_fields[family])
        assert "confidence" in model.model_fields
        field = model.model_fields["confidence"]
        description = _description(model, "confidence")
        assert "uncalibrated" in description
        assert "not a probability" in description
        # Existing interchange shape/range is preserved.
        metadata = field.metadata
        assert any(getattr(item, "ge", None) == 0.0 for item in metadata)
        assert any(getattr(item, "le", None) == 1.0 for item in metadata)


def test_populism_prompt_and_field_use_same_semantics() -> None:
    prompt = populism_prompt.build_system_prompt("topic", "metadata")
    lowered = prompt.lower()
    assert populism_prompt.PROMPT_VERSION == "populism-v3.4"
    assert "model-reported confidence" in lowered
    assert "uncalibrated self-report" in lowered
    assert "not a probability" in lowered
    assert "operational selection rule" in lowered

    element, _ = populism_prompt.pydantic_models()
    assert "confidence" in element.model_fields
    description = _description(element, "confidence")
    assert "uncalibrated" in description
    assert "not a probability" in description


def test_dashboard_labels_confidence_as_uncalibrated_model_report() -> None:
    source = (REPO_ROOT / "laclaugpt" / "visualization" / "app.py").read_text(
        encoding="utf-8"
    ).lower()
    assert 'model_confidence_label = "model-reported confidence (uncalibrated)"' in source
    assert "mean model-reported confidence (uncalibrated)" in source
    assert "not probabilities of correctness" in source
    assert "quotation verification" in source


def test_confidence_documentation_defines_thresholds_as_operational() -> None:
    text = (REPO_ROOT / "docs" / "CONFIDENCE_AND_UNCERTAINTY.md").read_text(
        encoding="utf-8"
    ).lower()
    assert "model-reported, uncalibrated self-report" in text
    assert "not automatically a probability" in text
    assert "operational selection rule" in text
    assert "evidence_verified" in text
    assert "human review" in text
    assert "declared reference task" in text
