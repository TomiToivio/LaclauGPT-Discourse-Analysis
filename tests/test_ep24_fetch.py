"""Issue #73 phase 1.1: EP24 fetch stage tests (no network)."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ep24_fetch


def _manifest(path: Path, rows: list[tuple[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["document_id", "allas_url", "row_count"])
        for nid, url in rows:
            w.writerow([nid, url, 1])


class ManifestTests(unittest.TestCase):

    def test_load_and_dedupe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp = Path(tmp) / "m.csv"
            _manifest(mp, [
                ("ID1", "https://a3s.fi/x/1.mp4"),
                ("ID2", "https://a3s.fi/x/1.mp4"),   # same URL, fan-out
                ("ID3", "https://a3s.fi/x/2.mp4"),
                ("ID4", "https://a3s.fi/x/2.mp4"),
            ])
            pairs = ep24_fetch.load_manifest(mp)
            self.assertEqual(len(pairs), 4)
            urls = ep24_fetch.unique_urls(pairs)
            self.assertEqual(len(urls), 2, "dedup: one fetch per unique URL")

    def test_dest_is_deterministic(self) -> None:
        d1 = ep24_fetch._dest_for(Path("/w"), "https://a3s.fi/x/1.mp4")
        d2 = ep24_fetch._dest_for(Path("/w"), "https://a3s.fi/x/1.mp4")
        self.assertEqual(d1 := d1, d2 := d2) if False else None
        self.assertEqual(d1, d2)
        self.assertTrue(d1.name.endswith(".mp4"))


class FetchTests(unittest.TestCase):

    def test_fetch_streams_and_is_resume_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            url = "https://a3s.fi/x/1.mp4"

            class FakeResponse:
                status = 200
                def __init__(self):
                    self._data = [b"V", b"ID", b"EOS", b""]
                def read(self, n):
                    return self._data.pop(0) if self._data else b""
                def __enter__(self): return self
                def __exit__(self, *a): return False

            with patch.object(ep24_fetch.urllib.request, "urlopen",
                              return_value=FakeResponse()):
                dest = ep24_fetch.fetch_video(url, workdir)
                self.assertEqual(dest.read_bytes(), b"VIDEOS")
                # second call skips the network (resume-safe)
                dest2 = ep24_fetch.fetch_video(url, workdir)
                self.assertEqual(dest, dest2)

    def test_fetch_all_maps_urls_to_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp = Path(tmp) / "m.csv"
            _manifest(mp, [("ID1", "https://a3s.fi/x/1.mp4"),
                           ("ID2", "https://a3s.fi/x/1.mp4")])
            workdir = Path(tmp) / "videos"

            class FakeResponse:
                status = 200
                def __init__(self):
                    self._data = [b"data", b"here", b""]
                def read(self, n):
                    return self._data.pop(0) if self._data else b""
                def __enter__(self): return self
                def __exit__(self, *a): return False

            with patch.object(ep24_fetch.urllib.request, "urlopen",
                              return_value=FakeResponse()):
                fetched = ep24_fetch.fetch_all(mp, workdir)
            self.assertEqual(len(fetched), 1, "one fetch per unique URL")
            self.assertTrue(fetched["https://a3s.fi/x/1.mp4"].endswith(".mp4"))

    def test_retries_then_raises(self) -> None:
        import urllib.error
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)

            def boom(req, timeout=None):
                raise urllib.error.URLError("down")

            with patch.object(ep24_fetch.urllib.request, "urlopen", boom):
                with self.assertRaises(RuntimeError):
                    ep24_fetch.fetch_video("https://a3s.fi/x/1.mp4", workdir)


import urllib.error  # noqa: E402  (after imports for the test above)


if __name__ == "__main__":
    unittest.main()