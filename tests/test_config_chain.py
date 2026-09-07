from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from laclaugpt.config import (
    arena_from_legacy_config,
    compose_config,
    list_arenas,
)
from laclaugpt.execution import EffectiveRunConfig, RunStore
from run_config import load_run_config, run_config_from_effective, stages_for_analysis


class CanonicalConfigurationTests(unittest.TestCase):
    def test_all_ai_arenas_compose_through_one_chain(self) -> None:
        expected = {
            "elites": ("ai-elites", ("en",), "web"),
            "grassroots": ("ai-grassroots", ("fi",), "tiktok"),
            "parliamentary": ("ai-parliamentary", ("fi",), "tiktok"),
        }
        self.assertEqual(list_arenas("ai26"), sorted(expected))
        for arena, (topic, languages, platform) in expected.items():
            with self.subTest(arena=arena):
                raw = compose_config("ai26", "roihu", "cli", arena=arena)
                effective = EffectiveRunConfig.model_validate(raw)
                self.assertEqual(effective.project, "ai26")
                self.assertEqual(effective.arena, arena)
                self.assertEqual(effective.analysis_profile, f"ai26:{arena}")
                self.assertEqual(effective.dataset["topic_key"], topic)
                self.assertEqual(tuple(effective.dataset["languages"]), languages)
                self.assertEqual(effective.dataset["platforms"], [platform])
                self.assertFalse(effective.dataset["data_policy"]["allow_cloud_fallback"])
                self.assertTrue(effective.analysis["laclau"])
                self.assertTrue(effective.analysis["palonen"])

    def test_project_analysis_switches_are_not_runtime_overridable(self) -> None:
        with self.assertRaisesRegex(ValueError, "analysis switches"):
            compose_config(
                "ai26", "roihu", "cli",
                {"analysis": {"laclau": False}},
                arena="elites",
            )

    def test_module_map_drives_pipeline_stages(self) -> None:
        analysis = {
            "laclau": True,
            "sociotechnical_imaginaries": False,
            "palonen": False,
            "topics": False,
            "entities": True,
            "sentiment": False,
        }
        self.assertEqual(
            stages_for_analysis(analysis),
            ("summary", "discourse", "postprocess"),
        )
        effective = EffectiveRunConfig.model_validate(
            compose_config("ai26", "roihu", "cli", arena="elites")
        )
        cfg = run_config_from_effective(effective, "run-test-123")
        self.assertEqual(cfg.run_id, "run-test-123")
        self.assertEqual(cfg.analysis_profile, "ai26:elites")
        self.assertEqual(cfg.arena_id, "elites")
        self.assertEqual(cfg.stages, ("summary", "discourse", "postprocess", "populism"))
        self.assertTrue(cfg.multimodal)
        self.assertFalse(cfg.allow_cloud_fallback)
        self.assertIn("signifiers", cfg.analytic_hints)

    def test_runstore_exposes_execution_and_profile_identity_separately(self) -> None:
        config = EffectiveRunConfig.compose(
            "ai26", "roihu", "cli", arena="grassroots"
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = RunStore(Path(tmp) / "runs.sqlite3")
            try:
                run = store.create_run(config, "test")
                row = store.connection.execute(
                    "SELECT run_id, analysis_profile, arena_id FROM runs WHERE run_id=?",
                    (run.run_id,),
                ).fetchone()
                self.assertEqual(row, (run.run_id, "ai26:grassroots", "grassroots"))
            finally:
                store.connection.close()

    def test_old_ai_arena_yaml_names_are_compatibility_aliases(self) -> None:
        root = Path(__file__).resolve().parents[1]
        legacy = root / "run_configs" / "arena_elites.yaml"
        self.assertEqual(arena_from_legacy_config(legacy), "elites")
        cfg = load_run_config(legacy)
        self.assertEqual(cfg.arena_id, "elites")
        self.assertEqual(cfg.analysis_profile, "ai26:elites")
        self.assertEqual(cfg.topic_key, "ai-elites")
        self.assertEqual(cfg.run_id, "arena-elites")


if __name__ == "__main__":
    unittest.main()
