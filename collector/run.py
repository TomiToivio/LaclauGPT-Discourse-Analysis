"""Collection runner: systematic, resumable, observable.

    python -m collector.run --config collector/config/brazil-election-2026.yaml

One run iterates every configured account on every enabled platform:
capture (driver) → parse (module capture + map_item) → normalise →
store (raw + normalized + state) → optional media queue. Per-account
failures are recorded and do not abort the run; checkpoints let the next
run resume; the study window gates execution.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import COLLECTOR_VERSION, browser, normalize
from .config import StudyConfig, load_config
from .media import MediaDownloader
from .modules import PLATFORM_MODULES
from .store import Store, utc_stamp

DEFAULT_SCROLLS = {"tiktok": 10, "x": 12, "instagram": 8}


def _git_commit(repo: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo,
            capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def collect_account(store: Store, cfg: StudyConfig, row: dict,
                    driver: browser.AgentBrowserDriver,
                    scrolls: int | None = None) -> dict:
    """Collect one account on one platform. Returns a per-account result."""
    platform = row["platform"]
    module = PLATFORM_MODULES[platform]
    account = f"{row['name']}:{row['handle']}"
    result = {"account": account, "platform": platform,
              "handle": row["handle"], "posts": 0, "status": "ok", "error": None}
    try:
        urls = browser.capture_platform_url(
            platform, row["handle"], cfg.platform_urls.get(platform, []))
        cursor = store.get_cursor(account, platform)
        if cursor:
            result["resumed_from"] = cursor
        seen_now = store.seen_count(platform)
        for url in urls:
            captures = driver.capture_account(
                platform, url, scrolls=scrolls or DEFAULT_SCROLLS.get(platform, 10))
            for cap in captures:
                if cap.get("data") is None:
                    continue
                captured_at = cap.get("ts") or datetime.now(
                    timezone.utc).isoformat(timespec="seconds")
                meta = {
                    "captured_at": captured_at,
                    "collector_version": COLLECTOR_VERSION,
                    "git_commit": _git_commit(Path.cwd()),
                    "source_platform_url": cap.get("platform_url", url),
                    "source_url": cap["url"],
                    "run_id": f"{utc_stamp()}",
                    "account": account,
                }
                raw_ref = store.append_raw(platform, {
                    "url": cap["url"], "ts": captured_at,
                    "platform_url": cap.get("platform_url", ""), "data": cap["data"]})
                for item in module.capture(cap["data"], cap.get("platform_url", url),
                                           cap["url"]):
                    mapped = module.map_item(item, meta)
                    record = normalize.normalise(platform, mapped, item, meta)
                    record["raw_ref"] = raw_ref
                    if store.upsert_post(record, raw_ref):
                        result["posts"] += 1
        store.checkpoint(account, platform, status="ok")
        result["new_posts"] = store.seen_count(platform) - seen_now
    except Exception as exc:  # noqa: BLE001 — one account failing never kills the run
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
    now = datetime.now(timezone.utc).date()
    if not cfg.in_window(now):
        return {"skipped": True, "reason": f"outside study window "
                f"{cfg.start}..{cfg.end} (today {now})"}

    manifest = {
        "study": cfg.study,
        "run_started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config_path,
        "collector_version": COLLECTOR_VERSION,
        "git_commit": _git_commit(Path.cwd()),
        "window": {"start": str(cfg.start), "end": str(cfg.end)},
        "accounts": [], "errors": [], "media": {},
    }

    if dry_run:
        manifest["dry_run"] = True
        manifest["accounts"] = [
            {"name": r["name"], "kind": r["kind"], "platform": r["platform"],
             "handle": r["handle"]} for r in cfg.accounts()]
        manifest["missing_candidates"] = cfg.missing_candidates()
        return manifest

    store = Store(Path(data_root))
    driver = driver or browser.AgentBrowserDriver()
    total_new = 0
    for row in cfg.accounts():
        result = collect_account(store, cfg, row, driver, scrolls=scrolls)
        manifest["accounts"].append(result)
        if result["status"] != "ok":
            manifest["errors"].append(result)
        else:
            total_new += result.get("new_posts", 0)

    if download_media:
        from .media import MediaDownloader
        dl = MediaDownloader(store, workers=media_workers)
        records = []
        for path in store.normalized_dir.glob("*.jsonl"):
            with open(path, encoding="utf-8") as fh:
                records = [json.loads(line) for line in fh if line.strip()]
        jobs = dl.enqueue_from_records(records)
        results = dl.run_queue(jobs)
        manifest["media"] = {
            "queued": len(jobs),
            "ok": sum(1 for r in results if r.get("status") == "ok"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
            "duplicates": sum(1 for r in results if r.get("status") == "duplicate"),
        }

    manifest["new_posts_total"] = total_new
    manifest["seen_total"] = store.seen_count()
    manifest["missing_candidates"] = cfg.missing_candidates()
    manifest["run_finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    store.write_manifest(manifest)
    store.close()
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m collector.run")
    ap.add_argument("--config", required=True, help="study YAML configuration")
    ap.add_argument("--data-root", required=True,
                    help="collection data root (outside the repo, not committed)")
    ap.add_argument("--scrolls", type=int, default=None)
    ap.add_argument("--download-media", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="print plan + config flags without browsing")
    args = ap.parse_args(argv)
    manifest = run_collection(
        args.config, args.data_root, scrolls=args.scrolls,
        download_media=args.download_media, dry_run=args.dry_run)
    print(json.dumps(manifest, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())