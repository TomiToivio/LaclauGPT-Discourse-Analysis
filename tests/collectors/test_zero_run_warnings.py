"""Regression tests: silent zero-run warnings + capture stats (2026-09-07).

The collector's classic failure mode is an account pass that reports a
clean "ok" while parsing 0 items — a login wall, empty CDP bodies, or a
parser mismatch all looked identical. The runner must now name the
likely cause and record the driver's capture stats per account.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from collector.config import load_config

CFG_PATH = str(Path("collector/config/brazil-election-2026.yaml").resolve())


@pytest.fixture
def in_window(monkeypatch):
    """Freeze the config loader so the study window always contains today."""
    from collector import run as runner

    real = load_config

    def fake_load(path):
        cfg = real(path)
        cfg.start, cfg.end = date(2026, 1, 1), date(2099, 12, 31)
        return cfg

    monkeypatch.setattr(runner, "load_config", fake_load)


@pytest.fixture
def one_tiktok_account():
    """Restrict the study to its first TikTok account (keeps runs fast)."""
    cfg = load_config(CFG_PATH)
    real_accounts = cfg.accounts()
    cfg.accounts = lambda: [r for r in real_accounts
                            if r["platform"] == "tiktok"][:1]
    return cfg


def _run(tmp_path, monkeypatch, driver, one_tiktok_account):
    from collector import run as runner

    monkeypatch.setattr(runner, "load_config", lambda path: one_tiktok_account)
    return runner.run_collection(CFG_PATH, str(tmp_path / "data"), driver=driver)


class ZeroRequestDriver:
    """Simulates a login wall: the page serves no platform API calls."""
    last_stats = {"api_requests": 0, "bodies": 0, "empty_bodies": 0}

    def capture_account(self, platform, url, scrolls, **_):
        return []


class EmptyBodyDriver:
    """Simulates Chromium/TikTok: API requests seen, response bodies empty."""
    last_stats = {"api_requests": 3, "bodies": 0, "empty_bodies": 3}

    def capture_account(self, platform, url, scrolls, **_):
        return [{"url": "https://www.tiktok.com/api/post/item_list/",
                 "data": None, "ts": "2026-09-07T00:00:00+00:00",
                 "platform_url": url}]


def test_zero_requests_warning(tmp_path, monkeypatch, in_window,
                               one_tiktok_account):
    from collector import run as runner

    manifest = _run(tmp_path, monkeypatch, ZeroRequestDriver(),
                    one_tiktok_account)
    acc = manifest["accounts"][0]
    assert acc["status"] == "ok"
    assert "warning" in acc
    assert "0 matching API requests" in acc["warning"]
    assert acc["capture_stats"] == ZeroRequestDriver.last_stats


def test_empty_body_warning_points_to_firefox(tmp_path, monkeypatch,
                                              in_window,
                                              one_tiktok_account):
    from collector import run as runner

    manifest = _run(tmp_path, monkeypatch, EmptyBodyDriver(),
                    one_tiktok_account)
    acc = manifest["accounts"][0]
    assert "warning" in acc
    assert "empty response bodies" in acc["warning"]
    assert "Firefox" in acc["warning"]


def test_parsed_items_no_false_warning(tmp_path, monkeypatch, in_window,
                                       one_tiktok_account,
                                       tiktok_api_response):
    """Items that parse fine (even if all deduped) must not warn."""
    from collector import run as runner

    class WorkingDriver:
        last_stats = {"api_requests": 1, "bodies": 1, "empty_bodies": 0}

        def capture_account(self, platform, url, scrolls, **_):
            return [{"url": "https://www.tiktok.com/api/post/item_list/",
                     "data": tiktok_api_response,
                     "ts": "2026-09-07T00:00:00+00:00",
                     "platform_url": url}]

    manifest = _run(tmp_path, monkeypatch, WorkingDriver(),
                    one_tiktok_account)
    acc = manifest["accounts"][0]
    assert "warning" not in acc
    assert acc["capture_stats"]["bodies"] == 1


def test_cdp_driver_exposes_last_stats():
    """The CDP driver must publish per-run capture counters."""
    from collector.browser import CDPCaptureDriver

    d = CDPCaptureDriver()
    assert d.last_stats == {"api_requests": 0, "bodies": 0,
                            "empty_bodies": 0}