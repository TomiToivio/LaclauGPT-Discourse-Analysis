"""Stage-aware local model routing tests (Laskin AI26, Tomi's 2026-09-08 rule).

No network, no Ollama daemon: chat_structured and pick_model are mocked.
Verifies that gemma4-configured runs resolve a per-stage local model while
non-gemma4 configurations (synthetic mocks, cloud tags) are left untouched.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline
from pipeline import Stage, _is_local_gemma4
from run_config import RunConfig


def _run(model: str, tmp: str) -> RunConfig:
    return RunConfig(
        run_id="routing-test",
        topic_key="ai-elites",
        sources=[],
        model_text=model,
        model_vision=model,
        database_dir=Path(tmp) / "database",
        allow_cloud_fallback=False,
        temperature=0.0,
        num_ctx=8192,
        num_predict=256,
    )


class _Result:
    @staticmethod
    def model_dump_json() -> str:
        return "{}"


class _Provenance:
    def __init__(self, model: str = "served-model"):
        self.actual_model = model
        self.actual_model_digest = f"digest:{model}"
        self.actual_mode = "local"
        self.endpoint = "test"
        self.fallback_used = False
        self.fallback_reason = ""

    def to_dict(self) -> dict:
        return {
            "actual_model": self.actual_model,
            "actual_model_digest": self.actual_model_digest,
            "actual_mode": self.actual_mode, "endpoint": self.endpoint,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason, "cache_hit": False,
        }


class _Model:
    @classmethod
    def model_validate_json(cls, raw: str):
        return cls()


class IsLocalGemma4Tests(unittest.TestCase):
    def test_local_gemma4_tags_detected(self) -> None:
        self.assertTrue(_is_local_gemma4("gemma4:e4b"))
        self.assertTrue(_is_local_gemma4("gemma4:26b"))
        self.assertTrue(_is_local_gemma4("Gemma4:12B"))

    def test_cloud_and_non_gemma4_rejected(self) -> None:
        self.assertFalse(_is_local_gemma4("gemma4:31b-cloud"))
        self.assertFalse(_is_local_gemma4("glm-5.3-flash:cloud"))
        self.assertFalse(_is_local_gemma4("synthetic-model"))
        self.assertFalse(_is_local_gemma4(""))
        self.assertFalse(_is_local_gemma4(None))


class StageRoutingTests(unittest.TestCase):
    def test_discourse_stage_routes_to_requested_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stage = Stage(_run("gemma4:e4b", tmp), None, "discourse", "v-test")
            try:
                with (
                    patch.object(pipeline, "_stage_pick_model",
                                 lambda stage_name, text_len: "gemma4:26b"),
                    patch.object(pipeline, "chat_structured",
                                 return_value=(_Result(), _Provenance())) as fake,
                    patch.object(pipeline, "resolve_endpoint",
                                 side_effect=lambda m: ("local", m)),
                    patch.object(pipeline, "model_digest",
                                 side_effect=lambda m: f"digest:{m}"),
                ):
                    stage.call("doc-1", "system", "user text", _Model)
                served = fake.call_args[0][0]
                self.assertEqual(served, "gemma4:26b")
            finally:
                stage.close()

    def test_long_text_escalation_argument_reaches_router(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stage = Stage(_run("gemma4:e4b", tmp), None, "summary", "v-test")
            try:
                seen: dict = {}

                def router(stage_name: str, text_len: int) -> str:
                    seen["stage"] = stage_name
                    seen["text_len"] = text_len
                    return "gemma4:26b"

                with (
                    patch.object(pipeline, "_stage_pick_model", router),
                    patch.object(pipeline, "chat_structured",
                                 return_value=(_Result(), _Provenance())),
                    patch.object(pipeline, "resolve_endpoint",
                                 side_effect=lambda m: ("local", m)),
                    patch.object(pipeline, "model_digest",
                                 side_effect=lambda m: f"digest:{m}"),
                ):
                    stage.call("doc-1", "s", "u" * 9000, _Model)
                self.assertEqual(seen["stage"], "summary")
                self.assertEqual(seen["text_len"], 9000 - 1)
            finally:
                stage.close()

    def test_non_gemma4_model_is_not_routed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stage = Stage(_run("synthetic-model", tmp), None, "discourse", "v-test")
            try:
                routed: list[str] = []

                def router(stage_name: str, text_len: int) -> str:
                    routed.append(stage_name)
                    return "gemma4:26b"

                with (
                    patch.object(pipeline, "_stage_pick_model", router),
                    patch.object(pipeline, "chat_structured",
                                 return_value=(_Result(), _Provenance())) as fake,
                    patch.object(pipeline, "resolve_endpoint",
                                 side_effect=lambda m: ("local", m)),
                    patch.object(pipeline, "model_digest",
                                 side_effect=lambda m: f"digest:{m}"),
                ):
                    stage.call("doc-1", "system", "user", _Model)
                self.assertEqual(routed, [])
                self.assertEqual(fake.call_args[0][0], "synthetic-model")
            finally:
                stage.close()

    def test_router_failure_falls_back_to_configured_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stage = Stage(_run("gemma4:e4b", tmp), None, "populism", "v-test")
            try:
                def boom(stage_name: str, text_len: int) -> str:
                    raise RuntimeError("no local model fits VRAM")

                with (
                    patch.object(pipeline, "_stage_pick_model", boom),
                    patch.object(pipeline, "chat_structured",
                                 return_value=(_Result(), _Provenance())) as fake,
                    patch.object(pipeline, "resolve_endpoint",
                                 side_effect=lambda m: ("local", m)),
                    patch.object(pipeline, "model_digest",
                                 side_effect=lambda m: f"digest:{m}"),
                ):
                    stage.call("doc-1", "system", "user", _Model)
                self.assertEqual(fake.call_args[0][0], "gemma4:e4b")
            finally:
                stage.close()


if __name__ == "__main__":
    unittest.main()