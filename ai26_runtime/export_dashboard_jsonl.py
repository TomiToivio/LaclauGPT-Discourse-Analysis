#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export ai26_annotations from MongoDB to canonical annotation JSONL per arena.

The dashboard (laclaugpt visualization) consumes canonical JSONL; this exporter
bridges the Laskin Mongo store to that existing input format. Written to
/mnt/workspace/LaclauGPT-Discourse-Analysis/collection-data/dashboard/<arena>.jsonl
(collection-data is gitignored — no research data in the repo).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/mnt/workspace/LaclauGPT-Discourse-Analysis/ai26_runtime")
sys.path.insert(0, "/mnt/workspace/LaclauGPT-Discourse-Analysis")

from mongo_writer import get_db  # noqa: E402

OUT_ROOT = Path("/mnt/workspace/LaclauGPT-Discourse-Analysis/collection-data/dashboard")


def main() -> None:
    db = get_db()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    per_arena: dict[str, int] = {}
    cursor = db.ai26_annotations.find({}, sort=[("created_at", 1)])
    for ann in cursor:
        arena = (ann.get("collection_provenance") or {}).get("arena") \
            or (db.ai26_sources.find_one(
                {"native_id": (ann.get("document_id") or "").split("::", 1)[-1]},
                {"metadata.arena": 1}).get("metadata") or {}).get("arena") \
            or "elites"
        # strip the Mongo _id — canonical interchange has no ObjectId
        ann.pop("_id", None)
        path = OUT_ROOT / f"{arena}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ann, ensure_ascii=False, default=str) + "\n")
        per_arena[arena] = per_arena.get(arena, 0) + 1
    print("exported:", per_arena)


if __name__ == "__main__":
    main()