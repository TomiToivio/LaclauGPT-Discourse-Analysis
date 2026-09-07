from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from laclaugpt_interchange import SCHEMA_VERSION, from_jsonl
from laclaugpt_memory import Memory as RealMemory
from pipeline import DiscourseStage, SummaryStage, run_pipeline


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_ai.csv"


class _SyntheticSummary:
    def model_dump_json(self) -> str:
        return '{"summary":"AI is presented as a tool for public abundance."}'


class MockedEndToEndTests(unittest.TestCase):
    def test_mocked_pipeline_exports_current_schema_without_external_services(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database_dir = root / "database"
            memory_dir = root / "memory"
            log_dir = root / "logs"
            output = root / "annotations.jsonl"
            run_config = root / "run.yaml"
            run_config.write_text(
                "\n".join((
                    "name: mocked-e2e",
                    "topic_key: generic",
                    "source_platform: synthetic",
                    "language: en",
                    f'database_dir: "{database_dir.as_posix()}"',
                    f'log_dir: "{log_dir.as_posix()}"',
                    f'memory_dir: "{memory_dir.as_posix()}"',
                    f'output_path: "{output.as_posix()}"',
                    "model: synthetic-model",
                    "model_vision: synthetic-model",
                    "ollama_mode: local",
                    "allow_cloud_fallback: false",
                    "stages:",
                    "  summary: true",
                    "  discourse: true",
                    "  postprocess: false",
                    "  populism: false",
                )) + "\n",
                encoding="utf-8",
            )

            def memory_factory(*args, **kwargs):
                kwargs["embedding_backend"] = "none"
                return RealMemory(*args, **kwargs)

            def fake_summary(stage, row, text, metadata):
                return _SyntheticSummary()

            def fake_discourse(stage, row, text, summary_json, metadata):
                return {
                    "signifiers": [],
                    "articulations": [],
                    "imaginaries": [],
                    "formation_candidates": [],
                    "hegemonic_evidence": [],
                    "uncertainties": [],
                }

            with (
                patch("pipeline.Memory", new=memory_factory),
                patch("pipeline.resolve_endpoint", side_effect=lambda model: ("local", model)),
                patch("pipeline.model_digest", return_value="synthetic-digest"),
                patch("llm.describe_routing", return_value="synthetic local routing"),
                patch.object(SummaryStage, "run_row", new=fake_summary),
                patch.object(DiscourseStage, "run_row", new=fake_discourse),
            ):
                annotations = run_pipeline(
                    str(run_config), str(FIXTURE), output_path=str(output)
                )

            self.assertEqual(len(annotations), 1)
            self.assertTrue(output.exists())
            parsed = from_jsonl(str(output))
            self.assertEqual(len(parsed), 1)
            self.assertEqual(parsed[0].schema_version, SCHEMA_VERSION)
            self.assertEqual(parsed[0].document_id, "synthetic::synthetic-1")
            self.assertEqual(parsed[0].source_platform, "synthetic")
            self.assertTrue(parsed[0].requires_human_review)
            self.assertEqual(parsed[0].review_status, "PROVISIONAL")
            self.assertTrue(output.with_suffix(".corpus.json").exists())
            self.assertTrue((log_dir / "glossary_review.csv").exists())


if __name__ == "__main__":
    unittest.main()
