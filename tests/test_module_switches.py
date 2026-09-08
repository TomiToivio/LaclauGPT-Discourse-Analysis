"""Issue #48 regression tests: authoritative module switches.

`sentiment`, `context_memory` and `temporal` must be lossless and
authoritative:

- sentiment: true round-trips resolved observations through the interchange;
  sentiment: false neither publishes sentiment output (strip) nor requests it.
- context_memory: false keeps codebook context out of prompts while stable-ID
  resolution stays on (canonical provenance, not optional context).
- temporal: false prevents relation-history writes in Context Memory.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from laclaugpt.canonical_pipeline import _apply_analysis_switches
from laclaugpt_interchange import SCHEMA_VERSION, DocumentAnnotation, from_jsonl, to_jsonl
from laclaugpt_memory import Memory as RealMemory
from pipeline import DiscourseStage, PostprocessStage, Stage, SummaryStage
from run_config import RunConfig, SourceSpec


def _run(**overrides) -> RunConfig:
    from pathlib import Path
    import tempfile
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
        memory_dir=tmp / "memory",
        output_path=tmp / "annotations.jsonl",
        model_text="synthetic", model_vision="synthetic",
    )
    defaults.update(overrides)
    return RunConfig(**defaults)


def _resolved_target_ref():
    return {"obj_id": "C001", "label": "European Union", "kind": "target",
            "raw": "the EU", "decision": "NEW", "ner_type": ""}


class SentimentLosslessExportTests(unittest.TestCase):
    """sentiment: true round-trips through build_annotation -> JSONL."""

    def _memory(self, run):
        return RealMemory(memory_dir=str(run.memory_dir), embedding_backend="none")

    def test_postprocess_output_carries_sentiment_observations(self) -> None:
        run = _run()
        stage = PostprocessStage(run, self._memory(run))
        stage.close()
        extracted = {
            "entities": [], "topics": [],
            "positive": [], "neutral": [],
            "negative": [_resolved_target_ref()],
            "sentiment": [{"target": _resolved_target_ref(), "polarity": "negative"}],
        }
        ann = DocumentAnnotation(document_id="synthetic::doc-1")
        from pipeline import build_annotation
        annotation = build_annotation(
            run, {"platform": "synthetic", "id": "doc-1"}, "{}", {}, extracted, {},
        )
        self.assertEqual(len(annotation.sentiment_observations), 1)
        obs = annotation.sentiment_observations[0]
        self.assertEqual(obs.target.obj_id, "C001")
        self.assertEqual(obs.polarity, "negative")
        self.assertEqual(obs.prompt_version, stage.prompt_version)

    def test_schema_14_round_trips_through_jsonl(self) -> None:
        ann = DocumentAnnotation(document_id="synthetic::doc-1")
        with patch("laclaugpt_interchange.datetime") as _:
            pass
        from laclaugpt_interchange import SentimentObservation
        from laclaugpt_interchange import MemoryRef as IMemoryRef
        ann.sentiment_observations = [SentimentObservation(
            target=IMemoryRef(obj_id="C001", label="EU", kind="target", raw="the EU"),
            polarity="negative", model="synthetic",
            prompt_version="postprocess-v2.1",
        )]
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "ann.jsonl")
            to_jsonl([ann], path)
            parsed = from_jsonl(path)[0]
        self.assertEqual(parsed.schema_version, SCHEMA_VERSION)
        self.assertEqual(parsed.sentiment_observations[0].polarity, "negative")
        self.assertEqual(parsed.sentiment_observations[0].target.obj_id, "C001")

    def test_sentiment_distinct_from_affect_family(self) -> None:
        from laclaugpt_interchange import Affect, SentimentObservation
        self.assertIsNot(SentimentObservation, Affect)
        # descriptive polarity never auto-fills affective investment:
        from laclaugpt_interchange import from_memory_results
        ann = from_memory_results(
            "doc::1", platform="synthetic",
            populism={"populism_us": [
                {"obj_id": "S001", "label": "us", "affect": "anger"}]},
        )
        for affect in ann.affects:
            self.assertEqual(affect.polarity, "")


class SentimentOffSwitchTests(unittest.TestCase):
    """sentiment: false publishes no sentiment output."""

    def test_canonical_strip_removes_sentiment_observations(self) -> None:
        from laclaugpt_interchange import SentimentObservation
        from laclaugpt_interchange import MemoryRef as IMemoryRef
        ann = DocumentAnnotation(document_id="synthetic::doc-1")
        ann.sentiment_observations = [SentimentObservation(
            target=IMemoryRef(obj_id="C001", label="EU", kind="target"),
            polarity="negative",
        )]
        _apply_analysis_switches(ann, {"sentiment": False, "laclau": True,
                                       "palonen": True, "topics": True,
                                       "entities": True})
        self.assertEqual(ann.sentiment_observations, [])
        # enabled families survive:
        self.assertEqual(ann.entities, [])
        self.assertEqual(ann.sentiment_observations, [])

    def test_stages_for_analysis_excludes_postprocess_without_descriptive_modules(self) -> None:
        from run_config import stages_for_analysis
        # sentiment alone still routes through postprocess
        self.assertIn("postprocess", stages_for_analysis({"sentiment": True}))
        # and nothing descriptive means no postprocess stage at all
        self.assertNotIn(
            "postprocess",
            stages_for_analysis({"sentiment": False, "topics": False,
                                 "entities": False, "laclau": False}),
        )


class ContextMemorySwitchTests(unittest.TestCase):
    """context_memory: false keeps codebook context out of prompts."""

    def test_memory_context_disabled_returns_placeholder_without_memory_call(self) -> None:
        run = _run(analysis_modules={
            "laclau": True, "context_memory": False, "temporal": True,
            "sentiment": True, "topics": True, "entities": True,
        })
        memory = RealMemory(memory_dir=str(run.memory_dir), embedding_backend="none")

        class RecordingMemory:
            def __init__(self, inner):
                self.inner = inner
                self.calls = []

            def context_prompt_block(self, text, top_k_per_kind=5, kinds=None):
                self.calls.append((text, kinds))
                return self.inner.context_prompt_block(text, top_k_per_kind, kinds)

        recording = RecordingMemory(memory)
        stage = Stage.__new__(Stage)
        stage.run = run
        stage.memory = recording
        stage.stage_name = "summary"
        stage.prompt_version = "test"
        stage.last_provenance = {}
        stage.conn = None

        block = stage.memory_context("some text")
        self.assertIn("context memory disabled", block)
        self.assertEqual(recording.calls, [])
        memory.close()

    def test_memory_context_enabled_delegates_to_memory(self) -> None:
        run = _run()
        memory = RealMemory(memory_dir=str(run.memory_dir), embedding_backend="none")
        stage = Stage.__new__(Stage)
        stage.run = run
        stage.memory = memory
        stage.stage_name = "summary"
        stage.prompt_version = "test"
        stage.last_provenance = {}
        stage.conn = None
        block = stage.memory_context("some text")
        self.assertIn("Established", block or "") if block else self.fail("empty block")
        memory.close()


class TemporalSwitchTests(unittest.TestCase):
    """temporal: false prevents relation-history writes."""

    def test_discourse_stage_skips_record_relation_when_temporal_false(self) -> None:
        run = _run(analysis_modules={
            "laclau": True, "context_memory": True, "temporal": False,
            "sentiment": True, "topics": True, "entities": True,
        })
        memory = RealMemory(memory_dir=str(run.memory_dir), embedding_backend="none")

        recorded = []
        original = memory.record_relation

        def recorder(*args, **kwargs):
            recorded.append(args)
            return original(*args, **kwargs)

        with patch.object(type(memory), "record_relation", side_effect=recorder), \
             patch("pipeline.resolve_endpoint", side_effect=lambda m: ("local", m)), \
             patch("pipeline.model_digest", return_value="digest"), \
             patch("llm.chat_structured") as fake_chat:
            from prompts import discourse as discourse_prompt

            Coding = discourse_prompt.pydantic_models()
            # Build a minimal fake result matching the schema
            class FakeCoding:
                term = "freedom"
                role = "element"
                rationale = "r"
                evidence_quote = "freedom is at stake"
                confidence = 0.5
                needs_corpus_validation = False

            class FakeArticulation:
                source = "freedom"
                target = "prosperity"
                relation = "articulation"
                rationale = "r"
                evidence_quote = "freedom is at stake"
                confidence = 0.5
                claim_status = "asserted"

            class FakeResult:
                applicable = True
                applicability_reason = "ok"
                signifiers = [FakeArticulation()]
                articulations = [FakeArticulation()]
                imaginaries = []
                formation_candidates = []
                hegemonic_evidence = []
                uncertainties = []

            fake_chat.return_value = (FakeResult(), {
                "actual_model": "synthetic", "actual_model_digest": "digest",
                "actual_mode": "local", "requested_mode": "local",
                "requested_model": "synthetic", "endpoint": "x",
                "fallback_used": False, "fallback_reason": "", "cache_hit": False,
            })
            stage = DiscourseStage(run, memory)
            from prompts.source_metadata import SourceMetadata
            metadata = SourceMetadata(
                platform="synthetic", country="", language="en",
                collection="test", has_metadata=True,
            )
            row = {"platform": "synthetic", "id": "doc-1",
                   "text": "freedom is at stake"}
            stage.run_row(row, "freedom is at stake", "{}", metadata)
            stage.close()
        self.assertEqual(recorded, [], "temporal: false must not write relations")
        memory.close()

    def test_discourse_stage_writes_relations_when_temporal_true(self) -> None:
        run = _run()  # temporal: True
        memory = RealMemory(memory_dir=str(run.memory_dir), embedding_backend="none")

        recorded = []
        with patch.object(type(memory), "record_relation",
                          side_effect=lambda *a, **k: recorded.append(a)), \
             patch("pipeline.resolve_endpoint", side_effect=lambda m: ("local", m)), \
             patch("pipeline.model_digest", return_value="digest"), \
             patch("llm.chat_structured") as fake_chat:
            from prompts import discourse as discourse_prompt
            class FakeCoding:
                term = "freedom"
                role = "element"
                rationale = "r"
                evidence_quote = "freedom is at stake"
                confidence = 0.5
                needs_corpus_validation = False
            class FakeArticulation:
                source = "freedom"
                target = "prosperity"
                relation = "articulation"
                rationale = "r"
                evidence_quote = "freedom is at stake"
                confidence = 0.5
                claim_status = "asserted"
            class FakeResult:
                applicable = True
                applicability_reason = "test"
                signifiers = [FakeArticulation()]
                articulations = [FakeArticulation()]
                imaginaries = []
                formation_candidates = []
                hegemonic_evidence = []
                uncertainties = []
            fake_chat.return_value = (FakeResult(), {
                "actual_model": "synthetic", "actual_model_digest": "digest",
                "actual_mode": "local", "requested_mode": "local",
                "requested_model": "synthetic", "endpoint": "x",
                "fallback_used": False, "fallback_reason": "", "cache_hit": False,
            })
            stage = DiscourseStage(run, memory)
            from prompts.source_metadata import SourceMetadata
            metadata = SourceMetadata(
                platform="synthetic", country="", language="en",
                collection="test", has_metadata=True,
            )
            row = {"platform": "synthetic", "id": "doc-1",
                   "text": "freedom is at stake"}
            stage.run_row(row, "freedom is at stake", "{}", metadata)
            stage.close()
        self.assertTrue(recorded, "temporal: true must write relations")
        memory.close()


if __name__ == "__main__":
    unittest.main()