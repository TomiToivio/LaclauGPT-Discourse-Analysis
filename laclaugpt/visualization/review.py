"""Separate local review notes for dashboard use.

Review notes intentionally do not mutate canonical analysis JSONL. They live in a
small SQLite sidecar that can be kept locally or on the dashboard web server.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReviewStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS dashboard_reviews (
                document_id TEXT PRIMARY KEY,
                review_status TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def get(self, document_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT review_status, note, tags, updated_at "
            "FROM dashboard_reviews WHERE document_id=?",
            (document_id,),
        ).fetchone()
        if not row:
            return {
                "document_id": document_id,
                "review_status": "",
                "note": "",
                "tags": [],
                "updated_at": "",
            }
        return {
            "document_id": document_id,
            "review_status": row[0],
            "note": row[1],
            "tags": [tag.strip() for tag in row[2].split(",") if tag.strip()],
            "updated_at": row[3],
        }

    def save(
        self,
        document_id: str,
        *,
        review_status: str = "",
        note: str = "",
        tags: list[str] | tuple[str, ...] = (),
    ) -> dict[str, Any]:
        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        normalized_tags = ",".join(sorted({str(tag).strip() for tag in tags if str(tag).strip()}))
        self.connection.execute(
            """
            INSERT INTO dashboard_reviews(document_id, review_status, note, tags, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                review_status=excluded.review_status,
                note=excluded.note,
                tags=excluded.tags,
                updated_at=excluded.updated_at
            """,
            (document_id, review_status, note, normalized_tags, updated_at),
        )
        self.connection.commit()
        return self.get(document_id)

    def dataframe_rows(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT document_id, review_status, note, tags, updated_at "
            "FROM dashboard_reviews ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {
                "document_id": row[0],
                "review_status": row[1],
                "note": row[2],
                "tags": row[3],
                "updated_at": row[4],
            }
            for row in rows
        ]
