"""Experimental EDSL helpers for explicit multi-model research experiments."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ._optional import require


def prepare_model_comparison(
    question_text: str,
    model_names: Sequence[str],
    *,
    question_name: str = "laclaugpt_experimental_question",
) -> tuple[Any, Any]:
    """Prepare, but do not run, an EDSL free-text question across model backends.

    This helper performs no network request. The caller must explicitly execute
    the returned EDSL objects. Agreement across models is a robustness signal only.
    """
    edsl = require("edsl")
    question = edsl.QuestionFreeText(
        question_name=question_name,
        question_text=question_text,
    )
    models = edsl.ModelList(edsl.Model(name) for name in model_names)
    return question, models
