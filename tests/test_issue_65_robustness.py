"""Regression tests for issue #65 attribution and robustness hardening."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from pydantic import BaseModel, model_validator

import llm
from prompts import discourse, populism, postprocess, summary


class AttributionTests(unittest.TestCase):
    def test_postprocess_sentiment_is_author_voice_only(self) -> None:
        prompt = postprocess.build_system_prompt(include_sentiment=True)
        self.assertIn("OWN ASSERTED VOICE", prompt)
        self.assertIn("quoted, reported, parodied, cited, or rejected speech", prompt)
        self.assertIn("abstain", prompt)

    def test_entity_mentions_do_not_imply_endorsement(self) -> None:
        prompt = postprocess.build_system_prompt(include_entities=True)
        self.assertIn("Entity presence never implies endorsement", prompt)
        self.assertIn("quoted/reported/rejected speech", prompt)

    def test_summary_issue_residual_was_superseded_by_descriptive_screen(self) -> None:
        Summary = summary.pydantic_models()
        self.assertIn("people_power_narrative", Summary.model_fields)
        self.assertNotIn("populist_elements", Summary.model_fields)
        prompt = summary.build_system_prompt("topic", "source")
        self.assertIn("Mentions of \"the people\"", prompt)
        self.assertIn("not by themselves enough", prompt)


class CorpusValidationTests(unittest.TestCase):
    def test_populism_empty_candidate_forces_corpus_validation(self) -> None:
        Element, _ = populism.pydantic_models()
        item = Element(
            populism_element="AI",
            evidence_quote="AI will save everyone",
            confidence=0.7,
            empty_candidate=True,
            needs_corpus_validation=False,
        )
        self.assertTrue(item.needs_corpus_validation)

    def test_imaginary_forces_corpus_validation(self) -> None:
        Analysis = discourse.pydantic_models()
        item_cls = Analysis.model_fields["imaginaries"].annotation.__args__[0]
        item = item_cls(
            label="automated abundance",
            normative_future="abundance",
            present_diagnosis="scarcity",
            technology_role="AI transforms production",
            human_agency="humans direct deployment",
            evidence_quote="AI can create abundance",
            confidence=0.6,
            needs_corpus_validation=False,
        )
        self.assertTrue(item.needs_corpus_validation)


class RetryFeedbackTests(unittest.TestCase):
    def test_structured_retry_receives_actual_validator_message(self) -> None:
        class Guarded(BaseModel):
            value: str

            @model_validator(mode="after")
            def theory_rule(self):
                if self.value != "allowed":
                    raise ValueError("THEORY_RULE: value must be allowed")
                return self

        prompts = []
        responses = iter([
            json.dumps({"value": "wrong"}),
            json.dumps({"value": "allowed"}),
        ])
        provenance = llm.LLMCallProvenance(
            requested_mode="local", requested_model="test",
            resolved_model="test", actual_mode="local", actual_model="test",
        )

        def fake_chat(model, system_prompt, user_prompt, *args, **kwargs):
            prompts.append(user_prompt)
            return next(responses), provenance

        with patch("llm.chat_with_provenance", side_effect=fake_chat):
            result = llm.chat_structured("test", "system", "user", Guarded)

        self.assertEqual(result.value, "allowed")
        self.assertEqual(len(prompts), 2)
        self.assertIn("THEORY_RULE: value must be allowed", prompts[1])
        self.assertIn("Correct the specific schema/theory rule", prompts[1])


if __name__ == "__main__":
    unittest.main()
