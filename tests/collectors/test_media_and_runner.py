"""Media downloader, runner, config and resume tests (mocked HTTP/offline).

Issue #20 required cases 7-12 plus config/provenance coverage.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from collector.config import load_config
from collector.media import MediaDownloader
from collector.store import Store


# --- 7/8/9. media download (mocked HTTP) ---------------------------------------

def _fake_fetch_ok(url: str):
    return b"synthetic-bytes", "image/jpeg"


def _fake_fetch_expired(url: str):
    raise Exception("404 Not Found: signed URL expired")


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "data")
    yield s
    s.close()


def _record_with_media(store: Store, platform="tiktok", doc="doc1") -> dict:
    return {
        "platform": platform, "document_id": doc,
        "media_references": [
            {"kind": "video", "url": "https://cdn.example/v.mp4", "media_index": 0},
            {"kind": "image", "url": "https://cdn.example/i.jpg", "media_index": 1},
        ],
    }


def test_media_download_success(store):
    dl = MediaDownloader(store, fetcher=_fake_fetch_ok)
    rec = _record_with_media(store)
    jobs = dl.enqueue_from_records([rec])
    assert len(jobs) == 2
    results = dl.run_queue(jobs)
    assert all(r["status"] == "ok" for r in results)
    for r in results:
        assert r["sha256"]  # checksum recorded
        assert r["byte_size"] == len(b"synthetic-bytes")
        assert r["local_path"].startswith("media/")
    # deterministic collision-resistant filenames platform_postID_mediaIndex
    names = sorted(r["media_key"] for r in results)
    assert names == ["tiktok_doc1_0", "tiktok_doc1_1"]


def test_media_failure_recorded_post_intact(store):
    dl = MediaDownloader(store, fetcher=_fake_fetch_expired)
    rec = _record_with_media(store)
    results = dl.run_queue(dl.enqueue_from_records([rec]))
    assert all(r["status"] == "failed" for r in results)
    assert "expired" in results[0]["failure_reason"]
    # the post metadata is unaffected — media_index just records failure
    known = store.media_known("tiktok_doc1_0")
    assert known["status"] == "failed"


def test_media_retry_no_duplicate(store):
    dl = MediaDownloader(store, fetcher=_fake_fetch_ok)
    rec = _record_with_media(store)
    dl.run_queue(dl.enqueue_from_records([rec]))
    # second enqueue: verified copies exist -> nothing queued
    jobs2 = dl.enqueue_from_records([rec])
    assert jobs2 == []
    # direct forced re-run also dedups by checksum
    results = dl.run_queue([{"media_key": "tiktok_doc1_0", "platform": "tiktok",
                             "document_id": "doc1", "media_index": 0,
                             "kind": "video", "url": "https://cdn.example/v.mp4"}])
    assert results[0]["status"] == "duplicate"


def test_media_failed_then_retry_downloads(store):
    dl = MediaDownloader(store, fetcher=_fake_fetch_expired)
    dl.run_queue(dl.enqueue_from_records([_record_with_media(store)]))
    # retry with a working fetcher: failures are retried, not blacklisted
    dl2 = MediaDownloader(store, fetcher=_fake_fetch_ok)
    jobs = dl2.enqueue_from_records([_record_with_media(store)])
    assert len(jobs) == 2  # failed entries stay queued
    results = dl2.run_queue(jobs)
    assert all(r["status"] == "ok" for r in results)


# --- 10. resume after interruption ----------------------------------------------

def test_checkpoints_resume(store):
    store.checkpoint("Lula:lulaoficial", "tiktok", status="ok")
    store.checkpoint("Lula:lulaoficial", "x", status="error: boom")
    assert store.get_cursor("Lula:lulaoficial", "tiktok") is None
    failing = store.failing_accounts()
    assert ("Lula:lulaoficial", "x") == (failing[0][0], failing[0][1])
    # a later successful run clears to ok
    store.checkpoint("Lula:lulaoficial", "x", status="ok")
    assert store.failing_accounts() == []


# --- 11. window filter -----------------------------------------------------------

def test_study_window_filter(tmp_path):
    cfg = load_config("collector/config/brazil-election-2026.yaml")
    assert cfg.in_window(date(2026, 9, 7)) is True
    assert cfg.in_window(date(2026, 10, 10)) is True
    assert cfg.in_window(date(2026, 10, 11)) is False
    assert cfg.in_window(date(2026, 9, 6)) is False


# --- 12. config: multiple accounts per candidate ---------------------------------

def test_config_multiple_accounts_and_parties():
    cfg = load_config("collector/config/brazil-election-2026.yaml")
    rows = cfg.accounts()
    lula = [r for r in rows if r["name"] == "Lula"]
    # two handles per platform for Lula
    assert len(lula) >= 6
    assert {r["handle"] for r in lula if r["platform"] == "x"} == {
        "LulaOficial", "OBrasilComLula"}
    assert {r["handle"] for r in lula if r["platform"] == "instagram"} == {
        "lulaoficial", "brasilcomlula"}
    assert {r["handle"] for r in lula if r["platform"] == "tiktok"} == {
        "lulaoficial", "brasilcomlula_"}
    # party accounts present as kind=party
    pt = [r for r in rows if r["name"] == "PT"]
    assert len(pt) == 3 and all(r["kind"] == "party" for r in pt)
    pl = [r for r in rows if r["name"] == "PL"]
    assert {r["handle"] for r in pl} == {"plnacional22", "plnacional_"}
    # handles stored exactly as supplied (no silent correction)
    zema = [r for r in rows if r["name"] == "Romeu Zema"]
    assert {r["handle"] for r in zema if r["platform"] == "x"} == {"RomeuZema"}


def test_config_missing_seventh_candidate_flagged():
    cfg = load_config("collector/config/brazil-election-2026.yaml")
    assert cfg.expected_candidates == 7
    flag = cfg.missing_candidates()
    assert flag, "gap must be flagged while only six candidates are configured"
    assert "7" in flag[0] and "6" in flag[0]


# --- runner manifest / provenance -------------------------------------------------

def test_run_dry_run_manifest(tmp_path):
    from collector import run as runner

    repo_cfg = str(Path("collector/config/brazil-election-2026.yaml").resolve())
    manifest = runner.run_collection(repo_cfg, str(tmp_path / "data"), dry_run=True)
    assert manifest["study"] == "brazil-presidential-2026"
    assert manifest["dry_run"] is True
    assert manifest["missing_candidates"]
    kinds = {a["kind"] for a in manifest["accounts"]}
    assert kinds == {"candidate", "party"}
    platforms = {a["platform"] for a in manifest["accounts"]}
    assert platforms == {"tiktok", "x", "instagram"}


def test_run_window_skip(tmp_path, monkeypatch):
    from collector import run as runner

    cfg_path = str(Path("collector/config/brazil-election-2026.yaml").resolve())
    # freeze the config loader to a window that excludes today
    real = load_config

    def fake_load(path):
        cfg = real(path)
        cfg.start, cfg.end = date(2026, 1, 1), date(2026, 1, 2)
        return cfg

    monkeypatch.setattr(runner, "load_config", fake_load)
    out = runner.run_collection(cfg_path, str(tmp_path / "data"))
    assert out["skipped"] is True
    assert "outside study window" in out["reason"]


def test_manifest_written_and_provenance_fields(tmp_path, monkeypatch):
    """A (captured-free) live runner pass writes a manifest with provenance."""
    from collector import run as runner
    from collector.browser import AgentBrowserDriver

    class FakeDriver:
        def capture_account(self, platform, url, scrolls, har_path=None):
            return []  # simulate platforms serving nothing (offline)

    cfg_path = "collector/config/brazil-election-2026.yaml"
    real = load_config

    def fake_load(path):
        cfg = real(path)
        cfg.start, cfg.end = date(2026, 1, 1), date(2099, 12, 31)
        return cfg

    monkeypatch.setattr(runner, "load_config", fake_load)
    root = tmp_path / "data"
    manifest = runner.run_collection(cfg_path, str(root), driver=FakeDriver())
    assert manifest["new_posts_total"] == 0
    assert manifest["collector_version"]
    assert len(manifest["git_commit"]) >= 7
    assert manifest["missing_candidates"]
    manifests = list((root / "manifests").glob("run-*.json"))
    assert manifests
    saved = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert saved["collector_version"] == manifest["collector_version"]
    assert saved["window"] == manifest["window"]


# --- config file validity ---------------------------------------------------------

def test_brazil_config_yaml_shape():
    data = yaml.safe_load(
        open("collector/config/brazil-election-2026.yaml", encoding="utf-8"))
    assert data["timezone"] == "America/Sao_Paulo"
    assert data["window"]["start"] == "2026-09-07"
    assert data["window"]["end"] == "2026-10-10"
    assert len(data["candidates"]) == 6
    assert len(data["parties"]) == 2