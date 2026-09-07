"""Optional media downloading — queued, checksummed, deduplicated.

Downloads public media referenced by captured posts. Never blocks
browser capture: the runner collects first, then hands the media queue
to this module, which works asynchronously (thread pool).

Design rules (issue #20):
- deterministic collision-resistant names: platform_postID_mediaIndex.ext
- no captions/unsafe strings in filenames
- duplicate prevention via the store media_index; a retry never creates
  a second copy of an already verified file
- signed CDN URLs expire (TikTok/Instagram): download near capture time
- failures are recorded per object; the post metadata stays intact
- media never committed to Git (data root lives outside the repo)
"""
from __future__ import annotations

import hashlib
import mimetypes
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Iterable
from urllib.request import Request, urlopen

from .store import Store

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) LaclauGPT-Collector/0.1 "
              "(research; contact tomi.toivio@helsinki.fi)")
CHUNK = 64 * 1024
DEFAULT_WORKERS = 4


class MediaBackend:
    """Storage interface — filesystem now, CSC Allas/S3 later."""

    def save(self, key: str, data: bytes, mime_type: str) -> str:
        raise NotImplementedError

    def exists(self, key: str) -> bool:  # pragma: no cover - trivial
        raise NotImplementedError


class FilesystemBackend(MediaBackend):
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def save(self, key: str, mime_type: str) -> str:  # type: ignore[override]
        path = self.root / key
        return str(path)

    def exists(self, key: str) -> bool:
        return (self.root / key).exists()


class MediaDownloader:
    """Queue-driven media fetcher with sha256 checksums and dedup."""

    def __init__(self, store: Store, backend: MediaBackend | None = None,
                 workers: int = DEFAULT_WORKERS,
                 fetcher: Callable[[str], tuple[bytes, str]] | None = None) -> None:
        self.store = store
        self.backend = backend or FilesystemBackend(store.media_dir)
        self.workers = workers
        self._fetcher = fetcher  # injectable for tests (mocked HTTP)

    # -- queue -----------------------------------------------------------

    def enqueue_from_records(self, records: Iterable[dict]) -> list[dict]:
        jobs: list[dict] = []
        for rec in records:
            for ref in rec.get("media_references", []):
                media_key = f"{rec['platform']}_{rec['document_id']}_{ref['media_index']}"
                known = self.store.media_known(media_key)
                if known and known.get("status") == "ok":
                    continue  # verified copy exists; never re-download
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
        """Process the queue concurrently; returns per-object outcomes."""
        results: list[dict] = []
        if not jobs:
            return results
        lock = threading.Lock()

        def work(job: dict) -> None:
            outcome = self._download_one(job)
            with lock:
                results.append(outcome)

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            list(pool.map(work, jobs))
        return results

    # -- one download -----------------------------------------------------

    def _download_one(self, job: dict) -> dict:
        key = job["media_key"]
        try:
            body, mime = self._fetch(job["url"])
        except Exception as exc:  # noqa: BLE001 — every failure is recorded
            failure = {
                "media_key": key, "status": "failed",
                "failure_reason": str(exc)[:200], "http_status": None,
                "local_path": None, "sha256": None, "byte_size": None,
                "mime_type": None,
            }
            self.store.record_media(
                key, job["platform"], job["document_id"], job["media_index"],
                job["url"], None, None, None, "", "failed",
                failure["failure_reason"], None)
            return failure

        sha = hashlib.sha256(body).hexdigest()
        # dedup: another thread may have finished the same object first
        known = self.store.media_known(key)
        if known and known.get("sha256") == sha and known.get("status") == "ok":
            return {"media_key": key, "status": "duplicate", "sha256": sha,
                    "local_path": known["local_path"]}

        ext = (mimetypes.guess_extension(mime) or "").replace("jpe", "jpg")
        fname = f"{key}{ext}"
        rel = f"media/{fname}"
        path = self.store.media_dir / fname
        path.write_bytes(body)

        self.store.record_media(
            key, job["platform"], job["document_id"], job["media_index"],
            job["url"], rel, sha, len(body), mime, "ok", None, 200)
        return {"media_key": key, "status": "ok", "sha256": sha,
                "byte_size": len(body), "mime_type": mime, "local_path": rel,
                "http_status": 200}

    def _fetch(self, url: str) -> tuple[bytes, str]:
        if self._fetcher is not None:
            return self._fetcher(url)
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=120) as resp:
            mime = resp.headers.get("Content-Type", "") or "application/octet-stream"
            return resp.read(), mime.split(";")[0].strip()