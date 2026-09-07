"""Durable storage: raw/ normalized/ manifests/ + SQLite state.

Layout (created under one data root):

    <root>/raw/<platform>/<YYYYMMDD>/capture-<n>.ndjson
        exact captured payloads, append-only, one JSON object per line
    <root>/normalized/<platform>.jsonl
        stable normalised records (deduplicated by platform+document_id)
    <root>/manifests/run-<UTC stamp>.json
        per-run manifest: config, git SHA, per-account results, errors
    <root>/state.sqlite3
        collection state: seen posts, per-account checkpoints, media index
"""
from __future__ import annotations

import itertools
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class Store:
    """Filesystem-backed collection store (S3-swappable interface)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.raw_dir = self.root / "raw"
        self.normalized_dir = self.root / "normalized"
        self.manifests_dir = self.root / "manifests"
        self.media_dir = self.root / "media"
        for directory in (self.raw_dir, self.normalized_dir,
                          self.manifests_dir, self.media_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.root / "state.sqlite3",
                                   check_same_thread=False)
        self._db_lock = threading.Lock()
        # A long-running Firefox backend can exceed 65,536 captures. The old
        # iter(range(0x10000)) silently became StopIteration at that point.
        self._counter = itertools.count()
        self._closed = False
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS seen_posts (
                platform TEXT NOT NULL,
                document_id TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                normalized_ref TEXT,
                PRIMARY KEY (platform, document_id)
            )""")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                account TEXT NOT NULL,
                platform TEXT NOT NULL,
                cursor TEXT,
                last_run TEXT,
                last_status TEXT,
                PRIMARY KEY (account, platform)
            )""")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS media_index (
                media_key TEXT PRIMARY KEY,
                platform TEXT, document_id TEXT, media_index INTEGER,
                url TEXT, local_path TEXT, sha256 TEXT,
                byte_size INTEGER, mime_type TEXT,
                status TEXT, failure_reason TEXT, http_status INTEGER,
                downloaded_at TEXT
            )""")
        self._db.commit()

    # -- raw layer ------------------------------------------------------

    def append_raw(self, platform: str, payload: dict) -> str:
        """Append one raw capture; returns the raw_ref pointer."""
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        directory = self.raw_dir / platform / day
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"capture-{utc_stamp()}-{next(self._counter):08x}.ndjson"
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        return str(path.relative_to(self.root))

    # -- normalized layer ----------------------------------------------

    def upsert_post(self, record: dict, raw_ref: str) -> bool:
        """Insert a normalised record if new; returns True when inserted."""
        key = (record["platform"], record["document_id"])
        with self._db_lock:
            cur = self._db.execute(
                "SELECT 1 FROM seen_posts WHERE platform=? AND document_id=?",
                key)
            if cur.fetchone():
                return False
            path = self.normalized_dir / f"{record['platform']}.jsonl"
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({**record, "raw_ref": raw_ref},
                                        ensure_ascii=False, default=str) + "\n")
            self._db.execute(
                "INSERT INTO seen_posts (platform, document_id, first_seen, normalized_ref)"
                " VALUES (?, ?, ?, ?)",
                (record["platform"], record["document_id"],
                 datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 str(path.relative_to(self.root))))
            self._db.commit()
        return True

    def seen_count(self, platform: str | None = None) -> int:
        with self._db_lock:
            if platform:
                cur = self._db.execute(
                    "SELECT COUNT(*) FROM seen_posts WHERE platform=?", (platform,))
            else:
                cur = self._db.execute("SELECT COUNT(*) FROM seen_posts")
            return cur.fetchone()[0]

    # -- checkpoints ----------------------------------------------------

    def checkpoint(self, account: str, platform: str,
                   cursor: str | None = None, status: str = "ok") -> None:
        with self._db_lock:
            self._db.execute("""
                INSERT INTO checkpoints (account, platform, cursor, last_run, last_status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(account, platform) DO UPDATE SET
                    cursor=excluded.cursor, last_run=excluded.last_run,
                    last_status=excluded.last_status
            """, (account, platform, cursor,
                  datetime.now(timezone.utc).isoformat(timespec="seconds"), status))
            self._db.commit()

    def get_cursor(self, account: str, platform: str) -> str | None:
        with self._db_lock:
            cur = self._db.execute(
                "SELECT cursor FROM checkpoints WHERE account=? AND platform=?",
                (account, platform))
            row = cur.fetchone()
            return row[0] if row else None

    def failing_accounts(self) -> list[tuple]:
        with self._db_lock:
            cur = self._db.execute(
                "SELECT account, platform, last_status FROM checkpoints"
                " WHERE last_status != 'ok'")
            return cur.fetchall()

    # -- media index ----------------------------------------------------

    def media_known(self, media_key: str) -> dict | None:
        with self._db_lock:
            cur = self._db.execute(
                "SELECT local_path, sha256, status FROM media_index WHERE media_key=?",
                (media_key,))
            row = cur.fetchone()
            if not row:
                return None
            return {"local_path": row[0], "sha256": row[1], "status": row[2]}

    def record_media(self, media_key: str, platform: str, document_id: str,
                     media_index: int, url: str, local_path: str | None,
                     sha256: str | None, byte_size: int | None, mime_type: str,
                     status: str, failure_reason: str | None = None,
                     http_status: int | None = None) -> None:
        with self._db_lock:
            self._db.execute("""
                INSERT OR REPLACE INTO media_index
                (media_key, platform, document_id, media_index, url, local_path,
                 sha256, byte_size, mime_type, status, failure_reason, http_status,
                 downloaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (media_key, platform, document_id, media_index, url, local_path,
                  sha256, byte_size, mime_type, status, failure_reason, http_status,
                  datetime.now(timezone.utc).isoformat(timespec="seconds")))
            self._db.commit()

    # -- manifests ------------------------------------------------------

    def write_manifest(self, manifest: dict) -> Path:
        path = self.manifests_dir / f"run-{utc_stamp()}.json"
        if path.exists():
            # Multiple short test/manual runs can finish within one second.
            index = 1
            while True:
                candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
                if not candidate.exists():
                    path = candidate
                    break
                index += 1
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1,
                                   default=str), encoding="utf-8")
        return path

    def close(self) -> None:
        if self._closed:
            return
        with self._db_lock:
            self._db.close()
            self._closed = True
