"""Issue #73: dual-format exports + relevance gate (mark-don't-drop).

- relevance: relevant | irrelevant (+ reason) — replaces the old
  dashboard's silent row drops; irrelevant rows stay queryable
- export_machine_csv: one flat row per document (legacy dashboard parity)
- write_human_report: markdown digest per document (legacy summary parity)
"""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from laclaugpt_interchange import DocumentAnnotation
from pipeline import (export_machine_csv, corpus_synthesis,
                      write_human_report)


def _ann(doc_id: str, **kw) -> DocumentAnnotation:
    kw.setdefault("document_id", doc_id)
    from laclaugpt_interchange import MemoryRef
    if kw.get("populist") is True and not kw.get("us"):
        kw["us"] = [MemoryRef(obj_id="U1", label="us", kind="signifier")]
        kw["frontier"] = [MemoryRef(obj_id="F1", label="frontier",
                                    kind="signifier")]
    return DocumentAnnotation(**kw)


class RelevanceGateTests(unittest.TestCase):

    def test_schema_defaults(self) -> None:
        ann = _ann("D1")
        self.assertIsNone(ann.relevance)
        self.assertEqual(ann.relevance_reason, "")

    def test_marked_irrelevant_stays_queryable(self) -> None:
        # mark-don't-drop: the annotation keeps everything it had.
        ann = _ann("D2", relevance="irrelevant",
                   relevance_reason="no political content",
                   summary="a cat video", populist=None)
        self.assertEqual(ann.relevance, "irrelevant")
        self.assertEqual(ann.summary, "a cat video")
        self.assertTrue(ann.requires_human_review is True)


class MachineCsvTests(unittest.TestCase):

    def test_one_row_per_document_with_relevance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.csv"
            export_machine_csv([
                _ann("D1", relevance="relevant", populist=True,
                     summary="s1", evidence_quotes=["q1"], run_id="r1"),
                _ann("D2", relevance="irrelevant",
                     relevance_reason="music only", populist=None),
            ], str(path))
            rows = list(csv.DictReader(open(path, encoding="utf-8")))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["relevance"], "relevant")
            self.assertEqual(rows[0]["populist"], "true")
            self.assertEqual(rows[0]["evidence_quotes"], "q1")
            self.assertEqual(rows[1]["relevance"], "irrelevant")
            self.assertEqual(rows[1]["relevance_reason"], "music only")
            self.assertEqual(rows[1]["populist"], "")


class HumanReportTests(unittest.TestCase):

    def test_report_has_sections_and_irrelevant_marked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.report.md"
            anns = [
                _ann("D1", relevance="relevant", populist=True,
                     summary="Kokoomus EU-vaalivideo",
                     populism_analysis="Us vs Frontier construction present",
                     evidence_quotes=["\"kokoomus mainittu\""],
                     uncertainties=["party affiliation unclear"]),
                _ann("D2", relevance="irrelevant",
                     relevance_reason="music only"),
            ]
            synthesis = {"documents": 2, "signifier_frequency": {},
                         "floating_candidates": [], "empty_candidates": [],
                         "nodal_candidates": []}
            write_human_report(anns, synthesis, str(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("1 retained, 1 marked irrelevant", text)
            self.assertIn("# LaclauGPT analysis report", text)
            self.assertIn("## D1", text)
            self.assertIn("## D2", text)
            self.assertIn("relevance: **irrelevant**", text)
            self.assertIn("music only", text)
            self.assertIn("Kokoomus EU-vaalivideo", text)
            self.assertIn('""kokoomus mainittu""', text)

    def test_corpus_synthesis_excludes_irrelevant_but_reports(self) -> None:
        relevant = _ann("D1", relevance="relevant")
        role_kw = {"signifier": {"obj_id": "S1", "label": "kela", "kind": "signifier"},
                   "role": "nodal_candidate", "rationale": "r",
                   "evidence": "e", "confidence": 0.9,
                   "evidence_verified": True}
        relevant.signifier_roles = [
            __import__("laclaugpt_interchange", fromlist=["SignifierRole"]
                       ).SignifierRole(**role_kw)]
        irrelevant = _ann("D2", relevance="irrelevant")
        irrelevant.signifier_roles = [
            __import__("laclaugpt_interchange", fromlist=["SignifierRole"]
                       ).SignifierRole(**{**role_kw,
                                          "signifier": {"obj_id": "S9",
                                                        "label": "musiikki",
                                                        "kind": "signifier"}})]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "c.json"
            synthesis = corpus_synthesis([relevant, irrelevant], out)
        self.assertNotIn("S9", json.dumps(synthesis["signifier_frequency"]))
        self.assertIn("S1", synthesis["signifier_frequency"])
        self.assertEqual(synthesis["documents_total"], 2)
        self.assertEqual(synthesis["documents_excluded_irrelevant"], 1)


if __name__ == "__main__":
    unittest.main()
