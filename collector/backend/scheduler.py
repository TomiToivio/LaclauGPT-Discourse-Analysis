"""Scheduled wrapper for the canonical LaclauGPT collector.

This module used to invoke legacy files (`autoscraper.py`,
`clean_captures.py`) that no longer exist in `collector/backend/`. It now
calls the shared `collector.run` pipeline instead, so scheduled and manual
collection use the same config, window gate, parsers, store and provenance.

Example:
    python -m collector.backend.scheduler \
        --config collector/config/brazil-election-2026.yaml \
        --data-root ~/laclaugpt-brasil-data
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ..run import run_collection


def _log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m collector.backend.scheduler",
        description="Run one scheduled pass of the canonical LaclauGPT collector",
    )
    parser.add_argument(
        "--config",
        default="collector/config/brazil-election-2026.yaml",
        help="study YAML configuration",
    )
    parser.add_argument(
        "--data-root",
        default=str(Path.home() / "laclaugpt-brasil-data"),
        help="persistent collection data root",
    )
    parser.add_argument("--scrolls", type=int, default=None)
    parser.add_argument("--download-media", action="store_true")
    parser.add_argument("--media-workers", type=int, default=4)
    parser.add_argument(
        "--log",
        default=str(Path.home() / "laclaugpt-brasil-data" / "collector.log"),
    )
    args = parser.parse_args(argv)

    log_path = Path(args.log)
    _log(log_path, f"RUN config={args.config} data_root={args.data_root}")
    try:
        manifest = run_collection(
            args.config,
            args.data_root,
            scrolls=args.scrolls,
            download_media=args.download_media,
            media_workers=args.media_workers,
        )
    except Exception as exc:  # noqa: BLE001
        _log(log_path, f"ERROR {type(exc).__name__}: {exc}")
        raise

    if manifest.get("skipped"):
        _log(log_path, f"SKIP {manifest.get('reason', '')}")
    else:
        _log(
            log_path,
            "OK " + json.dumps({
                "run_id": manifest.get("run_id"),
                "new_posts": manifest.get("new_posts_total", 0),
                "seen_total": manifest.get("seen_total", 0),
                "errors": len(manifest.get("errors") or []),
            }, ensure_ascii=False),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
