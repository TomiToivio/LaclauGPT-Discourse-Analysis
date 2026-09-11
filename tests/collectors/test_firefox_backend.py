"""Firefox backend tests: capture -> parse -> store pipeline (offline)."""
from __future__ import annotations

import json
import threading
import urllib.request
from datetime import date
from pathlib import Path

import pytest

from collector.firefox.firefox_backend import CaptureServer

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_CONFIG = REPO_ROOT / "tests" / "fixtures" / "synthetic-collector-study.yaml"


def _backend_url(server: CaptureServer, path: str) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}{path}"


def _post_json(server: CaptureServer, path: str, payload: dict):
    req = urllib.request.Request(
        _backend_url(server, path),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req, timeout=10)


@pytest.fixture
def server(tmp_path):
    s = CaptureServer(str(SYNTHETIC_CONFIG), str(tmp_path / "data"), port=0)
    # Keep pipeline tests independent of the real calendar. Window behaviour
    # has its own explicit regression test below.
    s.cfg.start, s.cfg.end = date(2000, 1, 1), date(2099, 12, 31)
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    yield s
    s.shutdown()
    s.server_close()
    s.store.close()


def _tiktok_capture(tiktok_item, body_prefix="") -> dict:
    return {
        "platform": "tiktok",
        "api_url": "https://www.tiktok.com/api/post/item_list/?count=24",
        "platform_url": "https://www.tiktok.com/@candidate_alpha",
        "captured_at": "2026-09-07T10:00:00Z",
        "body": body_prefix + json.dumps({"itemList": [tiktok_item]}),
    }


def test_backend_roundtrip(server, tiktok_item):
    """POST a TikTok item_list capture -> parsed post lands in the store."""
    with _post_json(server, "/capture", _tiktok_capture(tiktok_item)) as resp:
        assert resp.status == 200
        reply = json.loads(resp.read())
    assert reply["new_posts"] == 1
    assert server.stats["captures"] == 1
    assert server.stats["posts"] == 1
    assert server.store.seen_count("tiktok") == 1

    rec = json.loads((server.store.normalized_dir / "tiktok.jsonl")
                     .read_text(encoding="utf-8").splitlines()[-1])
    assert rec["document_id"] == tiktok_item["id"]
    assert rec["collection_provenance"]["collector_version"]
    # @handle URL attribution was previously broken and became "unattributed".
    assert rec["collection_provenance"]["account"] == "Candidate Alpha:candidate_alpha"


def test_backend_accepts_extension_embedded_object_body(server, tiktok_item):
    """content.js sends embedded page-state as a nested JSON object, not text."""
    capture = {
        "platform": "tiktok",
        "api_url": "https://www.tiktok.com/@synthetic_user#embedded:UNIVERSAL_DATA",
        "platform_url": "https://www.tiktok.com/@synthetic_user",
        "captured_at": "2026-09-07T10:00:00Z",
        "body": {"itemList": [tiktok_item]},
    }
    with _post_json(server, "/capture", capture) as resp:
        assert resp.status == 200
        reply = json.loads(resp.read())
    assert reply["new_posts"] == 1
    assert server.store.seen_count("tiktok") == 1


def test_backend_accepts_tiktok_challenge_route(server, tiktok_item):
    """Firefox matcher and native parser both support challenge item lists."""
    capture = {
        "platform": "tiktok",
        "api_url": "https://www.tiktok.com/api/challenge/item_list/?challengeID=synthetic",
        "platform_url": "https://www.tiktok.com/tag/synthetic",
        "captured_at": "2026-09-07T10:00:00Z",
        "body": {"itemList": [tiktok_item]},
    }
    with _post_json(server, "/capture", capture) as resp:
        assert resp.status == 200
        reply = json.loads(resp.read())
    assert reply["new_posts"] == 1


