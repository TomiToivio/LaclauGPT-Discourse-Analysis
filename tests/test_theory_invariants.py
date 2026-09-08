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

    def _formula(self) -> tuple:
        # The nested models are rebuilt per pydantic_models() call, so both
        # must come from the same call for isinstance checks to pass.
        return populism_prompt.pydantic_models()

    def test_populist_true_requires_both_us_and_frontier(self) -> None:
        _, Formula = self._formula()
        PopulismElement, _ = self._formula()
        element = PopulismElement(
            populism_element="the people", evidence_quote="the people demand",
            confidence=0.8,
        )
        with self.assertRaises(ValidationError):
            Formula(populist=True, populism_analysis="x", populism_us=[element])
        with self.assertRaises(ValidationError):
            Formula(populist=True, populism_analysis="x", populism_frontier=[element])

    def test_populist_true_with_both_sides_is_valid(self) -> None:
        PopulismElement, Formula = self._formula()
        formula = Formula(
            populist=True, populism_analysis="both sides evidenced",
            populism_us=[PopulismElement(
                populism_element="us", evidence_quote="us quote", confidence=0.8)],
            populism_frontier=[PopulismElement(
                populism_element="elite", evidence_quote="elite", confidence=0.8)],
        )
        self.assertTrue(formula.populist)

    def test_populist_false_requires_reason_and_empty_sides(self) -> None:
        _, Formula = self._formula()
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


def _iref(obj_id: str, label: str) -> "object":
    from laclaugpt_interchange import MemoryRef
    return MemoryRef(obj_id=obj_id, label=label, kind="signifier", raw=label)


class InterchangePopulismInvariant(unittest.TestCase):
    """INV_POPULISM at the interchange schema level (issue #50).

    The prompt-stage validator is not enough: the interchange file is what
    4CAT/DNA/INCEpTION actually consume, so populist=true must be invalid
    there too without both a Us and a Frontier side.
    """

    def test_populist_true_without_both_sides_is_invalid(self) -> None:
        from laclaugpt_interchange import DocumentAnnotation
        for kwargs in ({"us": [], "frontier": []},
                       {"us": [_iref("S001", "us")], "frontier": []},
                       {"us": [], "frontier": [_iref("S002", "elite")]}):
            with self.assertRaises(ValidationError):
                DocumentAnnotation(document_id="doc::1", populist=True, **kwargs)
            with self.assertRaises(ValidationError):
                DocumentAnnotation.model_validate({
                    "document_id": "doc::1", "populist": True, **kwargs})

    def test_populist_true_with_both_sides_round_trips(self) -> None:
        from laclaugpt_interchange import DocumentAnnotation, from_jsonl, to_jsonl
        ann = DocumentAnnotation(document_id="doc::1", populist=True,
                                 us=[_iref("S001", "us")],
                                 frontier=[_iref("S002", "elite")])
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "ann.jsonl")
            to_jsonl([ann], path)
            parsed = from_jsonl(path)[0]
        self.assertTrue(parsed.populist)
        self.assertEqual(parsed.us[0].obj_id, "S001")


class PopulismClaimStatusInvariant(unittest.TestCase):
    """INV_CONTEXT (issue #50): Us/Frontier elements carry claim_status so a
    quoted/reported/parodied/rejected articulation is never published as the
    author's asserted position."""

    def test_populism_element_schema_accepts_and_restricts_claim_status(self) -> None:
        PopulismElement, Formula = populism_prompt.pydantic_models()
        element = PopulismElement(
            populism_element="us", evidence_quote="quote", confidence=0.5,
            claim_status="quoted")
        self.assertEqual(element.claim_status, "quoted")
        with self.assertRaises(ValidationError):
            PopulismElement(populism_element="us", evidence_quote="q",
                            confidence=0.5, claim_status="shouted")
        # abstention validator still applies with the new field present
        with self.assertRaises(ValidationError):
            Formula(populist=True, populism_analysis="x",
                    populism_us=[element])

    def test_interchange_propagates_claim_status(self) -> None:
        from laclaugpt_interchange import (
            PopulismElementAssessment, from_memory_results)
        self.assertIn("claim_status", PopulismElementAssessment.model_fields)
        ann = from_memory_results(
            "doc::1", platform="synthetic",
            populism={
                "populist": True,
                "populism_us": [{"obj_id": "S001", "label": "us",
                                 "claim_status": "quoted"}],
                "populism_frontier": [{"obj_id": "S002", "label": "elite"}],
            },
        )
        us_element = next(e for e in ann.populism_elements if e.side == "us")
        self.assertEqual(us_element.claim_status, "quoted")
        frontier = next(e for e in ann.populism_elements if e.side == "frontier")
        self.assertEqual(frontier.claim_status, "asserted")


