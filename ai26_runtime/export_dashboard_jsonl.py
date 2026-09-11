#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atomically export canonical AI26 annotations from MongoDB for the dashboard.

The dashboard polls these files. Each arena is written to a temporary file and
replaced atomically only after the export succeeds, so readers never observe a
half-truncated JSONL file. Concrete deployment paths and credentials stay outside
this public module.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TextIO

REPO = Path(
    os.environ.get("LACLAUGPT_ROOT", str(Path(__file__).resolve().parents[1]))
).expanduser().resolve()
sys.path.insert(0, str(REPO / "ai26_runtime"))
sys.path.insert(0, str(REPO))

from mongo_writer import get_db  # noqa: E402

OUT_ROOT = Path(
    os.environ.get(
        "AI26_DASHBOARD_EXPORT_ROOT",
        str(REPO / "collection-data" / "dashboard"),
    )
).expanduser()


def _arena_for_annotation(db, annotation: dict) -> str:
    provenance = annotation.get("collection_provenance") or {}
    arena = provenance.get("arena_id") or provenance.get("arena")
    if arena:
        return str(arena)
    document_id = str(annotation.get("document_id") or "")
    native_id = document_id.split("::", 1)[-1]
    source = db.ai26_sources.find_one(
        {"native_id": native_id},
        {"metadata.arena": 1},
    ) or {}
    return str((source.get("metadata") or {}).get("arena") or "elites")


def main() -> None:
    db = get_db()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    handles: dict[str, TextIO] = {}
    temp_paths: dict[str, Path] = {}
    counts: dict[str, int] = {}
    pid = os.getpid()

    try:
        cursor = db.ai26_annotations.find({}, sort=[("created_at", 1)])
        for annotation in cursor:
            arena = _arena_for_annotation(db, annotation)
            if arena not in handles:
                temp_path = OUT_ROOT / f".{arena}.jsonl.tmp-{pid}"
                handles[arena] = temp_path.open("w", encoding="utf-8")
                temp_paths[arena] = temp_path
                counts[arena] = 0
            annotation.pop("_id", None)
            handles[arena].write(
                json.dumps(annotation, ensure_ascii=False, default=str) + "\n"
            )
            counts[arena] += 1

        for handle in handles.values():
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()

        for arena, temp_path in temp_paths.items():
            os.replace(temp_path, OUT_ROOT / f"{arena}.jsonl")
    finally:
        for handle in handles.values():
            if not handle.closed:
                handle.close()
        for temp_path in temp_paths.values():
            if temp_path.exists():
                temp_path.unlink()

    print("exported:", counts)


if __name__ == "__main__":
    main()
