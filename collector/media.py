"""Optional media downloading — queued, checksummed, deduplicated.

Downloads public media referenced by captured posts. Browser capture finishes
first; media downloads run afterwards in a worker pool. Storage is behind a
small backend interface so filesystem output can later be replaced by Allas/S3.
"""
from __future__ import annotations

import hashlib
import mimetypes
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Iterable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .store import Store

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) LaclauGPT-Collector/0.1 "
              "(research; contact tomi.toivio@helsinki.fi)")
DEFAULT_WORKERS = 4


class MediaBackend:
    """Storage interface — filesystem now, CSC Allas/S3 later."""

    def save(self, key: str, data: bytes, mime_type: str) -> str:
        """Persist bytes and return a stable path/URI stored in the media index."""
        raise NotImplementedError

    def exists(self, key: str) -> bool:  # pragma: no cover - interface method
        raise NotImplementedError


class FilesystemBackend(MediaBackend):
    def __init__(self, root: Path, reference_root: Path | None = None) -> None:
        self.root = Path(root)
        self.reference_root = Path(reference_root) if reference_root else self.root.parent
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, key: str, data: bytes, mime_type: str) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(path)
        try:
            return path.relative_to(self.reference_root).as_posix()
        except ValueError:
            return str(path)

    def exists(self, key: str) -> bool:
        return (self.root / key).exists()


class MediaDownloader:
    """Queue-driven media fetcher with sha256 checksums and dedup."""

    def __init__(self, store: Store, backend: MediaBackend | None = None,
                 workers: int = DEFAULT_WORKERS,
                 fetcher: Callable[[str], tuple[bytes, str]] | None = None) -> None:
        self.store = store
        self.backend = backend or FilesystemBackend(store.media_dir, store.root)
        self.workers = workers
        self._fetcher = fetcher

    def enqueue_from_records(self, records: Iterable[dict]) -> list[dict]:
        jobs: list[dict] = []
        queued = set()
        for rec in records:
            for ref in rec.get("media_references", []):
                media_key = f"{rec['platform']}_{rec['document_id']}_{ref['media_index']}"
                if media_key in queued:
                    continue
                known = self.store.media_known(media_key)
                if known and known.get("status") == "ok":
                    continue
                queued.add(media_key)
                jobs.append({
                    "media_key": media_key,
                    "platform": rec["platform"],
                    "document_id": rec["document_id"],
                    "media_index": ref["media_index"],
                    "kind": ref["kind"],
                    "url": ref["url"],
                })
        return jobs

    def run_queue(self, jobs: list[dict]) -> list[dict]:
        results: list[dict] = []
        if not jobs:
            return results
        lock = threading.Lock()

        def work(job: dict) -> None:
            outcome = self._download_one(job)
            with lock:
                results.append(outcome)

        with ThreadPoolExecutor(max_workers=max(1, self.workers)) as pool:
            list(pool.map(work, jobs))
        return results

    def _download_one(self, job: dict) -> dict:
        key = job["media_key"]
        try:
            body, mime = self._fetch(job["url"])
        except Exception as exc:  # noqa: BLE001
            http_status = exc.code if isinstance(exc, HTTPError) else None
            failure = {
                "media_key": key,
                "status": "failed",
                "failure_reason": str(exc)[:200],
                "http_status": http_status,
                "local_path": None,
                "sha256": None,
                "byte_size": None,
                "mime_type": None,
            }
            self.store.record_media(
                key, job["platform"], job["document_id"], job["media_index"],
                job["url"], None, None, None, "", "failed",
                failure["failure_reason"], http_status)
            return failure

        sha = hashlib.sha256(body).hexdigest()
        known = self.store.media_known(key)
        if known and known.get("sha256") == sha and known.get("status") == "ok":
            return {
                "media_key": key,
                "status": "duplicate",
                "sha256": sha,
                "local_path": known["local_path"],
            }

        mime = (mime or "application/octet-stream").split(";", 1)[0].strip()
        ext = (mimetypes.guess_extension(mime) or "").replace(".jpe", ".jpg")
        fname = f"{key}{ext}"
        local_path = self.backend.save(fname, body, mime)

        self.store.record_media(
            key, job["platform"], job["document_id"], job["media_index"],
            job["url"], local_path, sha, len(body), mime, "ok", None, 200)
        return {
            "media_key": key,
            "status": "ok",
            "sha256": sha,
            "byte_size": len(body),
            "mime_type": mime,
            "local_path": local_path,
            "http_status": 200,
        }

    def _fetch(self, url: str) -> tuple[bytes, str]:
        if self._fetcher is not None:
            return self._fetcher(url)
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=120) as resp:
            mime = resp.headers.get("Content-Type", "") or "application/octet-stream"
            return resp.read(), mime
