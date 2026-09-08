"""Regression tests for issue #51: summary must stay descriptive."""
from __future__ import annotations

import unittest

from pydantic import ValidationError

from pipeline import SUMMARY_PROMPT_VERSION
from prompts import summary as summary_prompt


class SummaryTheoryBoundaryTests(unittest.TestCase):
    def _base(self) -> dict:
        return {
            "narrative_construction": "A speaker addresses viewers.",
            "political_classification": "political",
            "political": True,
            "political_subcategory": "campaign speech",
            "difficult_language": [],
            "key_political_topics": [],
            "political_entities": [],
            "sentiments": [],
            "social_contract": [],
            "grievances": [],
        }

    def test_summary_schema_has_descriptive_screen_not_theory_codes(self) -> None:
        Summary = summary_prompt.pydantic_models()
        fields = Summary.model_fields
        self.assertIn("people_power_narrative", fields)
        self.assertNotIn("populist_elements", fields)

    def test_present_screen_requires_both_expressions_and_quote(self) -> None:
        Summary = summary_prompt.pydantic_models()
        row = self._base()
        row["people_power_narrative"] = {
            "status": "present",
            "collective_expression": "we citizens",
            "opposed_expression": "the government",
            "evidence_quote": "We citizens will not let the government decide for us.",
            "explanation": "Explicit collective/opposed construction.",
        }
        result = Summary.model_validate(row)
        self.assertEqual(result.people_power_narrative.status, "present")

        row["people_power_narrative"]["evidence_quote"] = ""
        with self.assertRaises(ValidationError):
            Summary.model_validate(row)

    def test_absence_and_uncertainty_are_valid_abstentions(self) -> None:
        Summary = summary_prompt.pydantic_models()
        for status in ("absent", "uncertain"):
            row = self._base()
            row["people_power_narrative"] = {
                "status": status,
                "explanation": "No complete collective-versus-opponent construction is evidenced.",
            }
            result = Summary.model_validate(row)
            self.assertEqual(result.people_power_narrative.status, status)

    def test_prompt_reserves_theoretical_categories_for_later_stages(self) -> None:
        prompt = summary_prompt.build_system_prompt("topic", "source", "memory")
        self.assertIn("descriptive only", prompt)
        self.assertIn("DO NOT label material", prompt)
        self.assertIn("handled later by the discourse/populism stages", prompt)

    def test_prompt_has_explicit_provenance_version(self) -> None:
        self.assertEqual(summary_prompt.PROMPT_VERSION, "summary-v2.2")
        self.assertEqual(SUMMARY_PROMPT_VERSION, summary_prompt.PROMPT_VERSION)


if __name__ == "__main__":
    unittest.main()
