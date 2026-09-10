# -*- coding: utf-8 -*-
"""AI26 canonical writer: CollectRecord-shaped dicts -> MongoDB.

Reads the JSONL produced by `laclaugpt collect ...` (source+ingestion pairs)
and upserts into prefixed collections. Concrete database names, endpoints and
credentials are runtime configuration and must not be committed.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from pymongo import MongoClient

CONFIG = Path(os.environ.get(
    "AI26_CONFIG", "~/.config/laclaugpt/ai26/ai26.yaml"
)).expanduser()
DATABASE = os.environ.get("AI26_MONGO_DATABASE", "laclaugpt")
P = "ai26_"


def _mongo_uri() -> str:
    text = CONFIG.read_text(encoding="utf-8")
    match = re.search(r'uri: "(mongodb://[^"]+)"', text)
    if not match:
        raise RuntimeError(f"MongoDB URI missing from private config: {CONFIG}")
    return match.group(1)


def get_db():
    client = MongoClient(_mongo_uri(), serverSelectionTimeoutMS=5000)
    return client[DATABASE]


def ingest_jsonl(path: str, arena: str | None = None) -> dict:
    db = get_db()
    saved = skipped = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            payload = json.loads(line)
            source = payload["source"]
            ingestion = payload["ingestion"]
            source["metadata"]["arena"] = arena or source.get("metadata", {}).get("arena")
            source["metadata"]["ingestion_id"] = ingestion["ingestion_id"]
            native_id = source.get("native_id")
            url = source.get("normalized_source_url")
            conds = []
            if native_id is not None:
                conds.append({"native_id": native_id})
            if url:
                conds.append({"normalized_source_url": url})
            if not conds:
                conds = [{"native_id": {"$exists": True, "$eq": None},
                          "source_type": source["source_type"]}]
            result = db[P + "sources"].update_one(
                {"source_type": source["source_type"], "$or": conds},
                {"$setOnInsert": source},
                upsert=True)
            if result.upserted_id:
                saved += 1
                db[P + "ingestion"].insert_one(ingestion)
            else:
                skipped += 1
    return {"saved": saved, "skipped": skipped}


def ingest_registry_entry(arena: str, source_url: str, label: str = "",
                          source_type: str = "rss") -> None:
    db = get_db()
    db[P + "registry"].update_one(
        {"source_url": source_url},
        {"$set": {"arena": arena, "label": label,
                   "source_type": source_type, "enabled": True}},
        upsert=True)
