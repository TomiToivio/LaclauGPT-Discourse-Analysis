"""Issue #73: full EP24 pipeline tests (offline — mock LLM/whisper)."""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ep24_fetch
import ep24_pipeline


def _write_manifest(path: Path, rows: list[tuple[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["document_id", "allas_url", "row_count"])
        for nid, url in rows:
            w.writerow([nid, url, 1])


def _write_legacy_csv(path: Path, rows: list[dict]) -> None:
    cols = ["new_id", "country", "political_preference", "corrected_date",
            "account_type", "source_type"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


class _FakeInfo:
    language = "fi"
    language_probability = 0.97
    duration = 10.0


class _FakeSeg:
    def __init__(self, text):
        self.text = text


class _FakeWhisper:
    model_size_or_path = "large-v3"

    def transcribe(self, path, **kwargs):
        return [_FakeSeg("kokoomus on tehnyt hyvää työtä"), _FakeSeg("")], _FakeInfo()


class BuildCanonicalTests(unittest.TestCase):

    def test_join_transcripts_with_legacy_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp = Path(tmp) / "finland_manifest.csv"
            _write_manifest(mp, [("ID1", "https://a3s.fi/x/1.mp4")])
            legacy = Path(tmp) / "ep24_finland.csv"
            _write_legacy_csv(legacy, [{
                "new_id": "ID1", "country": "Finland",
                "political_preference": "Centre right",
                "corrected_date": "2024-05-21",
                "account_type": "Synthetic", "source_type": "Instagram",
            }])
            transcripts = Path(tmp) / "t.jsonl"
            rec = {"document_id": "ID1", "transcript": "kokoomus hyvää",
                   "language": "fi", "screen_ocr": "@kokoomus\nKokoomus\n34 tykkäystä"}
            transcripts.write_text(json.dumps(rec), encoding="utf-8")
            out = Path(tmp) / "canonical.csv"
            n = ep24_pipeline.build_canonical_csv(mp, transcripts, legacy, out)
            self.assertEqual(n, 1)
            rows = list(csv.DictReader(open(out, encoding="utf-8")))
            row = rows[0]
            self.assertEqual(row["document_id"], "ID1")
            self.assertEqual(row["transcript"], "kokoomus hyvää")
            self.assertEqual(row["political_preference"], "Centre right")
            self.assertEqual(row["screen_handle"], "kokoomus")
            sm = json.loads(row["screen_metadata_json"])
            self.assertEqual(sm["screen_metadata"]["review_status"], "proposed")

    def test_no_legacy_model_output_columns_copied(self) -> None:
        # legacy model outputs (formula_of_populism_* etc.) must never enter
        # the canonical CSV — they are old-run outputs, not new-prompt input.
        with tempfile.TemporaryDirectory() as tmp:
            mp = Path(tmp) / "m.csv"
            _write_manifest(mp, [("ID1", "https://a3s.fi/x/1.mp4")])
            legacy = Path(tmp) / "ep24_finland.csv"
            cols = ["new_id", "country", "political_preference", "corrected_date",
                    "account_type", "source_type",
                    "formula_of_populism_analysis", "whisper_transcript"]
            with open(legacy, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=cols)
                w.writeheader()
                w.writerow({"new_id": "ID1", "country": "Finland",
                            "political_preference": "", "corrected_date": "",
                            "account_type": "Synthetic", "source_type": "Tiktok",
                            "formula_of_populism_analysis": "OLD RUN OUTPUT",
                            "whisper_transcript": "OLD TRANSCRIPT"})
            transcripts = Path(tmp) / "t.jsonl"
            transcripts.write_text(json.dumps(
                {"document_id": "ID1", "transcript": "fresh", "language": "fi"}),
                encoding="utf-8")
            out = Path(tmp) / "c.csv"
            ep24_pipeline.build_canonical_csv(mp, transcripts, legacy, out)
            row = list(csv.DictReader(open(out, encoding="utf-8")))[0]
            self.assertNotIn("formula_of_populism_analysis", row)
            self.assertNotIn("whisper_transcript", row)
            self.assertEqual(row["transcript"], "fresh")

    def test_not_yet_transcribed_rows_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp = Path(tmp) / "m.csv"
            _write_manifest(mp, [("ID1", "https://a3s.fi/x/1.mp4"),
                                 ("ID2", "https://a3s.fi/x/2.mp4")])
            legacy = Path(tmp) / "l.csv"
            _write_legacy_csv(legacy, [
                {"new_id": "ID1", "country": "Finland", "political_preference": "",
                 "corrected_date": "", "account_type": "", "source_type": ""},
                {"new_id": "ID2", "country": "Finland", "political_preference": "",
                 "corrected_date": "", "account_type": "", "source_type": ""}])
            transcripts = Path(tmp) / "t.jsonl"
            transcripts.write_text(json.dumps(
                {"document_id": "ID1", "transcript": "ok", "language": "fi"}),
                encoding="utf-8")
            out = Path(tmp) / "c.csv"
            n = ep24_pipeline.build_canonical_csv(mp, transcripts, legacy, out)
            self.assertEqual(n, 1, "resume: only transcribed rows enter")


class RunCountryTests(unittest.TestCase):

    def test_dry_run_counts_without_llm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mp = root / "ep24" / "csv" / "finland_manifest.csv"
            mp.parent.mkdir(parents=True, exist_ok=True)
            _write_manifest(mp, [("ID1", "https://a3s.fi/x/1.mp4")])
            # legacy identity CSV lives in the same phase-0 dir on Roihu
            legacy = root / "ep24" / "csv" / "ep24_finland.csv"
            _write_legacy_csv(legacy, [{
                "new_id": "ID1", "country": "Finland",
                "political_preference": "Centre right",
                "corrected_date": "2024-05-21",
                "account_type": "Synthetic", "source_type": "Instagram",
            }])

            class _Resp:
                status = 200
                def __init__(self):
                    self._d = [b"vid", b""]
                def read(self, n):
                    return self._d.pop(0) if self._d else b""
                def __enter__(self): return self
                def __exit__(self, *a): return False

            def fake_transcribe(manifest, videos_dir, out_path, **kw):
                out = Path(out_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(
                    {"document_id": "ID1", "transcript": "fresh",
                     "language": "fi", "screen_ocr": "@kokoomus\nKokoomus"}),
                    encoding="utf-8")
                return 1

            with patch.object(ep24_fetch.urllib.request, "urlopen",
                              return_value=_Resp()):
                with patch.object(ep24_pipeline.ep24_asr, "transcribe_manifest",
                                  side_effect=fake_transcribe):
                    status = ep24_pipeline.run_country(
                        "finland", data_root=str(root), repo_root=str(root),
                        dry_run=True)
            self.assertEqual(status["fetched"], 1)
            self.assertEqual(status["transcribed"], 1)
            self.assertEqual(status["canonical_rows"], 1)
            self.assertTrue(status["dry_run"])


class SlurmScriptTests(unittest.TestCase):

    def test_scripts_for_both_countries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scripts = ep24_pipeline.write_slurm_scripts(tmp)
            self.assertEqual(len(scripts), 2)
            for s in scripts:
                text = s.read_text(encoding="utf-8")
                self.assertIn("LACLAUGPT_REPO_ROOT", text)
                self.assertIn("LACLAUGPT_DATA_DIR", text)
                self.assertIn("ep24_pipeline.py --country", text)
                self.assertIn("LACLAUGPT_MEMORY_DIR", text)
            names = {s.name for s in scripts}
            self.assertEqual(names, {"ep24_full_finland.sh", "ep24_full_poland.sh"})


if __name__ == "__main__":
    unittest.main()