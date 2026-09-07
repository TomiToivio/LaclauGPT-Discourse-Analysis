"""Firefox backend tests: capture -> parse -> store pipeline (offline)."""
from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import pytest

from collector.firefox.firefox_backend import CaptureServer

REPO_ROOT = Path(__file__).resolve().parents[2]


def _backend_url(server: CaptureServer, path: str) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}{path}"


@pytest.fixture
def server(tmp_path):
    cfg = str(REPO_ROOT / "collector" / "config" / "brazil-election-2026.yaml")
    s = CaptureServer(cfg, str(tmp_path / "data"), port=0)  # port=0: free port
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    yield s
    s.shutdown()
    s.store.close()


def test_backend_roundtrip(server, tiktok_item):
    """POST a TikTok item_list capture -> parsed post lands in the store."""
    payload = json.dumps({"itemList": [tiktok_item]})
    req = urllib.request.Request(
        _backend_url(server, "/capture"),
        data=json.dumps({
            "platform": "tiktok",
            "api_url": "https://www.tiktok.com/api/post/item_list/?count=24",
            "platform_url": "https://www.tiktok.com/@lulaoficial",
            "captured_at": "2026-09-07T10:00:00Z",
            "body": payload,
        }).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200

    assert server.stats["captures"] == 1
    assert server.stats["posts"] == 1
    assert server.store.seen_count("tiktok") == 1
    # normalised record on disk with provenance
    rec = json.loads((server.store.normalized_dir / "tiktok.jsonl")
                     .read_text(encoding="utf-8").splitlines()[-1])
    assert rec["document_id"] == tiktok_item["id"]
    assert rec["collection_provenance"]["collector_version"]


def test_tour_endpoint(server):
    with urllib.request.urlopen(_backend_url(server, "/tour"), timeout=10) as resp:
        tour = json.loads(resp.read())
    assert tour["window"]["start"] == "2026-09-07"
    handles = {a["handle"] for a in tour["accounts"]}
    assert "lulaoficial" in handles and "ptbrasil" in handles


def test_duplicate_capture_not_double_stored(server, tiktok_item):
    body = json.dumps({"itemList": [tiktok_item]})
    for _ in range(2):
        req = urllib.request.Request(
            _backend_url(server, "/capture"),
            data=json.dumps({"platform": "tiktok",
                             "api_url": "https://www.tiktok.com/api/post/item_list/?c=1",
                             "platform_url": "https://www.tiktok.com/@lulaoficial",
                             "captured_at": "t", "body": body}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    assert server.store.seen_count("tiktok") == 1  # dedup holds