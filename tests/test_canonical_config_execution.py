from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from laclaugpt.canonical_pipeline import run_canonical_pipeline
from laclaugpt.config import compose_config
from laclaugpt.execution import EffectiveRunConfig, ExecutionCoordinator, RunStore
from laclaugpt_interchange import from_jsonl
from laclaugpt_memory import Memory as RealMemory
from pipeline import DiscourseStage, PopulismStage, PostprocessStage, SummaryStage


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_ai.csv"


class _SyntheticSummary:
    def model_dump_json(self) -> str:
        return '{"summary":"AI is presented as a tool for public abundance."}'


class CanonicalExecutionProvenanceTests(unittest.TestCase):
    def test_one_run_id_reaches_runstore_annotation_and_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            output = root / "annotations.jsonl"
            raw = compose_config(
                "ai26",
                "roihu",
                "cli",
                {
                    "dataset": {
                        "input": str(FIXTURE),
                        "output": str(output),
                        "storage": {"work_dir": str(work)},
                    }
                },
                arena="elites",
            )
            config = EffectiveRunConfig.model_validate(raw)
            store = RunStore(root / "runs.sqlite3")

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

            def fake_postprocess(stage, row, text, summary_json):
                return {}

            def fake_populism(stage, row, text, summary_json, discourse, metadata):
                return {
                    "populist": False,
                    "non_populist_reason": "synthetic non-populist fixture",
                    "populism_analysis": "",
                    "populism_us": [],
                    "populism_frontier": [],
                    "counter_evidence": [],
                    "uncertainties": [],
                }

            try:
                coordinator = ExecutionCoordinator(config, store, run_canonical_pipeline)
                with (
                    patch("pipeline.Memory", new=memory_factory),
                    patch("pipeline.resolve_endpoint", side_effect=lambda model: ("local", model)),
                    patch("pipeline.model_digest", return_value="synthetic-digest"),
                    patch("llm.describe_routing", return_value="synthetic local routing"),
                    patch.object(SummaryStage, "run_row", new=fake_summary),
                    patch.object(DiscourseStage, "run_row", new=fake_discourse),
                    patch.object(PostprocessStage, "run_row", new=fake_postprocess),
                    patch.object(PopulismStage, "run_row", new=fake_populism),
                ):
                    run_record, result = coordinator.execute()

                annotations = from_jsonl(str(output))
                self.assertEqual(len(annotations), 1)
                annotation = annotations[0]
                self.assertEqual(annotation.run_id, run_record.run_id)
                self.assertEqual(result["run_id"], run_record.run_id)
                self.assertEqual(result["analysis_profile"], "ai26:elites")
                self.assertEqual(result["arena_id"], "elites")
                self.assertEqual(
                    annotation.collection_provenance["analysis_profile"],
                    "ai26:elites",
                )
                self.assertEqual(annotation.collection_provenance["arena_id"], "elites")
                self.assertEqual(
                    annotation.collection_provenance["run_config"]["run_id"],
                    run_record.run_id,
                )

                run_row = store.connection.execute(
                    "SELECT run_id, analysis_profile, arena_id FROM runs WHERE run_id=?",
                    (run_record.run_id,),
                ).fetchone()
                self.assertEqual(
                    run_row,
                    (run_record.run_id, "ai26:elites", "elites"),
                )

                memory_db = work / "database" / "memory" / "memory.sqlite3"
                connection = sqlite3.connect(memory_db)
                try:
                    detail = connection.execute(
                        "SELECT detail FROM decisions "
                        "WHERE stage='pipeline' AND action='analysis' LIMIT 1"
                    ).fetchone()[0]
                finally:
                    connection.close()
                memory_payload = json.loads(detail)
                self.assertEqual(memory_payload["run_id"], run_record.run_id)
                self.assertEqual(
                    memory_payload["collection_provenance"]["run_config"]["analysis_profile"],
                    "ai26:elites",
                )
            finally:
                store.connection.close()


if __name__ == "__main__":
    unittest.main()
