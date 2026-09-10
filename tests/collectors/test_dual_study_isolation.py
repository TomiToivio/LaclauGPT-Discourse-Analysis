"""Dual-study isolation tests: one collector, two separate datasets.

Acceptance criteria (issue: Brazil26 + AI26 on the shared Firefox collector):
- one collector implementation serves two studies;
- data roots are physically separate (raw/normalized/media/manifests/state);
- the same platform document_id can exist once in EACH study;
- dedup/checkpoint state is independent;
- study identity rides in /status, /tour and normalized provenance;
- generic groups (AI26 shape) load; Brazil26 shape stays compatible.
"""
from __future__ import annotations

import json
import threading
import urllib.request
from datetime import date
from pathlib import Path

import pytest
import yaml

from collector.config import load_config
from collector.firefox.firefox_backend import CaptureServer

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_CONFIG = REPO_ROOT / "tests" / "fixtures" / "synthetic-collector-study.yaml"


def _url(server, path: str) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}{path}"


def _post(server, path: str, payload: dict):
    req = urllib.request.Request(
        _url(server, path),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return urllib.request.urlopen(req, timeout=10)


def _server(tmp_path, config=SYNTHETIC_CONFIG):
    s = CaptureServer(str(config), str(tmp_path / "data"), port=0)
    s.cfg.start, s.cfg.end = date(2000, 1, 1), date(2099, 12, 31)
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    yield s
    s.shutdown()
    s.server_close()
    s.store.close()


def _x_capture_payload(x_modern_tweet) -> dict:
    """Synthetic X GraphQL response shaped like TweetDetail instructions."""
    return {
        "type": "TimelineAddEntries",
        "entries": [{
            "entryId": f"tweet-{x_modern_tweet['rest_id']}",
            "content": {
                "itemContent": {
                    "itemType": "TimelineTweet",
                    "__typename": "TimelineTweet",
                    "tweet_results": {"result": x_modern_tweet},
                },
            },
        }],
    }


def _x_capture(x_modern_tweet, handle="synthetic_lab") -> dict:
    return {
        "platform": "x",
        "api_url": "https://x.com/i/api/graphql/abc/UserTweets?count=20",
        "platform_url": f"https://x.com/{handle}",
        "captured_at": "2026-09-10T12:00:00Z",
        "body": json.dumps(_x_capture_payload(x_modern_tweet)),
    }


@pytest.fixture
def brazil_server(tmp_path):
    yield from _server(tmp_path / "brazil26")


@pytest.fixture
def ai26_server(tmp_path, ai26_config):
    yield from _server(tmp_path / "ai26", config=ai26_config)


@pytest.fixture
def ai26_config(tmp_path) -> Path:
    """Synthetic AI26-shaped config: generic groups, X-first."""
    cfg = {
        "study": "ai26",
        "timezone": "UTC",
        "window": {"start": "2026-01-01", "end": "2026-12-31"},
        "platforms": {
            "x": {"enabled": True, "base_urls": ["https://x.com/{handle}"]},
            "instagram": {"enabled": False},
            "tiktok": {"enabled": False},
        },
        "groups": [
            {"id": "ai-elites-labs", "name": "AI Labs",
             "arena": "elites", "formation_seed": "techno_optimist",
             "accounts": {"x": ["synthetic_lab", "synthetic_lab2"]}},
            {"id": "ai-critical", "name": "Critical AI",
             "arena": "elites", "formation_seed": None,
             "accounts": {"x": ["synthetic_critical"]}},
        ],
    }
    path = tmp_path / "ai26.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


def test_generic_groups_load(ai26_config):
    cfg = load_config(ai26_config)
    assert cfg.study == "ai26"
    assert cfg.platforms == ["x"]
    rows = cfg.accounts()
    assert [r["platform"] for r in rows] == ["x"] * 3
    assert {r["group_id"] for r in rows} == {"ai-elites-labs", "ai-critical"}
    # formation_seed rides as provenance; null stays empty (never fabricated)
    seeds = {r["group_id"]: r["formation_seed"] for r in rows}
    assert seeds["ai-elites-labs"] == "techno_optimist"
    assert seeds["ai-critical"] == ""
    assert {r["kind"] for r in rows} == {"group"}


def test_status_and_tour_expose_study(ai26_config, tmp_path):
    s = next(_server(tmp_path / "s1", config=ai26_config))
    try:
        status = json.loads(urllib.request.urlopen(_url(s, "/status"), timeout=10).read())
        tour = json.loads(urllib.request.urlopen(_url(s, "/tour"), timeout=10).read())
        assert status["study"] == "ai26"
        assert tour["study"] == "ai26"
    finally:
        s.shutdown(); s.server_close(); s.store.close()


def test_same_document_id_in_both_studies(brazil_server, ai26_server,
                                          x_modern_tweet):
    """One collector codebase, two stores: the SAME document_id exists
    independently once per study (physical isolation, no shared dedup)."""
    cap = _x_capture(x_modern_tweet)
    with _post(brazil_server, "/capture", cap) as r1:
        assert json.loads(r1.read())["ok"] is True
    with _post(ai26_server, "/capture", cap) as r2:
        assert json.loads(r2.read())["ok"] is True

    b_root = Path(brazil_server.store.root)
    a_root = Path(ai26_server.store.root)
    # physical separation: separate state dbs
    assert (b_root / "state.sqlite3").exists()
    assert (a_root / "state.sqlite3").exists()
    assert (b_root / "state.sqlite3") != (a_root / "state.sqlite3")
    # separate normalized/raw/media/manifests dirs
    for sub in ("raw", "normalized", "media", "manifests"):
        assert (b_root / sub).is_dir() and (a_root / sub).is_dir()
    # same document_id stored once in EACH dataset
    b_seen = brazil_server.store.seen_count()
    a_seen = ai26_server.store.seen_count()
    assert b_seen >= 1 and a_seen >= 1
    # independent dedup: capturing the same payload AGAIN in one study does
    # not change the other study's counts
    with _post(brazil_server, "/capture", cap) as r:
        assert json.loads(r.read())["new_posts"] == 0  # dedup within study
    assert brazil_server.store.seen_count() == b_seen
    assert ai26_server.store.seen_count() == a_seen


def test_normalized_provenance_carries_study(brazil_server, ai26_server,
                                             x_modern_tweet):
    cap = _x_capture(x_modern_tweet)
    with _post(brazil_server, "/capture", cap):
        pass
    with _post(ai26_server, "/capture", cap):
        pass

    def read_normalized(root: Path) -> list[dict]:
        path = root / "normalized" / "x.jsonl"
        return [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()]

    b_rows = read_normalized(Path(brazil_server.store.root))
    a_rows = read_normalized(Path(ai26_server.store.root))
    assert b_rows and a_rows
    assert b_rows[0]["collection_provenance"]["study"] == "synthetic-election-study"
    assert a_rows[0]["collection_provenance"]["study"] == "ai26"
    # runs are per-backend-instance: study + run_id together identify the run
    assert (b_rows[0]["collection_provenance"]["run_id"],
            b_rows[0]["collection_provenance"]["study"]) != \
           (a_rows[0]["collection_provenance"]["run_id"],
            a_rows[0]["collection_provenance"]["study"])


def test_checkpoint_state_independent(brazil_server, ai26_server):
    brazil_server.store.checkpoint("synthetic_lab", "x", cursor="42")
    ai26_server.store.checkpoint("synthetic_lab", "x", cursor="999")
    assert brazil_server.store.get_cursor("synthetic_lab", "x") == "42"
    assert ai26_server.store.get_cursor("synthetic_lab", "x") == "999"