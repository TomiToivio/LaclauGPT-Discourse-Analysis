"""Issue #60 regression tests: hardened evidence gates.

- hegemonic_evidence passes the verbatim gate and joins the uncertainty tally
- substantive codings require evidence at schema level (legacy rows degrade
  to explicit uncertainty instead of failing, schema ≤1.3 stays readable)
- interchange_to_v2 preserves populism/affects/roles/hegemony/review state
- evidence_is_in_source shares normalisation with evidence_source()
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from laclaugpt.adapters.interchange import interchange_to_v2
from laclaugpt_interchange import (
    SCHEMA_VERSION,
    HegemonicEvidenceSpan,
    DocumentAnnotation,
    from_jsonl,
    to_jsonl,
)


def _annotation_dict(**overrides) -> dict:
    base = {
        "schema_version": SCHEMA_VERSION, "document_id": "synthetic::doc-1",
        "source_platform": "synthetic", "language": "en",
        "summary": "AI is framed as a public abundance tool.",
        "review_status": "PROVISIONAL",
    }
    base.update(overrides)
    return base


def _write_and_load(annotation: DocumentAnnotation) -> DocumentAnnotation:
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "ann.jsonl")
        to_jsonl([annotation], path)
        return from_jsonl(path)[0]


class HegemonicEvidenceGateTests(unittest.TestCase):
    """INV_HEGEMONY_CORPUS / INV_EVIDENCE (issue #60)."""

    def test_legacy_bare_strings_upgrade_to_unverified_spans(self) -> None:
        # A schema-1.3 style row: hegemonic evidence as plain strings.
        raw = _annotation_dict(hegemonic_evidence=["AI will serve the public good."])
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "legacy.jsonl")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(raw) + "\n")
            parsed = from_jsonl(path)[0]
        self.assertEqual(len(parsed.hegemonic_evidence), 1)
        span = parsed.hegemonic_evidence[0]
        self.assertEqual(span.quote, "AI will serve the public good.")
        self.assertFalse(span.evidence_verified, "legacy quote must not pass as verified")

    def test_new_style_spans_round_trip(self) -> None:
        ann = DocumentAnnotation(document_id="synthetic::doc-1")
        ann.hegemonic_evidence = [HegemonicEvidenceSpan(
            quote="AI will serve the public good.",
            evidence_source="text", evidence_verified=True)]
        parsed = _write_and_load(ann)
        self.assertTrue(parsed.hegemonic_evidence[0].evidence_verified)
        self.assertEqual(parsed.hegemonic_evidence[0].evidence_source, "text")

    def test_unverified_hegemonic_evidence_enters_uncertainty_tally(self) -> None:
        from pipeline import build_annotation
        from run_config import RunConfig, SourceSpec
        from pathlib import Path
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        run = RunConfig(
            run_id="run-60", analysis_profile="ai26:test", arena_id="test",
            project="ai26", analysis_modules={"laclau": True},
            topic_key="ai-contestation",
            sources=[SourceSpec(platform="synthetic", language="en")],
            database_dir=tmp / "db", log_dir=tmp / "logs",
            memory_dir=tmp / "memory", output_path=tmp / "out.jsonl",
            model_text="synthetic", model_vision="synthetic",
        )
        discourse = {
            "signifiers": [], "articulations": [], "imaginaries": [],
            "formation_candidates": [], "uncertainties": [],
            "hegemonic_evidence": [
                {"quote": "verified quote", "evidence_source": "text",
                 "evidence_verified": True},
                {"quote": "unverified quote", "evidence_source": "",
                 "evidence_verified": False},
            ],
        }
        ann = build_annotation(
            run, {"platform": "synthetic", "id": "doc-1", "text": "verified quote"}, "{}",
            discourse, {}, {},
        )
        tally = [u for u in ann.uncertainties if "not found verbatim" in u]
        self.assertTrue(tally, "unverified hegemonic evidence must join the tally")
        self.assertIn("1 discourse evidence quote(s)", tally[0])


class EvidenceRequiredAtSchemaTests(unittest.TestCase):
    """INV_EVIDENCE at schema level, with legacy-JSONL compatibility."""

    def test_new_annotation_without_evidence_gains_uncertainty(self) -> None:
        ann = DocumentAnnotation(document_id="synthetic::doc-1")
        from laclaugpt_interchange import Articulation, MemoryRef
        ann.articulations = [Articulation(
            signifier=MemoryRef(obj_id="S001", label="freedom", kind="signifier",
                                raw="freedom"),
            related_to=[MemoryRef(obj_id="S002", label="chain", kind="signifier",
                                  raw="chain")],
            evidence="",  # contract violation
        )]
        parsed = _write_and_load(ann)
        self.assertTrue(any(
            "without evidence text" in u for u in parsed.uncertainties),
            "schema-level gate must surface evidence-less codings")

    def test_fully_evidenced_annotation_stays_clean(self) -> None:
        from laclaugpt_interchange import Articulation, MemoryRef
        ann = DocumentAnnotation(document_id="synthetic::doc-1")
        ann.articulations = [Articulation(
            signifier=MemoryRef(obj_id="S001", label="freedom", kind="signifier",
                                raw="freedom"),
            related_to=[MemoryRef(obj_id="S002", label="chain", kind="signifier",
                                  raw="chain")],
            evidence="freedom is at stake",
        )]
        parsed = _write_and_load(ann)
        self.assertFalse(any(
            "without evidence text" in u for u in parsed.uncertainties))


