#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export canonical annotations from MongoDB to dashboard JSONL per arena.

The output root is configurable and defaults to the repository's gitignored
`collection-data/dashboard` directory. Concrete deployment paths stay outside
this public module.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(os.environ.get("LACLAUGPT_ROOT", str(Path(__file__).resolve().parents[1]))).expanduser().resolve()
sys.path.insert(0, str(REPO / "ai26_runtime"))
sys.path.insert(0, str(REPO))

from mongo_writer import get_db  # noqa: E402

OUT_ROOT = Path(os.environ.get(
    "AI26_DASHBOARD_EXPORT_ROOT",
    str(REPO / "collection-data" / "dashboard"),
)).expanduser()


def main() -> None:
    db = get_db()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    per_arena: dict[str, int] = {}
    cursor = db.ai26_annotations.find({}, sort=[("created_at", 1)])
    for ann in cursor:
        source = db.ai26_sources.find_one(
            {"native_id": (ann.get("document_id") or "").split("::", 1)[-1]},
            {"metadata.arena": 1},
        ) or {}
        arena = (ann.get("collection_provenance") or {}).get("arena") \
            or (source.get("metadata") or {}).get("arena") \
            or "elites"
        ann.pop("_id", None)
        path = OUT_ROOT / f"{arena}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ann, ensure_ascii=False, default=str) + "\n")
        per_arena[arena] = per_arena.get(arena, 0) + 1
    print("exported:", per_arena)


if __name__ == "__main__":
    main()
