"""Regression coverage for issue #90 confidence/uncertainty semantics."""
from __future__ import annotations

import ast
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


def _normalized(text: str) -> str:
    """Compare semantic wording without depending on Markdown or line wrapping."""
    return " ".join(text.lower().replace("**", "").split())


def _python_string_constants(path: Path) -> str:
    """Read runtime string literals without source-level adjacent-literal seams."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    strings = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    return _normalized(" ".join(strings))


def test_discourse_prompt_uses_uncalibrated_model_reported_confidence() -> None:
    prompt = _normalized(discourse_prompt.build_system_prompt("topic", "metadata"))
    assert discourse_prompt.PROMPT_VERSION == "discourse-v1.4"
    assert "calibrated confidence" not in prompt
    assert "model-reported confidence" in prompt
    assert "uncalibrated self-report" in prompt
    assert "not a probability" in prompt
    assert "quotation verification" in prompt
    assert "human review" in prompt
    assert "substantive validity" in prompt
    assert "operational selection rule" in prompt


def test_discourse_confidence_field_remains_compatible_but_is_described() -> None:
    analysis = discourse_prompt.pydantic_models()
    for family in ("signifiers", "articulations", "imaginaries", "formation_candidates"):
        model = _list_item_model(analysis.model_fields[family])
        assert "confidence" in model.model_fields
        field = model.model_fields["confidence"]
        description = _description(model, "confidence")
        assert "uncalibrated" in description
        assert "not a probability" in description
        # Existing output shape/range is preserved.
        metadata = field.metadata
        assert any(getattr(item, "ge", None) == 0.0 for item in metadata)
        assert any(getattr(item, "le", None) == 1.0 for item in metadata)


def test_populism_prompt_and_field_use_same_semantics() -> None:
    prompt = _normalized(populism_prompt.build_system_prompt("topic", "metadata"))
    assert populism_prompt.PROMPT_VERSION == "populism-v3.4"
    assert "model-reported confidence" in prompt
    assert "uncalibrated self-report" in prompt
    assert "not a probability" in prompt
    assert "quotation verification" in prompt
    assert "human review" in prompt
    assert "substantive theoretical validity" in prompt
    assert "operational selection rule" in prompt

    element, _ = populism_prompt.pydantic_models()
    assert "confidence" in element.model_fields
    description = _description(element, "confidence")
    assert "uncalibrated" in description
    assert "not a probability" in description


def test_dashboard_labels_confidence_as_uncalibrated_model_report() -> None:
    path = REPO_ROOT / "laclaugpt" / "visualization" / "app.py"
    source = path.read_text(encoding="utf-8").lower()
    rendered_strings = _python_string_constants(path)
    assert 'model_confidence_label = "model-reported confidence (uncalibrated)"' in source
    assert "mean model-reported confidence (uncalibrated)" in rendered_strings
    assert "not probabilities of correctness" in rendered_strings
    assert "quotation verification" in rendered_strings


def test_confidence_documentation_defines_thresholds_as_operational() -> None:
    text = _normalized(
        (REPO_ROOT / "docs" / "CONFIDENCE_AND_UNCERTAINTY.md").read_text(
            encoding="utf-8"
        )
    )
    assert "model-reported, uncalibrated self-report" in text
    assert "not automatically a probability" in text
    assert "operational selection rule" in text
    assert "evidence_verified" in text
    assert "human review" in text
    assert "declared reference task" in text