def test_backend_accepts_instagram_anti_json_prefix(server, instagram_itemlist_item):
    """Instagram-style `for (;;);` JSON prefix is stripped by the backend."""
    envelope = {"items": [instagram_itemlist_item]}
    capture = {
        "platform": "instagram",
        "api_url": "https://www.instagram.com/api/v1/feed/user/123/",
        "platform_url": "https://www.instagram.com/candidate_alpha/",
        "captured_at": "2026-09-07T10:00:00Z",
        "body": "for (;;);" + json.dumps(envelope),
    }
    with _post_json(server, "/capture", capture) as resp:
        assert resp.status == 200
    assert server.stats["errors"] == 0


def test_backend_roundtrip_instagram_extension_shape(server, instagram_itemlist_item):
    capture = {
        "platform": "instagram",
        "api_url": "https://www.instagram.com/api/v1/feed/user/9876543210/",
        "platform_url": "https://www.instagram.com/synthetic_user/",
        "captured_at": "2026-09-07T10:00:00Z",
        "body": {"items": [instagram_itemlist_item]},
    }
    with _post_json(server, "/capture", capture) as resp:
        assert resp.status == 200
        reply = json.loads(resp.read())
    assert reply["new_posts"] == 1
    assert server.store.seen_count("instagram") == 1


def test_backend_roundtrip_x_extension_shape(server, x_graphql_envelope):
    capture = {
        "platform": "x",
        "api_url": "https://x.com/i/api/graphql/abc123/UserOriginalsTimeline?variables=1",
        "platform_url": "https://x.com/synthetic_user",
        "captured_at": "2026-09-07T10:00:00Z",
        "body": x_graphql_envelope,
    }
    with _post_json(server, "/capture", capture) as resp:
        assert resp.status == 200
        reply = json.loads(resp.read())
    assert reply["new_posts"] == 1
    assert server.store.seen_count("x") == 1


def test_tour_endpoint_expands_all_configured_urls(server):
    with urllib.request.urlopen(_backend_url(server, "/tour"), timeout=10) as resp:
        tour = json.loads(resp.read())
    assert tour["active"] is True
    assert tour["timezone"] == "America/Sao_Paulo"
    handles = {a["handle"] for a in tour["accounts"]}
    assert "candidate_alpha" in handles and "party_alpha" in handles

    alpha_x = [a["url"] for a in tour["accounts"]
               if a["platform"] == "x" and a["handle"] == "CandidateAlpha"]
    assert "https://x.com/CandidateAlpha" in alpha_x
    assert "https://x.com/CandidateAlpha/with_replies" in alpha_x

    alpha_ig = [a["url"] for a in tour["accounts"]
                if a["platform"] == "instagram" and a["handle"] == "candidate_alpha"]
    assert "https://www.instagram.com/candidate_alpha/" in alpha_ig
    assert "https://www.instagram.com/candidate_alpha/reels/" in alpha_ig


def test_tour_and_capture_stop_outside_window(server, tiktok_item):
    server.cfg.start, server.cfg.end = date(1900, 1, 1), date(1900, 1, 2)
    with urllib.request.urlopen(_backend_url(server, "/tour"), timeout=10) as resp:
        tour = json.loads(resp.read())
    assert tour["active"] is False
    assert tour["accounts"] == []

    with _post_json(server, "/capture", _tiktok_capture(tiktok_item)) as resp:
        reply = json.loads(resp.read())
    assert reply["skipped"] == "outside study window"
    assert server.stats["captures"] == 0
    assert server.stats["skipped"] == 1
    assert server.store.seen_count() == 0


def test_duplicate_capture_not_double_stored(server, tiktok_item):
    capture = _tiktok_capture(tiktok_item)
    for _ in range(2):
        with _post_json(server, "/capture", capture) as resp:
            assert resp.status == 200
    assert server.store.seen_count("tiktok") == 1
    assert server.stats["captures"] == 2
    assert server.stats["posts"] == 1
