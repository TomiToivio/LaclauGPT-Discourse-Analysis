"""LaclauGPT Social Media Collector — normalised record schema (issue #20).

Every collected post becomes ONE NormalisedRecord; raw platform payloads are
kept separately under raw/ (reproducibility), media under media/ (checksums
+ stable names), manifests under manifests/ (runs, errors, provenance).

Interoperability rule: fields map 1:1 into the LaclauGPT interchange
(document_id, platform, author, timestamp, source_url, text, parent,
media refs, collection provenance). No discourse analysis happens here —
the collector produces source material only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COLLECTOR_VERSION = "laclaugpt-collector-0.1.0"


def media_filename(platform: str, post_id: str, media_index: int,
                   ext: str = "") -> str:
    """Deterministic collision-resistant name (issue: never use captions)."""
    base = f"{platform}_{post_id}_{media_index:03d}"
    return f"{base}{ext}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class MediaRef:
    platform: str
    post_id: str
    media_index: int
    original_url: str
    media_type: str              # image | video | thumbnail
    local_path: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
    sha256: str | None = None
    status: str = "pending"      # pending | downloaded | failed
    failure_reason: str | None = None
    http_status: int | None = None
    downloaded_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NormalizedPost:
    platform: str               # tiktok | instagram | x
    post_id: str                # EXACT string (X ids exceed int64-safe range)
    author: str
    author_display: str | None
    timestamp: str              # ISO 8601, original tz preserved in raw
    url: str
    text: str
    parent_post_id: str | None = None      # reply/quote/repost relation
    relation: str | None = None            # reply | quote | repost | None
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    engagement: dict = field(default_factory=dict)
    language: str | None = None
    media: list[MediaRef] = field(default_factory=list)
    # provenance (issue #20 §Provenance — all questions answerable)
    captured_at: str = ""
    captured_from_url: str = ""
    captured_from_response: str = ""       # endpoint/embedded marker
    collector_version: str = COLLECTOR_VERSION
    collector_commit: str | None = None
    transformations: list[str] = field(default_factory=list)
    raw_ref: str | None = None             # pointer into raw/ NDJSON
    study: str | None = None
    candidate_id: str | None = None

    def to_interchange(self) -> dict:
        """Map to LaclauGPT interchange document (analysis-ready)."""
        doc = {
            "document_id": f"{self.platform}::{self.post_id}",
            "platform": self.platform,
            "author": self.author,
            "author_display": self.author_display,
            "timestamp": self.timestamp,
            "source_url": self.url,
            "text": self.text,
            "hashtags": self.hashtags,
            "mentions": self.mentions,
            "urls": self.urls,
            "engagement": self.engagement,
            "language": self.language,
            "media": [m.to_dict() for m in self.media],
            "collection_provenance": {
                "captured_at": self.captured_at,
                "captured_from_url": self.captured_from_url,
                "captured_from_response": self.captured_from_response,
                "collector_version": self.collector_version,
                "collector_commit": self.collector_commit,
                "transformations": self.transformations,
                "raw_ref": self.raw_ref,
                "study": self.study,
                "candidate_id": self.candidate_id,
            },
        }
        if self.parent_post_id:
            doc["parent_document_id"] = f"{self.platform}::{self.parent_post_id}"
            doc["relation"] = self.relation
        return doc


def jsonl_append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_seen_ids(path: Path) -> set[str]:
    """Dedup state: post_id set persisted per platform (resume after crash)."""
    if not path.exists():
        return set()
    seen = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                seen.add(json.loads(line).get("post_id"))
            except (json.JSONDecodeError, AttributeError):
                continue
    return seen


def within_window(ts: str | None, start: str, end: str) -> bool:
    """Issue #20: respect configured start/end (inclusive), ISO dates."""
    if not ts:
        return True     # unknown timestamps kept, flagged by parser
    day = ts[:10]
    return start <= day <= end