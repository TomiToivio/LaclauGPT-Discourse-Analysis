"""Issue #73 phase 1.2: EP24 ASR stage tests (offline, mock WhisperModel)."""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import ep24_asr
import ep24_fetch


class FakeInfo:
    def __init__(self):
        self.language = "fi"
        self.language_probability = 0.97
        self.duration = 12.5


class FakeSegment:
    def __init__(self, text):
        self.text = text


class FakeWhisper:
    model_size_or_path = "large-v3"

    def __init__(self, segments, info=None):
        self._segments = segments
        self.info = info or FakeInfo()
        self.last_kwargs = None

    def transcribe(self, path, **kwargs):
        self.last_kwargs = kwargs
        return self._segments, self.info


class _Manifest:
    @staticmethod
    def write(path: Path, rows: list[tuple[str, str]]) -> None:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["document_id", "allas_url", "row_count"])
            for nid, url in rows:
                w.writerow([nid, url, 1])


class TranscribeTests(unittest.TestCase):
    def test_vad_filter_is_on(self) -> None:
        fake = FakeWhisper([FakeSegment("Hei vaalifanit"), FakeSegment("")])
        ep24_asr.transcribe_video("/tmp/whatever.mp4", model=fake)
        self.assertTrue(fake.last_kwargs["vad_filter"])

    def test_empty_segments_do_not_break_join(self) -> None:
        fake = FakeWhisper([FakeSegment("Yksi"), FakeSegment("   "), FakeSegment("kaksi")])
        result = ep24_asr.transcribe_video("/tmp/x.mp4", model=fake)
        self.assertEqual(result["transcript"], "Yksi kaksi")
        self.assertEqual(result["language"], "fi")
        self.assertEqual(result["duration"], 12.5)

    def test_model_provenance_recorded(self) -> None:
        fake = FakeWhisper([FakeSegment("ok")])
        result = ep24_asr.transcribe_video("/tmp/x.mp4", model=fake)
        self.assertIn("transcript", result)


class ManifestTranscribeTests(unittest.TestCase):
    def _setup_videos(self, tmp: str, urls: list[str]) -> Path:
        videos = Path(tmp) / "videos"
        videos.mkdir(exist_ok=True)
        for url in urls:
            dest = ep24_fetch._dest_for(videos, url)
            dest.write_bytes(b"fake video bytes")
        return videos

    def test_transcribe_manifest_writes_jsonl_and_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp = Path(tmp) / "finland_manifest.csv"
            _Manifest.write(mp, [("ID1", "https://a3s.fi/x/1.mp4"),
                                 ("ID2", "https://a3s.fi/x/2.mp4")])
            videos = self._setup_videos(tmp, ["https://a3s.fi/x/1.mp4",
                                              "https://a3s.fi/x/2.mp4"])
            out = Path(tmp) / "out" / "finland_transcripts.jsonl"
            fake = FakeWhisper([FakeSegment("transkriptio")])
            n = ep24_asr.transcribe_manifest(mp, videos, out, model=fake)
            self.assertEqual(n, 2)
            records = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
            self.assertEqual({r["document_id"] for r in records}, {"ID1", "ID2"})
            self.assertEqual(records[0]["transcript_version"], ep24_asr.TRANSCRIPT_VERSION)
            self.assertTrue(records[0]["vad_filter"])
            self.assertEqual(ep24_asr.transcribe_manifest(mp, videos, out, model=fake), 0)

    def test_missing_video_raises_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp = Path(tmp) / "poland_manifest.csv"
            _Manifest.write(mp, [("PL1", "https://a3s.fi/y/9.mp4")])
            videos = Path(tmp) / "videos"
            videos.mkdir(exist_ok=True)
            fake = FakeWhisper([FakeSegment("x")])
            with self.assertRaises(FileNotFoundError):
                ep24_asr.transcribe_manifest(mp, videos, Path(tmp) / "o.jsonl", model=fake)


class SlurmScriptTests(unittest.TestCase):
    def test_script_uses_runtime_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = ep24_asr.write_slurm_script(Path(tmp) / "asr_fi.sh", "finland")
            text = p.read_text(encoding="utf-8")
            self.assertIn("LACLAUGPT_REPO_ROOT", text)
            self.assertIn("LACLAUGPT_DATA_DIR", text)
            self.assertIn("finland_manifest.csv", text)
            self.assertIn("LACLAUGPT_MEMORY_DIR=$DATA_ROOT/memory", text)
            self.assertIn("#SBATCH --gpus=1", text)
            self.assertNotIn("/users/", text)
            self.assertNotIn("/scratch/project_", text)


if __name__ == "__main__":
    unittest.main()
