#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical-corpus → ai26_sources (Mongo) ingestion sync (TASK3 #3).

Bridges the canonical collection spine (collection-data/normalized/*.jsonl —
RSS, social/Bluesky/Mastodon via the DAIR collector, web, minet) into the
same ai26_sources collection the RSS/Telegram/YouTube/Firefox collectors
use, so the shared incremental analysis worker picks everything up.

Dedup: source_type+native_id upsert with $setOnInsert, plus a seen-file
keyed by (dedup_id) so re-scanning old lines is cheap. Records without
usable text are skipped (analysis needs text).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get("LACLAUGPT_ROOT", "/mnt/workspace/LaclauGPT-Discourse-Analysis"))
sys.path.insert(0, str(REPO / "ai26_runtime"))
sys.path.insert(0, str(REPO))
os.environ.setdefault("AI26_DATA_ROOT", os.path.expanduser("~/laclaugpt-ai26-data"))

from mongo_writer import get_db, P  # noqa: E402

CANONICAL = REPO / "collection-data" / "normalized"
DATA_ROOT = Path(os.environ["AI26_DATA_ROOT"])
STATE = DATA_ROOT / "canonical_ingest_state.json"
INGEST_BATCH = int(os.environ.get("AI26_INGEST_BATCH", "500"))

# normalized-tiedosto → source_type -mappaus (canonical spine)
FILES: dict[str, str] = {
    "rss.jsonl": "rss",
    "social.jsonl": "social",
    "web.jsonl": "web",
    "minet.jsonl": "minet",
    "manual.jsonl": "manual",
}


def _doc(record: dict, source_type: str) -> dict | None:
    src = record.get("source") or {}
    text = src.get("raw_text") or ""
    native = src.get("native_id") or src.get("source_id")
    if not text or not native:
        return None
    meta = src.get("metadata") or {}
    ing = record.get("ingestion") or {}
    return {
        "source_type": source_type,
        "platform": src.get("platform") or source_type,
        "native_id": str(native),
        "title": (src.get("title") or "")[:300],
        "author_text": src.get("author_text") or "",
        "published_at": src.get("published_at") or "",
        "collected_at": (src.get("collected_at")
                         or datetime.now(timezone.utc).isoformat()),
        "source_url": src.get("source_url") or "",
        "normalized_source_url": src.get("normalized_source_url")
        or src.get("source_url") or "",
        "raw_text": text,
        "analysis_status": "pending",
        "metadata": {
            "arena": "elites",
            "channel": "canonical_sync",
            "study": "ai26",
            "collector": meta.get("collector") or src.get("platform") or source_type,
            "feed_name": meta.get("feed_name") or "",
            # sampling provenance — heuristics, never analytical labels
            "source_family": meta.get("source_source_family")
            or meta.get("source_family") or "",
            "sampling_stratum": meta.get("sampling_stratum") or "",
            "sampling_rationale": meta.get("source_sampling_rationale")
            or meta.get("sampling_rationale") or "",
            "source_priority": meta.get("source_priority") or "",
            "language": src.get("language") or "",
            "dedup_id": meta.get("dedup_id") or "",
        },
    }


def main() -> int:
    db = get_db()
    seen: dict = {}
    if STATE.exists():
        try:
            seen = json.loads(STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            seen = {}
    saved = 0
    per_file: dict[str, int] = {}
    for fname, source_type in sorted(FILES.items()):
        path = CANONICAL / fname
        if not path.exists():
            continue
        count = 0
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                dedup = ((record.get("source") or {}).get("metadata") or {}).get(
                    "dedup_id") or ((record.get("source") or {}).get(
                        "source_id") or "")
                key = f"{fname}:{dedup}"
                if seen.get(key):
                    continue
                doc = _doc(record, source_type)
                if not doc:
                    continue
                db[P + "sources"].update_one(
                    {"source_type": source_type, "native_id": doc["native_id"]},
                    {"$setOnInsert": doc}, upsert=True)
                seen[key] = 1
                count += 1
                if count >= INGEST_BATCH:
                    break
        if count:
            per_file[fname] = count
            saved += count
    STATE.write_text(json.dumps(seen), encoding="utf-8")
    print(f"canonical sync: saved={saved} per_file={per_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())