class DiscourseAbstentionInvariant(unittest.TestCase):
    """INV_ABSTAIN (issue #50): the discourse stage's applicability signal is
    published, so a 'not applicable' document is distinguishable from one with
    legitimately empty codings."""

    def test_annotation_carries_and_round_trips_applicability(self) -> None:
        from laclaugpt_interchange import DocumentAnnotation, from_jsonl, to_jsonl
        ann = DocumentAnnotation(document_id="doc::1",
                                 discourse_applicable=False,
                                 discourse_applicability_reason="not political discourse")
        self.assertIs(ann.discourse_applicable, False)
        self.assertIn("discourse_applicable", DocumentAnnotation.model_fields)
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "ann.jsonl")
            to_jsonl([ann], path)
            parsed = from_jsonl(path)[0]
        self.assertIs(parsed.discourse_applicable, False)
        self.assertEqual(parsed.discourse_applicability_reason,
                         "not political discourse")
        # default state stays None (no forced abstention)
        self.assertIsNone(DocumentAnnotation(document_id="doc::2").discourse_applicable)


class AttributionLiftInvariant(unittest.TestCase):
    """INV_CONTEXT (issue #50): interchange_to_v2 maps claim_status onto the
    canonical AttributionType instead of flattening everything to 'unclear'."""

    def _corpus(self, claim_status: str):
        import json
        from laclaugpt.adapters.interchange import interchange_to_v2
        ann = {
            "schema_version": SCHEMA_VERSION, "document_id": "doc::1",
            "source_platform": "synthetic", "summary": "the quote",
            "articulations": [{
                "signifier": {"obj_id": "S001", "label": "freedom",
                              "kind": "signifier", "raw": "freedom"},
                "related_to": [{"obj_id": "S002", "label": "chain",
                                "kind": "signifier", "raw": "chain"}],
                "relation": "equivalence", "evidence": "the quote",
                "claim_status": claim_status, "confidence": 0.5,
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ann.jsonl"
            path.write_text(json.dumps(ann) + "\n", encoding="utf-8")
            return interchange_to_v2(str(path))

    def test_claim_status_maps_to_attribution(self) -> None:
        from laclaugpt.model import AttributionType
        self.assertEqual(self._corpus("asserted").statements[0].attribution_type,
                         AttributionType.AUTHOR)
        self.assertEqual(self._corpus("quoted").statements[0].attribution_type,
                         AttributionType.QUOTED)
        self.assertEqual(self._corpus("reported").statements[0].attribution_type,
                         AttributionType.REPORTED)
        self.assertEqual(self._corpus("parodied").statements[0].attribution_type,
                         AttributionType.IRONIC)
        # rejected/uncertain conservatively stay non-author (never AUTHOR)
        for status in ("rejected", "uncertain", "unknown-value"):
            self.assertEqual(self._corpus(status).statements[0].attribution_type,
                             AttributionType.UNCLEAR)


class InceptionMergePopulismCoherenceInvariant(unittest.TestCase):
    """INV_POPULISM (issue #50): human INCEpTION corrections re-derive the
    Formula of Populism instead of exporting contradictory states."""

    def test_human_us_and_frontier_spans_upgrade_abstention(self) -> None:
        from inception_adapter import merge_inception_corrections
        from laclaugpt_interchange import (
            DocumentAnnotation, PopulismElementAssessment, from_jsonl)
        base = DocumentAnnotation(
            document_id="doc::1", populist=False,
            non_populist_reason="no frontier",
            populism_elements=[PopulismElementAssessment(
                element=_iref("S001", "us"), side="us",
                evidence="us quote", evidence_verified=True, confidence=0.9,
            )])
        with tempfile.TemporaryDirectory() as tmp:
            src = str(Path(tmp) / "in.jsonl")
            out = str(Path(tmp) / "out.jsonl")
            to_jsonl([base], src)
            counts = merge_inception_corrections(src, [{
                "document_id": "doc::1",
                "span": {"obj_id": "S002", "label": "elite",
                         "covered_text": "the elites", "side": "frontier",
                         "affect": "", "evidence": "elite quote",
                         "confidence": 0.9, "nodal_candidate": False,
                         "empty_candidate": False},
            }], out)
            merged = from_jsonl(out)[0]
        self.assertEqual(counts["new_elements"], 1)
        self.assertTrue(merged.populist)
        self.assertEqual(merged.non_populist_reason, "")
        self.assertEqual([r.obj_id for r in merged.us], ["S001"])
        self.assertEqual([r.obj_id for r in merged.frontier], ["S002"])

    def test_demoted_populist_true_never_publishes_invalid_state(self) -> None:
        from inception_adapter import merge_inception_corrections
        from laclaugpt_interchange import (
            DocumentAnnotation, PopulismElementAssessment)
        base = DocumentAnnotation(
            document_id="doc::2", populist=True,
            us=[_iref("S001", "us")], frontier=[_iref("S002", "elite")],
            populism_elements=[
                PopulismElementAssessment(element=_iref("S001", "us"),
                                          side="us", evidence="q", confidence=0.9),
                PopulismElementAssessment(element=_iref("S002", "elite"),
                                          side="frontier", evidence="q", confidence=0.9),
            ])
        with tempfile.TemporaryDirectory() as tmp:
            src = str(Path(tmp) / "in.jsonl")
            out = str(Path(tmp) / "out.jsonl")
            to_jsonl([base], src)
            merge_inception_corrections(src, [{
                "document_id": "doc::2",
                "span": {"obj_id": "S001", "label": "us",
                         "covered_text": "us", "side": "frontier",
                         "affect": "", "evidence": "q", "confidence": 0.9,
                         "nodal_candidate": False, "empty_candidate": False},
            }], out)
            merged = from_jsonl(out)[0]
        self.assertFalse(merged.populist)
        self.assertTrue(merged.non_populist_reason)
        self.assertEqual(merged.us, [])
        self.assertEqual(merged.frontier, [])


class DiscourseMembershipAndSentimentProvenanceInvariant(unittest.TestCase):
    """INV_RELATIONAL/INV_EVIDENCE (issue #50): formation candidates do not
    fabricate signifier membership, and sentiment readings record the model
    that actually produced the postprocess stage."""

    def _run(self):
        from pathlib import Path
        import tempfile
        from run_config import RunConfig, SourceSpec
        tmp = Path(tempfile.mkdtemp())
        return RunConfig(
            run_id="run-issue-50", analysis_profile="ai26:test", arena_id="test",
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

    def test_discourse_candidates_carry_no_fabricated_membership(self) -> None:
        from pipeline import build_annotation
        ann = build_annotation(
            self._run(), {"platform": "synthetic", "id": "doc-1"}, "{}",
            {"formation_candidates": [
                {"obj_id": "F001", "label": "accelerationism", "kind": "formation",
                 "raw": "accelerationism", "supporting_features": [],
                 "counter_evidence": [], "evidence": "q", "confidence": 0.7}],
             "signifiers": [{"obj_id": "S009", "label": "freedom",
                             "kind": "signifier", "raw": "freedom",
                             "role": "nodal_candidate", "rationale": "r",
                             "evidence": "q", "confidence": 0.5,
                             "needs_corpus_validation": False}]},
            {}, {},
        )
        self.assertEqual(len(ann.discourses), 1)
        self.assertEqual(ann.discourses[0].elements, [])

    def test_sentiment_observation_records_actual_stage_model(self) -> None:
        from pipeline import build_annotation
        run = self._run()
        extracted = {"sentiment": [{"target": {
            "obj_id": "C001", "label": "EU", "kind": "target", "raw": "the EU"},
            "polarity": "negative"}]}
        ann = build_annotation(
            run, {"platform": "synthetic", "id": "doc-1"}, "{}", {}, extracted, {},
            stage_provenance={
                "summary": {"actual_model": "model-a", "actual_model_digest": "d"},
                "postprocess": {"actual_model": "model-b", "actual_model_digest": "e"},
            },
        )
        # Top-level model is honestly "mixed"; the sentiment reading itself
        # records the model that produced the postprocess stage.
        self.assertEqual(ann.model, "mixed")
        self.assertEqual(ann.sentiment_observations[0].model, "model-b")


if __name__ == "__main__":
    unittest.main()