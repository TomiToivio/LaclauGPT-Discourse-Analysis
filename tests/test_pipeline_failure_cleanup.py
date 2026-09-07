from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from laclaugpt.canonical_pipeline import run_canonical_pipeline
from laclaugpt.execution.core import EffectiveRunConfig, ExecutionCoordinator, RunStore
from laclaugpt_memory import Memory as RealMemory
from pipeline import DiscourseStage, Stage, SummaryStage, run_pipeline


class _SyntheticSummary:
    def model_dump_json(self) -> str:
        return '{"summary":"synthetic"}'


_EMPTY_DISCOURSE = {
    "signifiers": [],
    "articulations": [],
    "imaginaries": [],
    "formation_candidates": [],
    "hegemonic_evidence": [],
    "uncertainties": [],
}


def _assert_exclusive_lock_available(testcase: unittest.TestCase, path: Path) -> None:
    testcase.assertTrue(path.exists(), f"expected SQLite database {path}")
    connection = sqlite3.connect(path, timeout=0.1)
    try:
        connection.execute("BEGIN EXCLUSIVE")
        connection.execute("ROLLBACK")
    finally:
        connection.close()


class PipelineFailureCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.database_dir = self.root / "database"
        self.memory_dir = self.root / "memory"
        self.log_dir = self.root / "logs"
        self.output = self.root / "annotations.jsonl"
        self.csv_path = self.root / "input.csv"
        self.csv_path.write_text(
            "id,text,language,platform\n"
            "1,first document,en,test\n"
            "2,second document,en,test\n",
            encoding="utf-8",
        )
        self.run_config = self.root / "run.yaml"
        self.run_config.write_text(
            "\n".join((
                "name: cleanup-test",
                "topic_key: generic",
                "source_platform: test",
                "language: en",
                f'database_dir: "{self.database_dir.as_posix()}"',
                f'log_dir: "{self.log_dir.as_posix()}"',
                f'memory_dir: "{self.memory_dir.as_posix()}"',
                f'output_path: "{self.output.as_posix()}"',
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

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_mid_run_failure_closes_sqlite_and_publishes_no_partial_result(self) -> None:
        created_memories: list[RealMemory] = []
        summary_calls = 0

        def memory_factory(*args, **kwargs):
            kwargs["embedding_backend"] = "none"
            memory = RealMemory(*args, **kwargs)
            created_memories.append(memory)
            return memory

        def fake_summary(stage, row, text, metadata):
            nonlocal summary_calls
            summary_calls += 1
            if summary_calls == 2:
                raise RuntimeError("synthetic mid-run failure")
            return _SyntheticSummary()

        def fake_discourse(stage, row, text, summary_json, metadata):
            return dict(_EMPTY_DISCOURSE)

        with (
            patch("pipeline.Memory", new=memory_factory),
            patch("pipeline.resolve_endpoint", side_effect=lambda model: ("local", model)),
            patch("pipeline.model_digest", return_value="synthetic-digest"),
            patch("llm.describe_routing", return_value="synthetic local routing"),
            patch.object(SummaryStage, "run_row", new=fake_summary),
            patch.object(DiscourseStage, "run_row", new=fake_discourse),
        ):
            with self.assertRaisesRegex(RuntimeError, "synthetic mid-run failure"):
                run_pipeline(str(self.run_config), str(self.csv_path), output_path=str(self.output))

        self.assertEqual(len(created_memories), 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            created_memories[0].conn.execute("SELECT 1")

        _assert_exclusive_lock_available(self, self.database_dir / "summary.db")
        _assert_exclusive_lock_available(self, self.database_dir / "discourse.db")
        memory_db = self.memory_dir / "memory.sqlite3"
        _assert_exclusive_lock_available(self, memory_db)

        # The first document's committed provenance is useful debug state and
        # survives the failure, while success artifacts are never published.
        connection = sqlite3.connect(memory_db)
        try:
            count = connection.execute(
                "SELECT COUNT(*) FROM decisions WHERE stage='pipeline' AND action='analysis'"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(count, 1)

        self.assertFalse(self.output.exists())
        self.assertFalse(self.output.with_suffix(".corpus.json").exists())
        self.assertFalse((self.log_dir / "glossary_review.csv").exists())
        self.assertEqual(list(self.root.rglob("*.partial")), [])

    def test_stage_constructor_closes_connection_when_schema_setup_fails(self) -> None:
        connection = Mock()
        connection.execute.side_effect = RuntimeError("schema failure")
        run = SimpleNamespace(database_dir=self.database_dir)

        with patch("pipeline.sqlite3.connect", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "schema failure"):
                Stage(run, object(), "broken", "test-v1")

        connection.close.assert_called_once_with()

    def test_canonical_coordinator_marks_claims_and_run_failed(self) -> None:
        runs_db = self.root / "runs.sqlite3"
        store = RunStore(runs_db)
        output = self.root / "canonical-output.jsonl"
        config = EffectiveRunConfig(
            project="test",
            machine="local",
            execution="cli",
            analysis={},
            backends={},
            dataset={
                "input": str(self.csv_path),
                "run_config": str(self.run_config),
                "output": str(output),
            },
            orchestration={
                "runtime": {
                    "retry_failed_items": False,
                    "skip_already_processed": True,
                }
            },
        )
        coordinator = ExecutionCoordinator(config, store, run_canonical_pipeline)

        try:
            with patch("pipeline.run_pipeline", side_effect=RuntimeError("synthetic failure")):
                with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                    coordinator.execute()

            run_statuses = store.connection.execute(
                "SELECT status FROM runs"
            ).fetchall()
            checkpoint_statuses = store.connection.execute(
                "SELECT status FROM checkpoints ORDER BY source_id"
            ).fetchall()
            self.assertEqual(run_statuses, [("failed",)])
            self.assertEqual(checkpoint_statuses, [("failed",), ("failed",)])
            self.assertNotIn(("completed",), checkpoint_statuses)
            self.assertFalse(output.exists())
        finally:
            store.connection.close()


if __name__ == "__main__":
    unittest.main()
