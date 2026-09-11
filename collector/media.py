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

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) LaclauGPT-Collector/0.1 "
    "(research; project github.com/TomiToivio/LaclauGPT-Discourse-Analysis)"
)
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
    def __init__(self, store: Store, backend: MediaBackend,
                 workers: int = DEFAULT_WORKERS,
                 opener: Callable = urlopen) -> None:
        self.store = store
        self.backend = backend
        self.workers = workers
        self.opener = opener
        self._lock = threading.Lock()

    @staticmethod
    def _guess_extension(url: str, mime_type: str) -> str:
        extension = mimetypes.guess_extension(mime_type.split(";", 1)[0].strip())
        if extension:
            return extension
        suffix = Path(url.split("?", 1)[0]).suffix
        return suffix if suffix and len(suffix) <= 8 else ".bin"

    @staticmethod
    def _key(data: bytes, extension: str) -> tuple[str, str]:
        sha = hashlib.sha256(data).hexdigest()
        return sha, f"sha256/{sha[:2]}/{sha}{extension}"

    def _download(self, item: dict) -> dict:
        url = item["url"]
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with self.opener(request, timeout=45) as response:
                data = response.read()
                mime_type = response.headers.get_content_type()
        except HTTPError as exc:
            self.store.mark_media_failed(item["id"], str(exc))
            return {"url": url, "status": "failed", "error": str(exc)}
        except Exception as exc:  # network failures are recorded, not fatal to capture
            self.store.mark_media_failed(item["id"], str(exc))
            return {"url": url, "status": "failed", "error": str(exc)}

        extension = self._guess_extension(url, mime_type)
        sha, key = self._key(data, extension)
        with self._lock:
            if not self.backend.exists(key):
                stored = self.backend.save(key, data, mime_type)
            else:
                if isinstance(self.backend, FilesystemBackend):
                    path = self.backend.root / key
                    try:
                        stored = path.relative_to(self.backend.reference_root).as_posix()
                    except ValueError:
                        stored = str(path)
                else:
                    stored = key
            self.store.mark_media_done(
                item["id"],
                checksum=f"sha256:{sha}",
                storage_path=stored,
                mime_type=mime_type,
                size_bytes=len(data),
            )
        return {"url": url, "status": "done", "storage_path": stored,
                "checksum": f"sha256:{sha}"}

    def run_pending(self, limit: int = 100) -> list[dict]:
        pending = self.store.pending_media(limit=limit)
        if not pending:
            return []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return list(pool.map(self._download, pending))


def queue_from_records(store: Store, records: Iterable[dict]) -> int:
    """Queue all media URLs from normalized records. Returns queued count."""
    queued = 0
    for record in records:
        capture_id = record.get("capture_id")
        for url in record.get("media_urls", []) or []:
            if url:
                store.queue_media(capture_id, url)
                queued += 1
    return queued
