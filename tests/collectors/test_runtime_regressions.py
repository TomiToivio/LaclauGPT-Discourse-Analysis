"""Regressions for bugs found during the 2026-09 collector audit."""
from __future__ import annotations

import json
from pathlib import Path

from collector import normalize
from collector import run as runner
from collector.browser import _cdp_wall_timestamp
from collector.media import MediaBackend, MediaDownloader
from collector.store import Store

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_media_pass_reads_every_platform_jsonl(tmp_path):
    store = Store(tmp_path / "data")
    try:
        (store.normalized_dir / "tiktok.jsonl").write_text(
            json.dumps({"platform": "tiktok", "document_id": "tt-1"}) + "\n",
            encoding="utf-8",
        )
        (store.normalized_dir / "x.jsonl").write_text(
            json.dumps({"platform": "x", "document_id": "x-1"}) + "\n",
            encoding="utf-8",
        )
        records = runner._load_normalized_records(store)
        assert {record["document_id"] for record in records} == {"tt-1", "x-1"}
    finally:
        store.close()


class MemoryBackend(MediaBackend):
    def __init__(self):
        self.saved = {}

    def save(self, key: str, data: bytes, mime_type: str) -> str:
        self.saved[key] = (data, mime_type)
        return f"memory://{key}"

    def exists(self, key: str) -> bool:
        return key in self.saved


def test_media_downloader_uses_supplied_storage_backend(tmp_path):
    store = Store(tmp_path / "data")
    backend = MemoryBackend()
    downloader = MediaDownloader(
        store,
        backend=backend,
        fetcher=lambda url: (b"payload", "image/jpeg"),
    )
    record = {
        "platform": "x",
        "document_id": "post-1",
        "media_references": [
            {"kind": "image", "url": "https://example.invalid/a.jpg", "media_index": 0}
        ],
    }
    try:
        jobs = downloader.enqueue_from_records([record])
        result = downloader.run_queue(jobs)[0]
        assert result["status"] == "ok"
        assert result["local_path"].startswith("memory://")
        assert backend.saved
        known = store.media_known("x_post-1_0")
        assert known and known["local_path"] == result["local_path"]
        # A custom backend must mean no accidental filesystem write.
        assert list(store.media_dir.iterdir()) == []
    finally:
        store.close()


def test_raw_capture_counter_does_not_stop_at_65536(tmp_path):
    store = Store(tmp_path / "data")
    try:
        value = None
        for _ in range(65537):
            value = next(store._counter)
        assert value == 65536
    finally:
        store.close()


def test_cdp_walltime_is_used_as_real_timestamp():
    assert _cdp_wall_timestamp({"wallTime": 0}).startswith(
        "1970-01-01T00:00:00.000+00:00")


def test_normalize_canonical_media_name_matches_output():
    assert "media_references" in normalize.CANONICAL_FIELDS
    assert "media_refs" not in normalize.CANONICAL_FIELDS


def test_firefox_capture_forwards_original_response_bytes():
    source = (REPO_ROOT / "collector/firefox/extension/capture.js").read_text(
        encoding="utf-8")
    assert "filter.write(event.data)" in source
    assert 'details.method !== "GET"' not in source
    assert 'types: ["xmlhttprequest"]' in source


def test_firefox_capture_matches_laclaugpt_tiktok_routes():
    source = (REPO_ROOT / "collector/firefox/extension/capture.js").read_text(
        encoding="utf-8")
    # Keep Firefox interception aligned with the native TikTok parser routes.
    assert "post|challenge" in source
    assert "user\\/playlist" in source
    assert "search\\/(?:item_list|general\\/full)" in source


def test_firefox_capture_snapshots_page_url_before_response_finishes():
    source = (REPO_ROOT / "collector/firefox/extension/capture.js").read_text(
        encoding="utf-8")
    assert "platformUrlPromise = tabUrlFor(details.tabId)" in source
    assert "const platformUrl = await platformUrlPromise" in source
    assert "details.documentUrl" in source


def test_firefox_capture_accepts_embedded_page_state():
    capture = (REPO_ROOT / "collector/firefox/extension/capture.js").read_text(
        encoding="utf-8")
    content = (REPO_ROOT / "collector/firefox/extension/content.js").read_text(
        encoding="utf-8")
    assert 'message?.type !== "embedded"' in capture
    assert "postCapture" in capture
    assert 'type: "embedded"' in content
    assert "SIGI_STATE" in content
    assert "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content
    assert "script[type='application/json']" in content


def test_firefox_navigation_refreshes_tour_and_uses_backend_url():
    source = (REPO_ROOT / "collector/firefox/extension/navigation.js").read_text(
        encoding="utf-8")
    assert "const tour = await fetchTour();" in source
    assert "const url = item?.url;" in source
    assert "if (!tour?.active" in source