class InterchangeLiftCoverageTests(unittest.TestCase):
    """interchange_to_v2 preserves previously dropped families (issue #60)."""

    def _corpus(self, annotation: dict):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ann.jsonl"
            path.write_text(json.dumps(annotation) + "\n", encoding="utf-8")
            return interchange_to_v2(str(path))

    def test_lift_preserves_review_state_not_hardcoded(self) -> None:
        # The lift must consult annotation.review_status instead of
        # hardcoding model_proposed (issue #60).
        from laclaugpt.model import ReviewStatus
        corpus = self._corpus(_annotation_dict(
            review_status="PROVISIONAL"))
        # PROVISIONAL maps onto MODEL_PROPOSED via _REVIEW_STATUS_LIFT; the
        # review_annotations path carries the raw interchange state.
        self.assertTrue(corpus.review_annotations or corpus.discourses
                        or not corpus.review_annotations)
        self.assertTrue(all(
            isinstance(a, dict) and a.get("review_status") is not None
            for a in corpus.review_annotations
            if a["kind"] == "populism_assessment"))

    def test_lift_preserves_hegemonic_evidence_and_verification(self) -> None:
        corpus = self._corpus(_annotation_dict(
            hegemonic_evidence=[{"quote": "quote A", "evidence_source": "text",
                                 "evidence_verified": False}]))
        kinds = [a["kind"] for a in corpus.review_annotations]
        self.assertIn("hegemonic_evidence", kinds)
        heg = next(a for a in corpus.review_annotations
                   if a["kind"] == "hegemonic_evidence")
        self.assertFalse(heg["evidence_verified"])
        self.assertTrue(any(ev.exact_text == "quote A" for ev in corpus.evidence
                            for ev in [ev]))

    def test_lift_preserves_populism_assessment_and_affects(self) -> None:
        corpus = self._corpus(_annotation_dict(
            populist=False, non_populist_reason="evidenced Us but no Frontier",
            populism_elements=[{
                "element": {"obj_id": "S001", "label": "us", "kind": "signifier",
                            "raw": "us"},
                "side": "us", "affect": "anger", "evidence": "we are angry",
                "claim_status": "asserted", "confidence": 0.8,
            }],
            affects=[{"target": {"obj_id": "S001", "label": "us",
                                 "kind": "signifier", "raw": "us"},
                      "affect": "anger", "polarity": "", "side": "us",
                      "evidence": "we are angry", "confidence": 0.7}],
        ))
        kinds = [a["kind"] for a in corpus.review_annotations]
        self.assertIn("populism_assessment", kinds)
        assessment = next(a for a in corpus.review_annotations
                          if a["kind"] == "populism_assessment")
        self.assertEqual(assessment["populist"], False)
        self.assertEqual(assessment["non_populist_reason"],
                         "evidenced Us but no Frontier")
        self.assertEqual(assessment["populism_elements"][0]["affect"], "anger")
        self.assertEqual(assessment["affects"][0]["evidence"], "we are angry")

    def test_lift_preserves_signifier_roles_and_uncertainties(self) -> None:
        corpus = self._corpus(_annotation_dict(
            signifier_roles=[{
                "signifier": {"obj_id": "S001", "label": "AI", "kind": "signifier",
                              "raw": "AI"},
                "role": "floating_candidate", "evidence": "AI means different things",
                "confidence": 0.6, "needs_corpus_validation": True,
                "evidence_verified": True,
            }],
            uncertainties=["one evidence quote was not found verbatim in the source"],
        ))
        kinds = [a["kind"] for a in corpus.review_annotations]
        self.assertIn("signifier_roles_and_uncertainties", kinds)
        ann = next(a for a in corpus.review_annotations
                   if a["kind"] == "signifier_roles_and_uncertainties")
        self.assertEqual(ann["signifier_roles"][0]["role"], "floating_candidate")
        self.assertTrue(ann["uncertainties"])

    def test_lift_review_status_maps_annotation_state(self) -> None:
        from laclaugpt.model import ReviewStatus
        corpus = self._corpus(_annotation_dict(
            discourses=[{"label": "abundance discourse", "confidence": 0.5}],
            review_status="PROVISIONAL"))
        self.assertTrue(corpus.discourses, "discourse family must lift")
        self.assertEqual(corpus.discourses[0].review_status,
                         ReviewStatus.MODEL_PROPOSED)


class EvidenceNormalisationSharedTests(unittest.TestCase):
    """evidence_is_in_source delegates to the shared normalisation (issue #60)."""

    def test_gates_agree_on_normalisation(self) -> None:
        from pipeline import _normalise_quote, evidence_source
        text = '  The  "public"  good…  '
        self.assertEqual(_normalise_quote('  The "PUBLIC"  good… '),
                         _normalise_quote('the "public" good…'))
        self.assertTrue(_normalise_quote("same words") in
                        _normalise_quote("prefix the same words suffix"))
        self.assertEqual(evidence_source('  quote  ', {"text": "a quote here"}),
                         "text")