"""Collection runner: systematic, resumable, observable.

    python -m collector.run --config collector/config/brazil-election-2026.yaml \
        --data-root ~/laclaugpt-brasil-data

One run iterates every configured account on every enabled platform:
capture -> parse -> normalise -> store -> optional media download.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import COLLECTOR_VERSION, browser, normalize
from .config import StudyConfig, load_config
from .media import MediaDownloader
from .modules import PLATFORM_MODULES
from .store import Store, utc_stamp

DEFAULT_SCROLLS = {"tiktok": 10, "x": 12, "instagram": 8}
REPO_ROOT = Path(__file__).resolve().parents[1]


def _git_commit(repo: Path = REPO_ROOT) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo,
            capture_output=True, text=True, timeout=15, check=False).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _load_normalized_records(store: Store) -> list[dict]:
    """Load all platform JSONL files for a post-capture media pass."""
    records: list[dict] = []
    for path in sorted(store.normalized_dir.glob("*.jsonl")):
        with open(path, encoding="utf-8") as handle:
            records.extend(json.loads(line) for line in handle if line.strip())
    return records


def collect_account(store: Store, cfg: StudyConfig, row: dict,
                    driver: Any, run_id: str,
                    scrolls: int | None = None,
                    download_media: bool = False) -> dict:
    """Collect one account on one platform. Returns a per-account result."""
    platform = row["platform"]
    module = PLATFORM_MODULES[platform]
    account = f"{row['name']}:{row['handle']}"
    result = {
        "account": account,
        "platform": platform,
        "handle": row["handle"],
        "posts": 0,
        "status": "ok",
        "error": None,
    }
    parsed_items = 0
    try:
        urls = browser.capture_platform_url(
            platform, row["handle"], cfg.platform_urls.get(platform, []))
        cursor = store.get_cursor(account, platform)
        if cursor:
            result["resumed_from"] = cursor
        seen_now = store.seen_count(platform)

        for url in urls:
            captures = driver.capture_account(
                platform, url,
                scrolls=scrolls or DEFAULT_SCROLLS.get(platform, 10))
            for cap in captures:
                if cap.get("data") is None:
                    continue
                captured_at = cap.get("ts") or datetime.now(
                    timezone.utc).isoformat(timespec="seconds")
                meta = {
                    "captured_at": captured_at,
                    "collector_version": COLLECTOR_VERSION,
                    "git_commit": _git_commit(),
                    "source_platform_url": cap.get("platform_url", url),
                    "source_url": cap["url"],
                    "run_id": run_id,
                    "account": account,
                }
                raw_ref = store.append_raw(platform, {
                    "url": cap["url"],
                    "ts": captured_at,
                    "platform_url": cap.get("platform_url", ""),
                    "data": cap["data"],
                })
                for item in module.capture(
                        cap["data"], cap.get("platform_url", url), cap["url"]):
                    parsed_items += 1
                    mapped = module.map_item(item, meta)
                    record = normalize.normalise(platform, mapped, item, meta)
                    record["raw_ref"] = raw_ref
                    is_new = store.upsert_post(record, raw_ref)
                    if is_new:
                        result["posts"] += 1
                    # Media download while the CDN signatures from THIS browsing
                    # session are still fresh. TikTok signs video URLs per
                    # session: a signature that fails with 403 in a later
                    # hourly pass may be valid RIGHT NOW in this capture.
                    # Fires for NEW posts AND for already-seen posts whose
                    # media previously failed (retroactive recovery: the fresh
                    # capture carries a fresh signed URL for the same post).
                    if download_media and record.get("media_references"):
                        downloader = MediaDownloader(store, workers=1)
                        m_jobs = downloader.enqueue_from_records([record])
                        if m_jobs:
                            m_results = downloader.run_queue(m_jobs)
                            stats = result.setdefault("media_inline", {
                                "ok": 0, "failed": 0})
                            for r in m_results:
                                key = "ok" if r.get("status") == "ok" else "failed"
                                stats[key] += 1

        store.checkpoint(account, platform, status="ok")
        result["new_posts"] = store.seen_count(platform) - seen_now
        stats = dict(getattr(driver, "last_stats", {}) or {})
        result["capture_stats"] = stats
        if parsed_items == 0:
            # Silent zero runs are the classic collector failure mode: name
            # the likely cause instead of reporting a clean "ok". (0 new
            # posts on a re-run is normal dedup — parsed_items counts what
            # the parser produced this run, so it separates those cases.)
            if stats.get("api_requests", 0) == 0:
                result["warning"] = ("0 parsed items and 0 matching API "
                                     "requests — page served no platform "
                                     "API calls (login wall or wrong URL?)")
            elif stats.get("bodies", 0) == 0:
                result["warning"] = (
                    f"0 parsed items: {stats.get('api_requests')} API "
                    f"requests but {stats.get('empty_bodies', 0)} empty "
                    "response bodies — this platform serves empty bodies "
                    "over CDP; use the Firefox path (collector/firefox)")
            else:
                result["warning"] = ("0 parsed items: API bodies captured "
                                     "but nothing matched the parser")
    except Exception as exc:  # noqa: BLE001
        store.checkpoint(account, platform, status=f"error: {exc}")
        result["status"] = "failed"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc(limit=4)
    return result


def run_collection(config_path: str, data_root: str, driver=None,
                   scrolls: int | None = None, download_media: bool = False,
                   media_workers: int = 4, dry_run: bool = False) -> dict:
    """One full collection pass over the configured study."""
    cfg = load_config(config_path)
    today = cfg.local_today()
    if not cfg.in_window(today):
        return {
            "skipped": True,
            "reason": f"outside study window {cfg.start}..{cfg.end} "
                      f"(today {today} in {cfg.timezone})",
        }

    run_id = utc_stamp()
    manifest = {
        "study": cfg.study,
        "run_id": run_id,
        "run_started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config_path,
        "collector_version": COLLECTOR_VERSION,
        "git_commit": _git_commit(),
        "window": {"start": str(cfg.start), "end": str(cfg.end)},
        "timezone": cfg.timezone,
        "accounts": [],
        "errors": [],
        "media": {},
    }

    if dry_run:
        manifest["dry_run"] = True
        manifest["accounts"] = [
            {"name": row["name"], "kind": row["kind"],
             "platform": row["platform"], "handle": row["handle"]}
            for row in cfg.accounts()
        ]
        manifest["missing_candidates"] = cfg.missing_candidates()
        return manifest

    store = Store(Path(data_root))
    try:
        # The HAR path is a fallback and may omit response bodies. CDP is the
        # default CLI capture path; Firefox remains the preferred long-running
        # collector for platforms where Chromium body capture is unreliable.
        driver = driver or browser.CDPCaptureDriver()
        total_new = 0
        for row in cfg.accounts():
            result = collect_account(
                store, cfg, row, driver, run_id=run_id, scrolls=scrolls,
                download_media=download_media)
            manifest["accounts"].append(result)
            if result["status"] != "ok":
                manifest["errors"].append(result)
            else:
                total_new += result.get("new_posts", 0)

        if download_media:
            downloader = MediaDownloader(store, workers=media_workers)
            records = _load_normalized_records(store)
            jobs = downloader.enqueue_from_records(records)
            results = downloader.run_queue(jobs)
            manifest["media"] = {
                "queued": len(jobs),
                "ok": sum(1 for result in results if result.get("status") == "ok"),
                "failed": sum(1 for result in results if result.get("status") == "failed"),
                "duplicates": sum(1 for result in results
                                  if result.get("status") == "duplicate"),
            }

        manifest["new_posts_total"] = total_new
        manifest["seen_total"] = store.seen_count()
        manifest["missing_candidates"] = cfg.missing_candidates()
        manifest["run_finished"] = datetime.now(
            timezone.utc).isoformat(timespec="seconds")
        store.write_manifest(manifest)
        return manifest
    finally:
        store.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m collector.run")
    parser.add_argument("--config", required=True, help="study YAML configuration")
    parser.add_argument("--data-root", required=True,
                        help="collection data root (outside the repo, not committed)")
    parser.add_argument("--scrolls", type=int, default=None)
    parser.add_argument("--download-media", action="store_true")
    parser.add_argument("--media-workers", type=int, default=4)
    parser.add_argument("--driver", choices=("cdp", "har"), default="cdp",
                        help="browser capture path for the CLI runner")
    parser.add_argument("--dry-run", action="store_true",
                        help="print plan + config flags without browsing")
    args = parser.parse_args(argv)

    driver = None
    if not args.dry_run:
        driver = (browser.CDPCaptureDriver() if args.driver == "cdp"
                  else browser.AgentBrowserDriver())

    manifest = run_collection(
        args.config,
        args.data_root,
        driver=driver,
        scrolls=args.scrolls,
        download_media=args.download_media,
        media_workers=args.media_workers,
        dry_run=args.dry_run,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
