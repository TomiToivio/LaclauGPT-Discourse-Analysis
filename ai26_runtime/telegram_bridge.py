#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI26 Telegram bridge: vasama_ai.events -> ai26_sources (adapter boundary).

The existing vasama_collect_telegram.py keeps collecting into vasama_ai.events.
This bridge converts new telegram-sourced events into canonical ai26 sources
using the laclaugpt collect adapter. No second telethon client.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/mnt/workspace/LaclauGPT-Discourse-Analysis")
sys.path.insert(0, "/mnt/workspace/LaclauGPT-Discourse-Analysis/ai26_runtime")

from mongo_writer import get_db  # noqa: E402

P = "ai26_"
STATE_ID = "telegram_bridge_state"


def main() -> int:
    db = get_db()
    # resume from last processed event timestamp
    state = db[P + "runs"].find_one({"run_id": STATE_ID}) or {}
    last_ts = state.get("last_event_ts")
    query = {"source_kind": {"$in": ["telegram", "telegram-channel"]}}
    if last_ts:
        query["published_at"] = {"$gt": last_ts}
    events = list(db[os.environ.get("AI26_UPSTREAM_DB", "vasama_ai")]
        ["events"].find(query).sort(
        "published_at", 1).limit(500))
    new = 0
    latest_ts = last_ts
    for ev in events:
        native_id = f"tg:{ev.get('event_id') or str(ev['_id'])}"
        if db[P + "sources"].find_one({"source_type": "telegram",
                                        "native_id": native_id}):
            continue
        doc = {
            "source_type": "telegram",
            "platform": "telegram",
            "native_id": native_id,
            "source_url": ev.get("url"),
            "title": (ev.get("title") or "")[:300] or None,
            "author_text": ev.get("actor_label") or ev.get("source"),
            "published_at": ev.get("published_at"),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "raw_text": ev.get("text"),
            "language": ev.get("language"),
            "metadata": {
                "arena": "grassroots",   # default; researcher re-tags freely
                "channel": ev.get("source"),
                "upstream_db": os.environ.get("AI26_UPSTREAM_DB", "vasama_ai") + ".events",
                "collection_provenance": ev.get("collection_provenance"),
            },
        }
        db[P + "sources"].insert_one(doc)
        new += 1
        if ev.get("published_at"):
            latest_ts = max(latest_ts or "", ev["published_at"])
    if latest_ts:
        db[P + "runs"].update_one(
            {"run_id": STATE_ID},
            {"$set": {"last_event_ts": latest_ts,
                       "updated": datetime.now(timezone.utc).isoformat()}},
            upsert=True)
    print(f"telegram bridge: +{new}")
    return new


if __name__ == "__main__":
    main()
