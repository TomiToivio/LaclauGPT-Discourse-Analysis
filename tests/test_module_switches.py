"""Issue #48 regression tests: authoritative analysis-module switches."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from laclaugpt.canonical_pipeline import _apply_analysis_switches
from laclaugpt_interchange import (
    SCHEMA_VERSION, DocumentAnnotation, MemoryRef as IMemoryRef,
    SentimentObservation, from_jsonl, to_jsonl,
)
from pipeline import DiscourseStage, PostprocessStage, Stage, build_annotation
from prompts.source_metadata import SourceMetadata
from run_config import RunConfig, SourceSpec, stages_for_analysis


def _run(**overrides) -> RunConfig:
    tmp = Path(tempfile.mkdtemp())
    defaults = dict(
        run_id="run-issue-48", analysis_profile="ai26:test", arena_id="test",
        project="ai26", analysis_modules={
            "laclau": True, "sentiment": True, "context_memory": True,
            "temporal": True, "topics": True, "entities": True,
        },
        topic_key="ai-contestation",
        sources=[SourceSpec(platform="synthetic", language="en")],
        database_dir=tmp / "database", log_dir=tmp / "logs",
        memory_dir=tmp / "memory", output_path=tmp / "annotations.jsonl",
        model_text="synthetic", model_vision="synthetic",
    )
    defaults.update(overrides)
    return RunConfig(**defaults)


class FakeMemory:
    def __init__(self):
        self.context_calls: list[tuple[str, object]] = []
        self.relations: list[tuple[tuple, dict]] = []
        self.resolutions: list[tuple[str, str]] = []

    def context_prompt_block(self, text, top_k_per_kind=5, kinds=None):
        self.context_calls.append((text, kinds))
        return "Established synthetic context"

    def resolve(self, raw, kind, **kwargs):
        self.resolutions.append((raw, kind))
        prefix = {"target": "C", "entity": "E", "topic": "T", "signifier": "S",
                  "formation": "F"}.get(kind, "X")
        return SimpleNamespace(
            obj_id=f"{prefix}001", label=raw, kind=kind, raw=raw,
            decision="NEW", type_="",
        )

    def record_relation(self, *args, **kwargs):
        self.relations.append((args, kwargs))


class SentimentLosslessExportTests(unittest.TestCase):
    def test_schema_14_round_trips_descriptive_sentiment(self) -> None:
        ann = DocumentAnnotation(document_id="synthetic::doc-1")
        ann.sentiment_observations = [SentimentObservation(
            target=IMemoryRef(obj_id="C001", label="EU", kind="target", raw="the EU"),
            polarity="negative", evidence_source="text", uncertainty=0.25,
            model="synthetic", prompt_version="postprocess-v2.2",
            review_status="PROVISIONAL",
        )]
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "ann.jsonl")
            to_jsonl([ann], path)
            parsed = from_jsonl(path)[0]
        obs = parsed.sentiment_observations[0]
        self.assertEqual(parsed.schema_version, SCHEMA_VERSION)
        self.assertEqual(obs.target.obj_id, "C001")
        self.assertEqual(obs.target.raw, "the EU")
        self.assertEqual(obs.polarity, "negative")
        self.assertEqual(obs.evidence_source, "text")
        self.assertEqual(obs.uncertainty, 0.25)
        self.assertEqual(obs.model, "synthetic")
        self.assertEqual(obs.prompt_version, "postprocess-v2.2")
        self.assertEqual(obs.review_status, "PROVISIONAL")

    def test_build_annotation_uses_postprocess_actual_model(self) -> None:
        run = _run()
        extracted = {"entities": [], "topics": [], "sentiment": [{
            "target": {"obj_id": "C001", "label": "EU", "kind": "target",
                       "raw": "the EU", "ner_type": ""},
            "polarity": "negative", "evidence_source": "text", "uncertainty": 0.2,
        }]}
        ann = build_annotation(
            run, {"platform": "synthetic", "id": "doc-1"}, "{}", {}, extracted, {},
            stage_provenance={"postprocess": {"actual_model": "actual-post-model"}},
        )
        obs = ann.sentiment_observations[0]
        self.assertEqual(obs.target.obj_id, "C001")
        self.assertEqual(obs.target.raw, "the EU")
        self.assertEqual(obs.model, "actual-post-model")
        self.assertEqual(obs.review_status, "PROVISIONAL")

    def test_sentiment_is_distinct_from_laclaudian_affect(self) -> None:
        from laclaugpt_interchange import Affect
        self.assertIsNot(SentimentObservation, Affect)


class SentimentSwitchTests(unittest.TestCase):
    def test_sentiment_false_strips_publication(self) -> None:
        ann = DocumentAnnotation(document_id="synthetic::doc-1")
        ann.sentiment_observations = [SentimentObservation(
            target=IMemoryRef(obj_id="C001", label="EU", kind="target"),
            polarity="negative",
        )]
        _apply_analysis_switches(ann, {
            "sentiment": False, "laclau": True, "palonen": True,
            "topics": True, "entities": True,
        })
        self.assertEqual(ann.sentiment_observations, [])

    def test_sentiment_false_is_not_requested_when_postprocess_runs_for_topics(self) -> None:
        run = _run(analysis_modules={
            "laclau": True, "sentiment": False, "context_memory": True,
            "temporal": True, "topics": True, "entities": False,
        })
        memory = FakeMemory()
        stage = PostprocessStage(run, memory)
        Extraction = __import__("prompts.postprocess", fromlist=["pydantic_models"]).pydantic_models()
        with patch.object(stage, "call", return_value=Extraction()) as mocked:
            result = stage.run_row(
                {"platform": "synthetic", "id": "doc-1", "text": "hello"},
                "hello", "{}",
            )
        system = mocked.call_args.args[1]
        self.assertNotIn("Determine descriptive sentiment", system)
        self.assertEqual(result["sentiment"], [])
        stage.close()

    def test_sentiment_true_requests_structured_evidence_bearing_reading(self) -> None:
        from prompts import postprocess as postprocess_prompt
        run = _run()
        memory = FakeMemory()
        stage = PostprocessStage(run, memory)
        Extraction = postprocess_prompt.pydantic_models()
        reading_type = Extraction.model_fields["sentiments"].annotation.__args__[0]
        result = Extraction(sentiments=[reading_type(
            target="the EU", polarity="negative",
            evidence_quote="the EU failed us", uncertainty=0.3,
        )])
        row = {"platform": "synthetic", "id": "doc-1",
               "text": "the EU failed us"}
        with patch.object(stage, "call", return_value=result) as mocked:
            extracted = stage.run_row(row, row["text"], "{}")
        system = mocked.call_args.args[1]
        self.assertIn("Determine descriptive sentiment", system)
        self.assertEqual(extracted["sentiment"][0]["target"]["obj_id"], "C001")
        self.assertEqual(extracted["sentiment"][0]["target"]["raw"], "the EU")
        self.assertEqual(extracted["sentiment"][0]["polarity"], "negative")
        self.assertEqual(extracted["sentiment"][0]["evidence_source"], "text")
        self.assertEqual(extracted["sentiment"][0]["uncertainty"], 0.3)
        stage.close()

    def test_stage_mapping_only_runs_postprocess_for_enabled_descriptive_families(self) -> None:
        self.assertIn("postprocess", stages_for_analysis({"sentiment": True}))
        self.assertNotIn("postprocess", stages_for_analysis({
            "sentiment": False, "topics": False, "entities": False, "laclau": False,
        }))


class ContextMemorySwitchTests(unittest.TestCase):
    def _stage(self, run, memory):
        stage = Stage.__new__(Stage)
        stage.run = run
        stage.memory = memory
        stage.stage_name = "summary"
        stage.prompt_version = "test"
        stage.last_provenance = {}
        stage.conn = None
        return stage

    def test_context_memory_false_does_not_call_codebook_context(self) -> None:
        run = _run(analysis_modules={
            "laclau": True, "context_memory": False, "temporal": True,
            "sentiment": True, "topics": True, "entities": True,
        })
        memory = FakeMemory()
        block = self._stage(run, memory).memory_context("some text")
        self.assertIn("context memory disabled", block)
        self.assertEqual(memory.context_calls, [])

    def test_context_memory_true_delegates_to_codebook_context(self) -> None:
        run = _run()
        memory = FakeMemory()
        block = self._stage(run, memory).memory_context("some text")
        self.assertEqual(block, "Established synthetic context")
        self.assertEqual(len(memory.context_calls), 1)


class TemporalSwitchTests(unittest.TestCase):
    def _run_discourse(self, temporal: bool) -> FakeMemory:
        from prompts import discourse as discourse_prompt
        run = _run(analysis_modules={
            "laclau": True, "context_memory": True, "temporal": temporal,
            "sentiment": True, "topics": True, "entities": True,
        })
        memory = FakeMemory()
        stage = DiscourseStage(run, memory)
        Analysis = discourse_prompt.pydantic_models()
        fake = Analysis(
            applicable=True,
            applicability_reason="synthetic",
            signifiers=[{
                "term": "freedom", "role": "element", "rationale": "synthetic",
                "evidence_quote": "freedom is at stake", "confidence": 0.6,
            }],
            articulations=[{
                "source": "freedom", "target": "prosperity",
                "relation": "articulation", "rationale": "synthetic",
                "evidence_quote": "freedom is at stake", "confidence": 0.6,
            }],
        )
        metadata = SourceMetadata(
            platform="synthetic", country="", language="en",
            collection="synthetic test", has_metadata=True,
        )
        row = {"platform": "synthetic", "id": "doc-1",
               "text": "freedom is at stake"}
        with patch.object(stage, "call", return_value=fake):
            stage.run_row(row, row["text"], "{}", metadata)
        stage.close()
        return memory

    def test_temporal_false_skips_relation_history_write(self) -> None:
        self.assertEqual(self._run_discourse(False).relations, [])

    def test_temporal_true_writes_relation_history(self) -> None:
        self.assertTrue(self._run_discourse(True).relations)


if __name__ == "__main__":
    unittest.main()
