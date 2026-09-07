"""Media downloader — queued, non-blocking, checksummed (issue #20).

Media downloading is ASYNCHRONOUS relative to browser capture: capture never
waits for large files. Each MediaRef carries status/failure so metadata stays
usable even when a signed CDN URL has expired (TikTok/Instagram common case).

Storage behind an interface: FileSystemMediaStore today, Allas/S3 later.
Downloaded research media are NEVER committed to Git (issue rule).
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .records import MediaRef, media_filename, sha256_file

UA = {"User-Agent": "Mozilla/5.0 (LaclauGPT collector; research)"}


class MediaStore:
    """Storage interface — swap for object storage (Allas/S3) later."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def path_for(self, platform: str, post_id: str, media_index: int,
                 ext: str) -> Path:
        d = self.root / platform
        d.mkdir(parents=True, exist_ok=True)
        return d / media_filename(platform, post_id, media_index, ext)

    def exists_verified(self, path: Path, sha: str | None) -> bool:
        if not path.exists():
            return False
        return sha is None or sha256_file(path) == sha


class MediaQueue:
    """Serial queue worker; capture loop just enqueues and moves on."""

    def __init__(self, store: MediaStore, manifest_dir: Path | None = None):
        self.store = store
        self.manifest_dir = Path(manifest_dir) if manifest_dir else None

    def download(self, ref: MediaRef) -> MediaRef:
        """Download one MediaRef; dedupe by checksum; never raise."""
        if ref.status == "downloaded":
            return ref
        ext = self._ext_for(ref.original_url, ref.media_type)
        dest = self.store.path_for(ref.platform, ref.post_id,
                                   ref.media_index, ext)
        # dedupe: retry must not create a second copy
        if dest.exists():
            ref.local_path = str(dest)
            ref.sha256 = sha256_file(dest)
            ref.byte_size = dest.stat().st_size
            ref.status = "downloaded"
            ref.downloaded_at = datetime.now(timezone.utc).isoformat()
            return ref
        try:
            req = urllib.request.Request(ref.original_url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                ref.http_status = resp.status
                ref.mime_type = resp.headers.get("Content-Type")
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(data)
            tmp.rename(dest)
            ref.local_path = str(dest)
            ref.byte_size = len(data)
            ref.sha256 = sha256_file(dest)
            ref.status = "downloaded"
            ref.downloaded_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:            # noqa: BLE001 — failures recorded, never fatal
            ref.status = "failed"
            ref.failure_reason = str(exc)[:200]
        return ref

    @staticmethod
    def _ext_for(url: str, media_type: str) -> str:
        tail = url.split("?")[0].rsplit(".", 1)
        if len(tail) == 2 and tail[1].lower() in {"jpg", "jpeg", "png", "webp",
                                                  "mp4", "webm", "gif"}:
            return "." + tail[1].lower()
        return {"video": ".mp4", "image": ".jpg", "thumbnail": ".jpg"}.get(
            media_type, ".bin")


def process_queue(refs: list[MediaRef], store: MediaStore,
                  manifest_dir: Path | None = None) -> list[MediaRef]:
    """Drain the queue (serial today; threads later if needed)."""
    q = MediaQueue(store)
    done = []
    for ref in refs:
        done.append(q.download(ref))
    if manifest_dir:
        manifest = {
            "at": datetime.now(timezone.utc).isoformat(),
            "downloads": [
                {"platform": r.platform, "post_id": r.post_id,
                 "status": r.status, "sha256": r.sha256,
                 "local_path": r.local_path, "failure": r.failure_reason}
                for r in done],
        }
        manifest_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_dir / f"media_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.json",
                  "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1)
    return done