from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from laclaugpt.canonical_pipeline import run_canonical_pipeline
from laclaugpt.config import compose_config
from laclaugpt.execution import EffectiveRunConfig, ExecutionCoordinator, RunStore
from laclaugpt.integrations.fourcat import run_fourcat_rows
from laclaugpt_interchange import from_jsonl
from laclaugpt_memory import Memory as RealMemory
from pipeline import DiscourseStage, PopulismStage, PostprocessStage, SummaryStage


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_ai.csv"
EVIDENCE = "AI is presented as a tool for public abundance"


class _SyntheticSummary:
    def model_dump_json(self) -> str:
        return '{"summary":"AI is presented as a tool for public abundance."}'


class FourcatCanonicalAdapterTests(unittest.TestCase):
    def _patches(self, topic_keys: list[str]):
        def memory_factory(*args, **kwargs):
            kwargs["embedding_backend"] = "none"
            return RealMemory(*args, **kwargs)

        def fake_summary(stage, row, text, metadata):
            topic_keys.append(stage.run.topic_key)
            return _SyntheticSummary()

        def fake_discourse(stage, row, text, summary_json, metadata):
            ai = {
                "obj_id": "s001", "label": "Artificial Intelligence",
                "kind": "signifier", "raw": "artificial intelligence",
                "role": "nodal_candidate", "rationale": "synthetic fixture",
                "evidence": EVIDENCE, "confidence": 0.95,
                "needs_corpus_validation": False, "evidence_verified": True,
                "evidence_source": "text",
            }
            regulation = {
                "obj_id": "s002", "label": "Regulation", "kind": "signifier",
                "raw": "regulation",
            }
            return {
                "signifiers": [ai],
                "articulations": [{
                    "source": ai, "target": regulation, "relation": "difference",
                    "rationale": "synthetic fixture", "evidence": EVIDENCE,
                    "confidence": 0.8, "claim_status": "asserted",
                    "evidence_verified": True, "evidence_source": "text",
                }],
                "imaginaries": [{
                    "label": "abundance", "normative_future": "public abundance",
                    "present_diagnosis": "political choice",
                    "technology_role": "tool", "human_agency": "collective choice",
                    "evidence_quote": EVIDENCE, "confidence": 0.85,
                    "claim_status": "asserted", "evidence_verified": True,
                    "evidence_source": "text",
                }],
                "formation_candidates": [{
                    "obj_id": "f001", "label": "synthetic formation",
                    "kind": "formation", "raw": "synthetic formation",
                    "supporting_features": ["abundance"], "counter_evidence": [],
                    "evidence": EVIDENCE, "confidence": 0.7,
                    "evidence_verified": True, "evidence_source": "text",
                }],
                "hegemonic_evidence": [EVIDENCE],
                "uncertainties": ["synthetic uncertainty"],
            }

        def fake_postprocess(stage, row, text, summary_json):
            return {
                "topics": [{
                    "obj_id": "t001", "label": "AI policy", "kind": "topic",
                    "raw": "AI policy", "decision": "NEW", "ner_type": "",
                }],
                "entities": [{
                    "obj_id": "e001", "label": "Public", "kind": "entity",
                    "raw": "public", "decision": "NEW", "ner_type": "ORG",
                }],
            }

        def fake_populism(stage, row, text, summary_json, discourse, metadata):
            return {
                "populist": True,
                "non_populist_reason": "",
                "populism_analysis": "synthetic Formula of Populism",
                "populism_us": [{
                    "obj_id": "s003", "label": "Public", "kind": "signifier",
                    "raw": "public", "affect": "hope", "evidence": EVIDENCE,
                    "confidence": 0.8, "nodal": False, "empty_candidate": False,
                    "evidence_verified": True, "evidence_source": "text",
                }],
                "populism_frontier": [{
                    "obj_id": "s004", "label": "Constraint", "kind": "signifier",
                    "raw": "constraint", "affect": "concern", "evidence": EVIDENCE,
                    "confidence": 0.75, "nodal": False, "empty_candidate": False,
                    "evidence_verified": True, "evidence_source": "text",
                }],
                "counter_evidence": [],
                "uncertainties": [],
            }

        return (
            patch("pipeline.Memory", new=memory_factory),
            patch("pipeline.resolve_endpoint", side_effect=lambda model: ("local", model)),
            patch("pipeline.model_digest", return_value="synthetic-digest"),
            patch("llm.describe_routing", return_value="synthetic local routing"),
            patch.object(SummaryStage, "run_row", new=fake_summary),
            patch.object(DiscourseStage, "run_row", new=fake_discourse),
            patch.object(PostprocessStage, "run_row", new=fake_postprocess),
            patch.object(PopulismStage, "run_row", new=fake_populism),
        )

    def test_fourcat_matches_direct_canonical_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct_output = root / "direct.ndjson"
            fourcat_output = root / "fourcat.ndjson"
            direct_work = root / "direct-work"
            fourcat_work = root / "fourcat-work"
            topic_keys: list[str] = []

            raw = compose_config(
                "ai26", "roihu", "cli",
                overrides={"dataset": {
                    "input": str(FIXTURE),
                    "output": str(direct_output),
                    "topic_key": "ai-grassroots",
                    "model": {"text": "synthetic-model", "vision": "synthetic-model"},
                    "storage": {"work_dir": str(direct_work)},
                }},
                arena="elites",
            )
            direct_config = EffectiveRunConfig.model_validate(raw)
            direct_store = RunStore(root / "direct-runs.sqlite3")
            try:
                with self._patches(topic_keys):
                    direct_run, direct_result = ExecutionCoordinator(
                        direct_config, direct_store, run_canonical_pipeline
                    ).execute()
            finally:
                direct_store.connection.close()

            with FIXTURE.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            with self._patches(topic_keys):
                fourcat_execution = run_fourcat_rows(
                    rows,
                    output_path=fourcat_output,
                    dataset_key="synthetic-fourcat",
                    project="ai26",
                    arena="elites",
                    machine="roihu",
                    execution="cli",
                    model="synthetic-model",
                    topic_key="ai-grassroots",
                    work_dir=fourcat_work,
                )

            direct = from_jsonl(str(direct_output))[0]
            fourcat = from_jsonl(str(fourcat_output))[0]
            self.assertEqual(topic_keys, ["ai-grassroots", "ai-grassroots"])
            self.assertEqual(direct_result["enabled_modules"], fourcat_execution["result"]["enabled_modules"])
            self.assertEqual(fourcat_execution["config"].dataset["topic_key"], "ai-grassroots")

            analytical_fields = (
                "summary", "signifiers", "signifier_roles", "articulations",
                "imaginaries", "formation_candidates", "topics", "entities",
                "populist", "populism_analysis", "us", "frontier", "affects",
                "prompt_versions", "review_status", "requires_human_review",
            )
            for field in analytical_fields:
                self.assertEqual(getattr(direct, field), getattr(fourcat, field), field)

            self.assertEqual(fourcat.review_status, "PROVISIONAL")
            self.assertTrue(fourcat.requires_human_review)
            self.assertEqual(fourcat.collection_provenance["analysis_profile"], "ai26:elites")
            self.assertEqual(fourcat.collection_provenance["arena_id"], "elites")
            self.assertEqual(fourcat.run_id, fourcat_execution["run"].run_id)
            self.assertNotEqual(fourcat.run_id, direct_run.run_id)
            self.assertTrue(Path(str(fourcat_output) + ".review.csv").exists())
            self.assertFalse((fourcat_work / "fourcat-input.csv").exists())

    def test_canonical_summary_injects_context_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = compose_config(
                "ai26", "roihu", "cli",
                overrides={"dataset": {"storage": {"work_dir": str(root / "work")}}},
                arena="elites",
            )
            config = EffectiveRunConfig.model_validate(raw)
            from run_config import run_config_from_effective
            run = run_config_from_effective(config, "context-run", repository_root=root)

            class FakeMemory:
                def __init__(self):
                    self.calls = []

                def context_prompt_block(self, text, *args, **kwargs):
                    self.calls.append(text)
                    return "CONTEXT-MEMORY-MARKER"

            memory = FakeMemory()
            stage = SummaryStage(run, memory)
            captured = {}

            def fake_system(topic, metadata, context):
                captured["context"] = context
                return "system"

            try:
                from prompts.source_metadata import SourceMetadata
                with (
                    patch("pipeline.summary_prompt.build_system_prompt", side_effect=fake_system),
                    patch.object(stage, "call", return_value=_SyntheticSummary()),
                ):
                    stage.run_row(
                        {"id": "ctx-1", "text": EVIDENCE, "platform": "web", "language": "en"},
                        EVIDENCE,
                        SourceMetadata(
                            platform="web", country="US", language="en",
                            collection="synthetic fixture", has_metadata=True,
                        ),
                    )
            finally:
                stage.close()

            self.assertEqual(memory.calls, [EVIDENCE])
            self.assertEqual(captured["context"], "CONTEXT-MEMORY-MARKER")


if __name__ == "__main__":
    unittest.main()
