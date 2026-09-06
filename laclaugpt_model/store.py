# -*- coding: utf-8 -*-
"""Parquet/Arrow bulk export + SQLite persistence for the canonical model.

Pydantic -> JSON (API/agents) and Parquet (bulk analysis). Storage
lives in LACLAUGPT_MEMORY_DIR-style persistent dirs so Roihu batch jobs
keep state across jobs.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from laclaugpt_model import (Actor, AnalysisResult, Annotation, Concept,
                             Document, Relation, Statement)

SCHEMA = {
    "documents": ["id", "type", "text", "author_id", "published_at", "source",
                  "url", "parent_id", "metadata"],
    "actors": ["id", "type", "name", "aliases", "attributes"],
    "concepts": ["id", "label", "description", "aliases", "embedding", "attributes"],
    "annotations": ["id", "document_id", "start", "end", "type", "value",
                    "confidence", "analysis_run_id", "attributes"],
    "statements": ["id", "document_id", "actor_id", "concept_id", "stance",
                   "stance_score", "timestamp", "evidence_span", "confidence",
                   "qualifiers", "analysis_run_id"],
    "relations": ["id", "source_id", "target_id", "type", "weight", "polarity",
                  "timestamp", "evidence_ids", "analysis_run_id", "properties"],
    "analysis_runs": ["id", "method", "model", "model_version", "prompt_id",
                      "parameters", "software_version", "created_at", "operator", "notes"],
    "analysis_results": ["id", "subject_id", "classification", "score", "method",
                         "analysis_run_id", "evidence_ids", "timestamp", "notes"],
}

_JSON_FIELDS = {"metadata", "attributes", "aliases", "embedding", "qualifiers",
                "evidence_ids", "evidence_span", "parameters", "properties"}


def init_sqlite(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    for table, cols in SCHEMA.items():
        types = {"id": "TEXT PRIMARY KEY", "start": "INTEGER", "end": "INTEGER",
                 "confidence": "REAL", "stance_score": "REAL", "weight": "REAL",
                 "polarity": "REAL", "score": "REAL"}
        defs = ", ".join(f"{c} {types.get(c, 'TEXT')}" for c in cols)
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({defs})")
    return conn


def upsert(conn: sqlite3.Connection, table: str, rows: Iterable[dict]) -> int:
    cols = SCHEMA[table]
    n = 0
    for row in rows:
        vals = []
        for c in cols:
            v = row.get(c)
            if c in _JSON_FIELDS and isinstance(v, (dict, list, tuple)):
                v = json.dumps(v, ensure_ascii=False)
            vals.append(v)
        conn.execute(
            f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' * len(cols))})", vals)
        n += 1
    conn.commit()
    return n


def model_to_row(model) -> dict:
    d = model.model_dump(mode="json")
    if "evidence_span" in d and d["evidence_span"] is not None:
        d["evidence_span"] = json.dumps(d["evidence_span"])
    return d


def _flatten_row(row: dict, cols: list[str]) -> dict:
    """Parquet-flat rows: any non-scalar (dict/list/tuple) becomes a JSON
    string. Keeps the Arrow schema stable regardless of content."""
    out = {}
    for c in cols:
        v = row.get(c)
        if isinstance(v, (dict, list, tuple)):
            v = json.dumps(v, ensure_ascii=False)
        out[c] = v
    return out


def export_parquet(tables: dict[str, list[dict]], out_dir: str) -> list[str]:
    """Bulk analytical export. Falls back to JSONL when pyarrow is
    absent (Slurm-safe)."""
    out = []
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        for name, rows in tables.items():
            cols = SCHEMA[name]
            flat = [_flatten_row(r, cols) for r in rows]
            data = {c: [r[c] for r in flat] for c in cols}
            p = outp / f"{name}.parquet"
            pq.write_table(pa.table(data), str(p))
            out.append(str(p))
        return out
    except ImportError:
        for name, rows in tables.items():
            p = outp / f"{name}.jsonl"
            with open(p, "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            out.append(str(p))
        return out