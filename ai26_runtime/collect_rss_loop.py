#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI26 RSS collection loop: feeds.txt -> laclaugpt collect -> mongo_writer.

One process per timer tick; idempotent thanks to CollectionStore dedup
ledger + unique Mongo indexes. Arena comes from feeds.txt col 1.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/mnt/workspace/LaclauGPT-Discourse-Analysis")
from ai26_runtime.mongo_writer import ingest_jsonl, get_db  # noqa: E402

FEEDS = Path(os.environ.get("AI26_FEEDS",
        "~/.config/laclaugpt/ai26/feeds.txt"))
REPO = Path("/mnt/workspace/LaclauGPT-Discourse-Analysis")
STORE = REPO / "collection-data"


def collect_feed(arena: str, url: str, label: str) -> int:
    """Run laclaugpt collect rss for one feed; ingest result into Mongo."""
    before = STORE.glob("normalized/rss.jsonl")
    count_before = sum(1 for _ in open(next(before), encoding="utf-8")) if any(STORE.glob("normalized/rss.jsonl")) else 0
    result = subprocess.run(
        ["python3", "-m", "laclaugpt.cli", "collect", "rss", url,
         "--fetch-article"],
        cwd=REPO, capture_output=True, text=True, timeout=600)
    rss_file = STORE / "normalized" / "rss.jsonl"
    if not rss_file.exists():
        return 0
    count_after = sum(1 for _ in open(rss_file, encoding="utf-8"))
    if count_after <= count_before:
        return 0
    # read only the NEW lines and ingest with arena tag
    import json
    stats = {"saved": 0, "skipped": 0}
    with open(rss_file, encoding="utf-8") as fh:
        lines = fh.readlines()[count_before:]
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as tmp:
        tmp.writelines(lines)
        tmp_path = tmp.name
    try:
        stats = ingest_jsonl(tmp_path, arena=arena)
    finally:
        Path(tmp_path).unlink()
    return stats["saved"]


def main() -> None:
    db = get_db()
    total = 0
    for line in FEEDS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        arena, url, label = parts
        try:
            n = collect_feed(arena, url, label)
            total += n
            print(f"{label}: +{n}")
        except Exception as exc:
            print(f"{label}: ERROR {exc}")
    print(f"total new: {total}")


if __name__ == "__main__":
    main()
