"""Regression tests for issue #15.

No real Ollama endpoint or cloud request is used. The transport is mocked so
these tests exercise routing and provenance only.
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

import llm


class _FakeClient:
    def __init__(self, failures):
        self.failures = list(failures)
        self.models = []

    def chat(self, *, model, messages, options, **kwargs):
        self.models.append(model)
        if self.failures:
            failure = self.failures.pop(0)
            if failure is not None:
                raise failure
        return {"message": {"content": '{"value":"ok"}'}}


class _Answer(BaseModel):
    value: str


def _force_local(monkeypatch):
    monkeypatch.setattr(llm, "resolve_endpoint", lambda model: ("local", "local-test-model"))
    monkeypatch.setattr(llm, "model_digest", lambda model: f"digest:{model}")


def test_local_failure_does_not_fallback_by_default(monkeypatch):
    _force_local(monkeypatch)
    client = _FakeClient([ConnectionError("local down")])
    monkeypatch.setattr(llm, "_client", lambda: client)

    with pytest.raises(ConnectionError):
        llm.chat_with_provenance("auto", "system", "user")

    assert client.models == ["local-test-model"]


def test_authorised_retryable_failure_records_actual_cloud_model(monkeypatch):
    _force_local(monkeypatch)
    client = _FakeClient([ConnectionError("local down"), None])
    monkeypatch.setattr(llm, "_client", lambda: client)

    content, provenance = llm.chat_with_provenance(
        "auto", "system", "user", allow_cloud_fallback=True,
    )

    assert content == '{"value":"ok"}'
    assert client.models == ["local-test-model", llm.LLM_DEFAULT_CLOUD]
    assert provenance.requested_mode == "local"
    assert provenance.resolved_model == "local-test-model"
    assert provenance.actual_mode == "cloud"
    assert provenance.actual_model == llm.LLM_DEFAULT_CLOUD
    assert provenance.actual_model_digest == f"digest:{llm.LLM_DEFAULT_CLOUD}"
    assert provenance.fallback_used is True
    assert "ConnectionError" in provenance.fallback_reason


def test_non_retryable_error_never_falls_back(monkeypatch):
    _force_local(monkeypatch)
    client = _FakeClient([ValueError("bad request")])
    monkeypatch.setattr(llm, "_client", lambda: client)

    with pytest.raises(ValueError):
        llm.chat_with_provenance(
            "auto", "system", "user", allow_cloud_fallback=True,
        )

    assert client.models == ["local-test-model"]


def test_structured_call_returns_actual_model_provenance(monkeypatch):
    _force_local(monkeypatch)
    client = _FakeClient([TimeoutError("local timeout"), None])
    monkeypatch.setattr(llm, "_client", lambda: client)

    result, provenance = llm.chat_structured(
        "auto", "system", "user", _Answer,
        allow_cloud_fallback=True, return_provenance=True,
    )

    assert result.value == "ok"
    assert provenance.actual_model == llm.LLM_DEFAULT_CLOUD
    assert provenance.actual_mode == "cloud"
    assert provenance.fallback_used is True
