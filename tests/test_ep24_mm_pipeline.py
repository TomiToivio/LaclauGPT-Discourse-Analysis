"""Issue #73 sample: offline tests for the mm-pipeline wiring."""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ep24_asr
import ep24_fetch
import ep24_mm_pipeline


def _manifest(path: Path, rows: list[tuple[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["document_id", "allas_url", "row_count"])
        for nid, url in rows:
            w.writerow([nid, url, 1])


def _legacy(path: Path, ids: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "new_id", "country", "political_preference", "corrected_date",
            "account_type", "source_type"])
        w.writeheader()
        for nid in ids:
            w.writerow({"new_id": nid, "country": "Finland",
                        "political_preference": "", "corrected_date": "",
                        "account_type": "Synthetic", "source_type": "Tiktok"})


class PathsTests(unittest.TestCase):
    def test_paths_use_roots(self) -> None:
        p = ep24_mm_pipeline.paths("finland")
        self.assertEqual(p["repo_root"], Path(ep24_mm_pipeline.REPO_ROOT))
        self.assertIn("finland_sample20.csv", str(p["manifest"]))
        self.assertIn("annotations", str(p["annotations"]))


class RunCountryTests(unittest.TestCase):
    def test_full_chain_with_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mp = root / "ep24" / "csv" / "finland_sample20.csv"
            mp.parent.mkdir(parents=True, exist_ok=True)
            _manifest(mp, [("ID1", "https://a3s.fi/x/1.mp4")])
            _legacy(root / "ep24" / "csv" / "ep24_finland.csv", ["ID1"])

            class _Resp:
                status = 200
                def __init__(self): self._d = [b"vid", b""]
                def read(self, n): return self._d.pop(0) if self._d else b""
                def __enter__(self): return self
                def __exit__(self, *a): return False

            def fake_ocr(video_path, **kw):
                return "@kokoomus\nKokoomus\n34 tykkäystä"

            fake_whisper = ep24_asr_tests_fake_model()

            def fake_transcribe(manifest, videos_dir, out_path, **kw):
                out = Path(out_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                rec = {"document_id": "ID1", "allas_url": "https://a3s.fi/x/1.mp4",
                       "transcript": "kokoomus puheenvuoro", "language": "fi"}
                out.write_text(json.dumps(rec) + "\n", encoding="utf-8")
                return 1

            with patch.object(ep24_fetch.urllib.request, "urlopen", return_value=_Resp()):
                with patch.object(ep24_mm_pipeline.ep24_asr, "transcribe_manifest", side_effect=fake_transcribe):
                    with patch.object(ep24_mm_pipeline, "ocr_video_frames", side_effect=fake_ocr):
                        with patch.object(ep24_mm_pipeline, "_load_jsonl", side_effect=[[
                            {"document_id": "ID1", "allas_url": "https://a3s.fi/x/1.mp4", "transcript": "x"}
                        ]]):
                            with patch("pipeline.run_pipeline", return_value=[]):
                                status = ep24_mm_pipeline.run_country(
                                    "finland", data_root=str(root), repo_root=str(root),
                                    model=fake_whisper, ocr_fn=fake_ocr)
            self.assertEqual(status["fetched"], 1)
            self.assertEqual(status["canonical_rows"], 1)


def ep24_asr_tests_fake_model():
    class _Info:
        language = "fi"
        language_probability = 0.97
        duration = 10.0
    class _Seg:
        text = "x"
    class _M:
        model_size_or_path = "large-v3"
        def transcribe(self, path, **kw):
            return [_Seg()], _Info()
    return _M()


def canon_module():
    import pipeline
    return pipeline


class SlurmScriptTests(unittest.TestCase):
    def test_sample_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            scripts = ep24_mm_pipeline.write_slurm_scripts(tmp)
            self.assertEqual({s.name for s in scripts},
                             {"ep24_mm_finland.sh", "ep24_mm_poland.sh"})
            text = scripts[0].read_text(encoding="utf-8")
            self.assertIn("ep24_mm_pipeline.py --country", text)
            self.assertIn("LACLAUGPT_REPO_ROOT", text)
            self.assertIn("LACLAUGPT_DATA_DIR", text)
            self.assertNotIn("/users/", text)
            self.assertNotIn("/scratch/project_", text)


if __name__ == "__main__":
    unittest.main()
