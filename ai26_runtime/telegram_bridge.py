#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI26 Telegram bridge: upstream event collection -> canonical sources.

The upstream collection name is deployment configuration. This public adapter
contains no production database name, hostname or account information.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get("LACLAUGPT_ROOT", str(Path(__file__).resolve().parents[1]))).expanduser().resolve()
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ai26_runtime"))

from mongo_writer import get_db  # noqa: E402

P = "ai26_"
STATE_ID = "telegram_bridge_state"
UPSTREAM_COLLECTION = os.environ.get("AI26_UPSTREAM_COLLECTION", "events")


def main() -> int:
    db = get_db()
    state = db[P + "runs"].find_one({"run_id": STATE_ID}) or {}
    last_ts = state.get("last_event_ts")
    query = {"source_kind": {"$in": ["telegram", "telegram-channel"]}}
    if last_ts:
        query["published_at"] = {"$gt": last_ts}
    events = list(db[UPSTREAM_COLLECTION].find(query).sort(
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
                "arena": "grassroots",
                "channel": ev.get("source"),
                "upstream_collection": UPSTREAM_COLLECTION,
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
