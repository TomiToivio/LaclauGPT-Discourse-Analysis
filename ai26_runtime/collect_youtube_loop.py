#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI26 YouTube collection: official channel RSS -> metadata -> Mongo.

Hierarchy level 1 (per issue #73 task): official YouTube channel RSS for
new-video detection. Transcript retrieval is a later stage (level 3).
Format of youtube.txt: arena<TAB>channel_rss_url<TAB>label
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, "/mnt/workspace/LaclauGPT-Discourse-Analysis")
sys.path.insert(0, "/mnt/workspace/LaclauGPT-Discourse-Analysis/ai26_runtime")

import feedparser  # noqa: E402
from mongo_writer import get_db  # noqa: E402

FEEDS = Path(os.environ.get("AI26_FEEDS",
        "~/.config/laclaugpt/ai26/feeds.txt"))
P = "ai26_"


def collect_youtube() -> int:
    db = get_db()
    total = 0
    for line in FEEDS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        arena, url = parts[0], parts[1]
        label = parts[2] if len(parts) > 2 else url
        try:
            parsed = feedparser.parse(url)
        except Exception as exc:
            print(f"{label}: PARSE ERROR {exc}")
            continue
        new = 0
        for entry in parsed.entries:
            video_id = getattr(entry, "yt_videoid", None) or (
                entry.get("id", "").replace("yt:video:", "") or None)
            if not video_id:
                continue
            native_id = f"yt:{video_id}"
            existing = db[P + "sources"].find_one(
                {"source_type": "youtube", "native_id": native_id})
            if existing:
                continue
            doc = {
                "source_type": "youtube",
                "platform": "youtube",
                "native_id": native_id,
                "source_url": f"https://www.youtube.com/watch?v={video_id}",
                "normalized_source_url": f"https://www.youtube.com/watch?v={video_id}",
                "title": (entry.get("title") or "")[:300] or None,
                "author_text": entry.get("author") or None,
                "published_at": entry.get("published") or None,
                "collected_at": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc).isoformat(),
                "raw_text": (entry.get("summary") or "")[:5000] or None,
                "metadata": {
                    "arena": arena,
                    "channel_label": label,
                    "channel_rss": url,
                    "transcript": None,  # level 3: fetched later
                },
            }
            db[P + "sources"].insert_one(doc)
            new += 1
        total += new
        print(f"{label}: +{new}")
    return total


if __name__ == "__main__":
    n = collect_youtube()
    print(f"total new: {n}")
