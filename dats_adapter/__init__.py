# -*- coding: utf-8 -*-
"""DATS adapter — importer/exporter over the LaclauGPT interchange schema.

DATS (uhh-lt/dats) is the qualitative/discourse workbench layer; it runs
on its own server. LaclauGPT does NOT live inside DATS: DATS consumes
LaclauGPT annotations (and hands documents/concepts back).

Concept Over Time (DATS) ↔ LaclauGPT canonical signifier:
  a DATS concept (definition + feedback) maps to a canonical
  signifier/topic object; articulations-over-time come back as
  annotations referencing the same stable IDs.

Import (DATS → LaclauGPT):
  - documents: DATS corpus export (JSONL with id/text) → analysis input
  - concepts: DATS concept list → provisional signifiers/topics

Export (LaclauGPT → DATS):
  - interchange JSONL → DATS importable JSONL annotations
  - concept timelines: articulations per signifier over time
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from laclaugpt_interchange import DocumentAnnotation, MemoryRef, from_jsonl


def import_dats_documents(jsonl_path: str) -> list[dict]:
    """DATS corpus export → LaclauGPT analysis-ready rows.
    Expected DATS fields (tolerant): id/document_id, text/body/content."""
    rows = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            item = json.loads(line)
            doc_id = str(item.get("id") or item.get("document_id") or "")
            text = item.get("text") or item.get("body") or item.get("content") or ""
            if doc_id and text.strip():
                rows.append({"id": doc_id, "body": text,
                             "source_platform": "dats"})
    return rows


def import_dats_concepts(concepts_jsonl: str, memory) -> list[str]:
    """DATS concepts → PROVISIONAL signifiers in laclaugpt_memory.
    Expected: {"concept_id": "...", "label": "...", "definition": "..."}
    Returns the created/reused obj_ids."""
    ids = []
    with open(concepts_jsonl, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            c = json.loads(line)
            res = memory.resolve(c.get("label", ""), kind="signifier",
                                 definition=c.get("definition", ""),
                                 stage="dats-import", video_key="",
                                 evidence="DATS concept")
            ids.append(res.obj_id)
    return ids


def export_for_dats(annotations_path: str, out_path: str,
                    concept_obj_id: str) -> int:
    """Concept Over Time feed: all articulations of one canonical concept
    over time, DATS-ingestible JSONL."""
    count = 0
    events_all = []
    for ann in from_jsonl(annotations_path):
        for art in ann.articulations:
            if art.signifier.obj_id == concept_obj_id:
                events_all.append({
                    "document_id": ann.document_id,
                    "created_at": ann.created_at,
                    "raw": art.signifier.raw,
                    "relation": art.relation,
                    "related": [r.obj_id for r in art.related_to],
                    "evidence": art.evidence,
                    "concept_obj_id": concept_obj_id,
                })
    with open(out_path, "w", encoding="utf-8") as fh:
        for e in events_all:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return len(events_all)


def concept_over_time(annotations_path: str, concept_obj_id: str) -> list[dict]:
    """Return the concept's articulation timeline (raw forms + docs)."""
    rows = []
    for ann in from_jsonl(annotations_path):
        for art in ann.articulations:
            if art.signifier.obj_id == concept_obj_id:
                rows.append({"document_id": ann.document_id,
                             "created_at": ann.created_at,
                             "raw": art.signifier.raw,
                             "relation": art.relation,
                             "evidence": art.evidence,
                             "concept_obj_id": concept_obj_id,
                             "schema_version": ann.schema_version})
    rows.sort(key=lambda r: r["created_at"])
    return rows