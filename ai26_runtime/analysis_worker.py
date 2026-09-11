#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI26 incremental analysis worker: ai26_sources -> canonical pipeline -> ai26_annotations.

Local Ollama only. Stage-aware local model routing is resolved by
pipeline.Stage.call via laclaugpt.model_routing. No cloud fallback.

Failure semantics:
- if the pipeline subprocess fails, documents are marked analysis_status=error
  with the stderr tail, NOT done;
- documents are marked done only after their annotations were actually written;
- every tick appends a run record for observability.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(os.environ.get(
    "LACLAUGPT_ROOT", str(Path(__file__).resolve().parents[1])
)).expanduser().resolve()
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ai26_runtime"))

os.environ["LLM_MODE"] = "local"
os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:11434")
os.environ.setdefault("OLLAMA_KEEP_ALIVE", "24h")
os.environ.pop("LLM_ALLOW_CLOUD_FALLBACK", None)

from mongo_writer import get_db  # noqa: E402

P = "ai26_"
BATCH = int(os.environ.get("AI26_BATCH", "10"))


def pick_unanalyzed(arena: str | None = None) -> list[dict]:
    db = get_db()
    query = {"analysis_status": {"$ne": "done"}}
    if arena:
        query["metadata.arena"] = arena
    return list(db[P + "sources"].find(query)
                .sort([("analysis_status", 1), ("collected_at", 1)])
                .limit(BATCH))


def run_pipeline(docs: list[dict]) -> dict:
    """Build a canonical CSV from the docs and run pipeline.py."""
    db = get_db()
    arena = (docs[0].get("metadata") or {}).get("arena", "elites")
    run_config = REPO / "run_configs" / f"arena_{arena}.yaml"
    if not run_config.exists():
        run_config = REPO / "run_configs" / "arena_elites.yaml"
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as tmp:
        import csv as csvmod
        writer = csvmod.writer(tmp)
        writer.writerow(["document_id", "text", "url", "author",
                         "created_at", "source_platform"])
        ids = []
        for d in docs:
            did = d["native_id"]
            ids.append(did)
            writer.writerow([
                did,
                d.get("raw_text") or d.get("title") or "",
                d.get("source_url") or "",
                d.get("author_text") or "",
                d.get("published_at") or "",
                d.get("source_type") or ""])
        csv_path = tmp.name
    out_jsonl = tempfile.mktemp(suffix=".jsonl")
    started = datetime.now(timezone.utc)
    run_id = f"ai26-incr-{started.strftime('%Y%m%dT%H%M%S')}"
    try:
        result = subprocess.run(
            ["python3", "pipeline.py", "--run-config", str(run_config),
             "--csv", csv_path, "--output", out_jsonl],
            cwd=REPO, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired as exc:
        _mark_error(db, ids, f"pipeline timeout after 3600s: {exc}")
        _record_run(db, run_id, arena, len(docs), 0, "timeout", started)
        return {"docs": len(docs), "annotated": 0, "status": "timeout"}
    except Exception as exc:
        _mark_error(db, ids, f"pipeline spawn failed: {exc}")
        _record_run(db, run_id, arena, len(docs), 0, "spawn_error", started)
        return {"docs": len(docs), "annotated": 0, "status": "spawn_error"}

    annotated_ids: list[str] = []
    stats = {"docs": len(docs), "annotated": 0, "status": "ok"}
    if result.returncode != 0:
        stats["status"] = "pipeline_error"
        tail = (result.stderr or result.stdout or "")[-1500:]
        _mark_error(db, ids, tail)
        _record_run(db, run_id, arena, len(docs), 0, "pipeline_error", started,
                    stderr_tail=tail)
    elif Path(out_jsonl).exists():
        from laclaugpt_interchange import from_jsonl
        annotations = from_jsonl(out_jsonl)
        for ann in annotations:
            payload = ann.model_dump(mode="json")
            db2 = get_db()
            db2[P + "annotations"].update_one(
                {"document_id": ann.document_id, "run_id": ann.run_id},
                {"$set": payload}, upsert=True)
            stats["annotated"] += 1
            annotated_ids.append(ann.document_id)
        Path(out_jsonl).unlink()
        if annotated_ids:
            bare = [a.split("::", 1)[1] for a in annotated_ids if "::" in a]
            match_ids = list(dict.fromkeys(annotated_ids + bare))
            db[P + "sources"].update_many(
                {"$or": [{"native_id": {"$in": match_ids}},
                          {"source_url": {"$in": match_ids}},
                          {"normalized_source_url": {"$in": match_ids}}]},
                {"$set": {"analysis_status": "done",
                          "analyzed_at": datetime.now(timezone.utc).isoformat()}})
    else:
        stats["status"] = "no_output"
        _mark_error(db, ids, "pipeline produced no output file")
        _record_run(db, run_id, arena, len(docs), 0, "no_output", started)
    if stats.get("status") == "ok":
        _record_run(db, run_id, arena, len(docs), stats["annotated"], "ok",
                    started)
    Path(csv_path).unlink()
    return stats


def _mark_error(db, ids: list[str], reason: str) -> None:
    if not ids:
        return
    db[P + "sources"].update_many(
        {"native_id": {"$in": ids}},
        {"$set": {"analysis_status": "error",
                  "analysis_error": (reason or "")[-1000:]}})


def _record_run(db, run_id: str, arena: str, docs: int, annotated: int,
                status: str, started: datetime, stderr_tail: str = "") -> None:
    db[P + "runs"].insert_one({
        "run_id": run_id,
        "kind": "incremental_analysis",
        "arena": arena,
        "docs": docs,
        "annotated": annotated,
        "status": status,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "stderr_tail": stderr_tail[-500:],
    })


def main() -> None:
    docs = pick_unanalyzed()
    if not docs:
        print("nothing to analyze")
        return
    try:
        stats = run_pipeline(docs)
        print(f"analysis: {stats}")
    except Exception:
        print("worker crashed:", traceback.format_exc()[-1500:])
        raise


if __name__ == "__main__":
    main()
