"""Machine-verifiable THEORY.md invariant checks (issue #50).

THEORY.md is the semantic contract; these tests pin down the invariants that
can be checked mechanically. They do NOT claim that interpretive validity is
unit-testable — corpus-level concepts (hegemony, floating/empty signifier
status, polarisation) remain human adjudications. The tests here only make
the schema/visualisation/agent-instruction invariants regress-proof.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from laclaugpt_interchange import (
    SCHEMA_VERSION,
    DocumentAnnotation,
    from_jsonl,
    to_jsonl,
)
from prompts import discourse as discourse_prompt
from prompts import populism as populism_prompt
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_app_module():
    """Load the Streamlit app module without a dashboard runtime."""
    path = REPO_ROOT / "laclaugpt" / "visualization" / "app.py"
    spec = importlib.util.spec_from_file_location("laclaugpt_viz_app_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PopulismFormulaInvariants(unittest.TestCase):
    """INV_POPULISM / INV_ABSTAIN (THEORY.md §15)."""

    def _element(self, term: str = "the people"):
        PopulismElement, _ = populism_prompt.pydantic_models()
        return PopulismElement(
            populism_element=term, evidence_quote="the people demand", confidence=0.8,
        )

    def test_populist_true_requires_both_us_and_frontier(self) -> None:
        _, Formula = populism_prompt.pydantic_models()
        with self.assertRaises(ValidationError):
            Formula(populist=True, populism_analysis="x", populism_us=[self._element()])
        with self.assertRaises(ValidationError):
            Formula(populist=True, populism_analysis="x", populism_frontier=[self._element()])

    def test_populist_true_with_both_sides_is_valid(self) -> None:
        _, Formula = populism_prompt.pydantic_models()
        formula = Formula(
            populist=True, populism_analysis="both sides evidenced",
            populism_us=[self._element("us")],
            populism_frontier=[self._element("elite")],
        )
        self.assertTrue(formula.populist)

    def test_populist_false_requires_reason_and_empty_sides(self) -> None:
        _, Formula = populism_prompt.pydantic_models()
        with self.assertRaises(ValidationError):
            Formula(populist=False, populism_analysis="x", non_populist_reason="")
        formula = Formula(populist=False, populism_analysis="x", non_populist_reason="no frontier")
        self.assertEqual(formula.populism_us, [])


class EvidencePreservationInvariants(unittest.TestCase):
    """INV_EVIDENCE (THEORY.md §15): theory-facing schemas keep evidence fields."""

    def test_every_discourse_coding_model_requires_evidence_quote(self) -> None:
        models = discourse_prompt.pydantic_models()
        for name in ("SignifierCoding", "ArticulationCoding", "ImaginaryCoding",
                     "FormationCandidate"):
            model = getattr(models, name) if hasattr(models, name) else None
        # pydantic_models() returns the top-level class; the element models are
        # accessible through the analysis model's fields.
        analysis = models
        for field_name, field in analysis.model_fields.items():
            if field_name in {"signifiers", "articulations", "imaginaries",
                              "formation_candidates"}:
                inner = (field.annotation or object())
                model = getattr(inner, "__args__", [inner])[0] if hasattr(inner, "__args__") else inner
                self.assertIn("evidence_quote", getattr(model, "model_fields", {}),
                              f"{field_name} element model lost evidence_quote")

    def test_populism_elements_require_evidence_quote(self) -> None:
        PopulismElement, _ = populism_prompt.pydantic_models()
        self.assertIn("evidence_quote", PopulismElement.model_fields)
        self.assertEqual(PopulismElement.model_fields["evidence_quote"].metadata[0].min_length, 1)


class FloatingSignifierCorpusInvariant(unittest.TestCase):
    """INV_FLOAT_CORPUS (THEORY.md §15): corpus-level roles demand validation."""

    def test_floating_and_empty_candidates_flag_corpus_validation(self) -> None:
        models = discourse_prompt.pydantic_models()
        coding = models(
            applicable=True, applicability_reason="test",
            signifiers=[{
                "term": "freedom", "role": "floating_candidate",
                "rationale": "contested", "evidence_quote": "freedom for whom?",
                "confidence": 0.5,
            }],
        )
        self.assertTrue(coding.signifiers[0].needs_corpus_validation)


class AffectNotSentimentInvariant(unittest.TestCase):
    """INV_AFFECT (THEORY.md §15): sentiment cannot ride in as affect, and the
    descriptive Affects dashboard tab is gated by the Laclaudian palonen
    stage, not the sentiment switch."""

    def test_affect_polarity_is_never_inferred_from_side(self) -> None:
        from laclaugpt_interchange import from_memory_results
        ann = from_memory_results(
            "doc::1", platform="synthetic",
            populism={
                "populism_us": [{"obj_id": "S001", "label": "us-element",
                                 "affect": "anger"}],
                "populism_frontier": [],
            },
        )
        self.assertTrue(ann.affects)
        self.assertTrue(all(a.polarity == "" for a in ann.affects))

    def test_affects_tab_not_gated_by_sentiment_switch(self) -> None:
        import ast
        source = (REPO_ROOT / "laclaugpt" / "visualization" / "app.py").read_text(
            encoding="utf-8")
        self.assertNotIn(
            'analysis.get("sentiment") or analysis.get("palonen")', source,
            "Affects tab must not be gated by the descriptive sentiment switch "
            "(INV_AFFECT: sentiment polarity must not substitute for affective "
            "investment)",
        )


class DescriptiveSentimentSeparationInvariant(unittest.TestCase):
    """THEORY.md §8/INV_AFFECT: sentiment is not a substitute for affective
    investment. The schema-level separation (descriptive SentimentObservation
    vs Laclaudian Affect) is added with the sentiment-losslessness work and
    tested there; here we only pin the current polarity rule."""

    def test_affect_polarity_field_stays_empty_when_inferred(self) -> None:
        from laclaugpt_interchange import Affect, from_memory_results
        ann = from_memory_results(
            "doc::1", platform="synthetic",
            populism={
                "populism_frontier": [
                    {"obj_id": "S002", "label": "elite", "affect": "admiration"},
                ],
            },
        )
        self.assertTrue(ann.affects)
        # Affect.polarity must never be auto-filled from the side/affect name:
        for affect in ann.affects:
            self.assertEqual(affect.polarity, "")

    def test_affect_model_has_no_review_status_substitution(self) -> None:
        from laclaugpt_interchange import Affect
        # Affect and a future descriptive sentiment record must remain
        # separate families; polarity field exists but stays empty in
        # from_memory_results (checked above).
        self.assertIn("polarity", Affect.model_fields)


class AgentInstructionInvariant(unittest.TestCase):
    """Agent-facing instructions must reference THEORY.md as required context."""

    def test_hermes_md_requires_reading_theory_md(self) -> None:
        hermes_md = (REPO_ROOT / "HERMES.md").read_text(encoding="utf-8")
        self.assertIn("THEORY.md", hermes_md)
        self.assertIn("read", hermes_md.lower())

    def test_readme_documents_the_theory_contract(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("THEORY.md", readme)

    def test_theory_md_declares_agent_normativity(self) -> None:
        theory = (REPO_ROOT / "THEORY.md").read_text(encoding="utf-8")
        self.assertIn("normative_for_agents: true", theory)
        self.assertIn("theory_invariants:", theory)


if __name__ == "__main__":
    unittest.main()