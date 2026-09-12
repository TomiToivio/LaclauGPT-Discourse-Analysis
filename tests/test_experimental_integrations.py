from __future__ import annotations

from types import SimpleNamespace

import pytest

from laclaugpt.experimental import (
    INTEGRATIONS,
    OptionalDependencyError,
    available_integrations,
)
from laclaugpt.experimental import _optional, corpus, models


EXPECTED = {
    "pycorpdiff",
    "scattertext",
    "convokit",
    "hypothesaes",
    "textnets",
    "edsl",
}


def test_experimental_registry_is_complete_and_lazy():
    assert set(INTEGRATIONS) == EXPECTED
    assert set(available_integrations()) == EXPECTED


def test_missing_optional_dependency_has_actionable_error(monkeypatch):
    monkeypatch.setattr(_optional, "find_spec", lambda _module: None)

    with pytest.raises(OptionalDependencyError, match="research-experimental"):
        _optional.require("scattertext")


def test_pycorpdiff_keyness_wrapper_is_thin(monkeypatch):
    expected = object()

    class FakeComparison:
        def keyness(self, **kwargs):
            assert kwargs == {"min_count": 3}
            return expected

    fake = SimpleNamespace(compare=lambda left, right: FakeComparison())
    monkeypatch.setattr(corpus, "require", lambda name: fake)

    assert corpus.compare_keyness("left", "right", min_count=3) is expected


def test_edsl_comparison_is_prepared_not_run(monkeypatch):
    calls: list[tuple[str, object]] = []

    class FakeQuestion:
        def __init__(self, **kwargs):
            calls.append(("question", kwargs))

    class FakeModel:
        def __init__(self, name):
            self.name = name

    class FakeModelList(list):
        pass

    fake = SimpleNamespace(
        QuestionFreeText=FakeQuestion,
        Model=FakeModel,
        ModelList=FakeModelList,
    )
    monkeypatch.setattr(models, "require", lambda name: fake)

    question, model_list = models.prepare_model_comparison(
        "Code this synthetic text",
        ["model-a", "model-b"],
    )

    assert isinstance(question, FakeQuestion)
    assert [model.name for model in model_list] == ["model-a", "model-b"]
    assert calls == [
        (
            "question",
            {
                "question_name": "laclaugpt_experimental_question",
                "question_text": "Code this synthetic text",
            },
        )
    ]
