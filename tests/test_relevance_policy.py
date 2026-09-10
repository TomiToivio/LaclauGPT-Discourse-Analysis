"""Project-specific relevance policy regression tests."""
from __future__ import annotations

import unittest

from laclaugpt_interchange import DocumentAnnotation, MemoryRef
from pipeline import _apply_relevance, corpus_synthesis
from run_config import RunConfig


def _run(*, mode: str = "retain_unjudged", scope: str = "",
         terms: tuple[str, ...] = ()) -> RunConfig:
    return RunConfig(
        run_id="test-run",
        topic_key="test",
        sources=[],
        project="test-project",
        relevance_mode=mode,
        relevance_scope=scope,
        relevance_terms=terms,
    )


def _ann(summary: str = "") -> DocumentAnnotation:
    return DocumentAnnotation(document_id="D1", summary=summary)


class RelevancePolicyTests(unittest.TestCase):

    def test_retain_unjudged_keeps_zero_code_document(self) -> None:
        ann = _ann("AI deployment and labour are discussed without a clear articulation")
        _apply_relevance(ann, ann.summary, {"applicable": True}, _run())
        self.assertIsNone(ann.relevance)
        self.assertEqual(ann.relevance_reason, "")

        synthesis = corpus_synthesis([ann])
        self.assertEqual(synthesis["documents"], 1)
        self.assertEqual(synthesis["documents_excluded_irrelevant"], 0)

    def test_explicit_non_applicability_marks_irrelevant(self) -> None:
        ann = _ann("unrelated source")
        ann.discourse_applicable = False
        ann.discourse_applicability_reason = "no analysable political discourse"
        _apply_relevance(ann, ann.summary, {"applicable": False}, _run())
        self.assertEqual(ann.relevance, "irrelevant")
        self.assertIn("non-applicable", ann.relevance_reason)

    def test_coded_content_is_relevant_without_keyword_gate(self) -> None:
        ann = _ann("ambiguous summary")
        ann.us = [MemoryRef(obj_id="U1", label="workers", kind="signifier")]
        _apply_relevance(ann, ann.summary, {"applicable": True}, _run())
        self.assertEqual(ann.relevance, "relevant")

    def test_keyword_scope_uses_project_configuration(self) -> None:
        run = _run(
            mode="keyword_scope",
            scope="political/electoral",
            terms=("election", "parliament"),
        )
        relevant = _ann("European Parliament election campaign")
        _apply_relevance(relevant, relevant.summary, {"applicable": True}, run)
        self.assertEqual(relevant.relevance, "relevant")

        irrelevant = _ann("a music performance")
        _apply_relevance(irrelevant, irrelevant.summary, {"applicable": True}, run)
        self.assertEqual(irrelevant.relevance, "irrelevant")
        self.assertIn("test-project keyword scope gate", irrelevant.relevance_reason)

    def test_empty_keyword_vocabulary_fails_open(self) -> None:
        ann = _ann("zero-code document")
        run = _run(mode="keyword_scope", scope="test", terms=())
        _apply_relevance(ann, ann.summary, {"applicable": True}, run)
        self.assertIsNone(ann.relevance)


if __name__ == "__main__":
    unittest.main()
