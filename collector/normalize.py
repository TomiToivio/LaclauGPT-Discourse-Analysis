"""Normalisation: raw platform items → stable LaclauGPT records.

The collector produces two linked representations per post:

- the RAW payload (exact captured platform object, kept in raw/ as NDJSON)
- the NORMALISED record (this module), designed to feed LaclauGPT analysis
  and the existing adapters/interchange conventions.

Every normalised record carries `provenance` answering: when captured,
by which collector/module version, from which visited URL, which network
response, which raw platform ID, which transformations, media status,
and which collector code version.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

MODULE_VERSIONS = {
    "tiktok": "zeeschuimer-tiktok-2026-09",
    "instagram": "zeeschuimer-instagram-2026-09",
    "x": "zeeschuimer-twitter-2026-09",
}

# canonical LaclauGPT document fields the analysis pipeline consumes
CANONICAL_FIELDS = (
    "document_id", "platform", "author", "timestamp", "source_url",
    "text", "language", "parent_document_id", "media_refs",
    "collection_provenance",
)


def normalise(platform: str, mapped: dict, raw: dict | None,
              metadata: dict | None = None) -> dict:
    """Build one normalised record from a module map_item() result.

    `mapped` is the module's map_item() output; `raw` the native platform
    object it was parsed from (kept linked, never discarded).
    """
    metadata = metadata or {}
    document_id = str(mapped.get("id") or "")
    if not document_id:
        raise ValueError("normalise: mapped record without id")

    # deterministic source_url: module-provided permalink when available
    source_url = (mapped.get("link") or mapped.get("tiktok_url")
                  or mapped.get("url") or mapped.get("collected_from_url") or "")

    parent = None
    if platform == "x":
        # conversation/thread relationship (reply/quote handled in fields)
        thread = mapped.get("thread_id") or ""
        if mapped.get("is_reply") == "yes" and thread != document_id:
            parent = str(thread)
    elif platform == "instagram":
        parent = mapped.get("parent_id") or None

    lang = (mapped.get("language_guess") or "") if platform == "x" else ""

    return {
        "document_id": document_id,
        "platform": platform,
        "author": mapped.get("author") or "",
        "author_fullname": (mapped.get("author_full")
                            or mapped.get("author_fullname") or ""),
        "timestamp": mapped.get("timestamp") or "",
        "unix_timestamp": mapped.get("unix_timestamp") or 0,
        "source_url": source_url,
        "text": mapped.get("body") or "",
        "language": lang,
        "parent_document_id": parent,
        "hashtags": (mapped.get("hashtags") or "").split(",")
        if mapped.get("hashtags") else [],
        "mentions": (mapped.get("mentions") or "").split(",")
        if mapped.get("mentions") else [],
        "engagement": {
            k: mapped[k] for k in (
                "likes", "comments", "shares", "plays",
                "like_count", "comment_count", "retweet_count",
                "quote_count", "reply_count", "impression_count",
                "play_count", "num_likes", "num_comments",
                "author_followers")
            if mapped.get(k) not in (None, "", -1)
        },
        "media_references": _media_refs(platform, mapped),
        "raw_ref": "",  # filled by the store layer (raw NDJSON pointer)
        "collection_provenance": {
            "captured_at": metadata.get("captured_at", ""),
            "collector_version": metadata.get("collector_version", ""),
            "module": MODULE_VERSIONS.get(platform, platform),
            "module_version": MODULE_VERSIONS.get(platform, ""),
            "git_commit": metadata.get("git_commit", ""),
            "visited_url": metadata.get("source_platform_url", ""),
            "api_url": metadata.get("source_url", ""),
            "capture_id": metadata.get("capture_id", ""),
            "run_id": metadata.get("run_id", ""),
            "account": metadata.get("account", ""),
            "transformations": ["zeeschuimer-capture", "map_item-normalise"],
            "media_downloaded": None,  # set by the media layer
        },
    }


def _media_refs(platform: str, mapped: dict) -> list[dict]:
    """Uniform media references for the media downloader queue."""
    refs: list[dict] = []

    def add(kind: str, url: str, index: int) -> None:
        if url and isinstance(url, str) and url.startswith("http"):
            add_refs.append({"kind": kind, "url": url, "media_index": index})

    add_refs: list[dict] = []
    if platform == "tiktok":
        if mapped.get("video_url"):
            add("video", mapped["video_url"], 0)
        if mapped.get("thumbnail_url"):
            add("thumbnail", mapped["thumbnail_url"], 1)
    elif platform == "instagram":
        urls = mapped.get("media_urls") or ""
        display = mapped.get("image_urls") or ""
        for i, url in enumerate(u for u in urls.split(",") if u):
            add("video" if mapped.get("media_type") == "video" else "image", url, i)
        for i, url in enumerate(u for u in display.split(",") if u):
            add("image", url, 100 + i)
    elif platform == "x":
        for i, url in enumerate(u for u in (mapped.get("videos") or "").split(",") if u):
            add("video", url, i)
        for i, url in enumerate(u for u in (mapped.get("images") or "").split(",") if u):
            add("image", url, 10 + i)
        # quoted/reposted media when clearly attributable
        if mapped.get("quote_videos"):
            for i, url in enumerate(u for u in mapped["quote_videos"].split(",") if u):
                add("quote_video", url, 20 + i)
        if mapped.get("quote_images"):
            for i, url in enumerate(u for u in mapped["quote_images"].split(",") if u):
                add("quote_image", url, 30 + i)
    refs = add_refs
    return refs


def dedup_key(record: dict) -> tuple:
    """Identity of a post across runs: (platform, document_id)."""
    return (record["platform"], record["document_id"])