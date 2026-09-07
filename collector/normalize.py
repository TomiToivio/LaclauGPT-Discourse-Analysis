"""Normalisation: raw platform items -> stable LaclauGPT records.

The collector produces two linked representations per post:

- RAW payload: exact captured platform object, append-only under raw/
- NORMALISED record: stable fields for LaclauGPT analysis and interchange

Every record retains provenance linking it back to the visited page, network
response, raw object, collector build and platform parser module.
"""
from __future__ import annotations

from typing import Any

MODULE_VERSIONS = {
    # These names describe the Python parser implementation lineage. They do
    # not describe the browser capture mechanism, which is LaclauGPT-native.
    "tiktok": "zeeschuimer-tiktok-2026-09",
    "instagram": "zeeschuimer-instagram-2026-09",
    "x": "zeeschuimer-twitter-2026-09",
}

CANONICAL_FIELDS = (
    "document_id", "platform", "author", "timestamp", "source_url",
    "text", "language", "parent_document_id", "media_references",
    "collection_provenance",
)


def normalise(platform: str, mapped: dict, raw: dict | None,
              metadata: dict | None = None) -> dict:
    """Build one normalised record from a platform module map_item result."""
    metadata = metadata or {}
    document_id = str(mapped.get("id") or "")
    if not document_id:
        raise ValueError("normalise: mapped record without id")

    source_url = (mapped.get("link") or mapped.get("tiktok_url")
                  or mapped.get("url") or mapped.get("collected_from_url") or "")

    parent = None
    if platform == "x":
        thread = mapped.get("thread_id") or ""
        if mapped.get("is_reply") == "yes" and thread != document_id:
            parent = str(thread)
    elif platform == "instagram":
        parent = mapped.get("parent_id") or None

    language = (mapped.get("language_guess") or "") if platform == "x" else ""

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
        "language": language,
        "parent_document_id": parent,
        "hashtags": (mapped.get("hashtags") or "").split(",")
        if mapped.get("hashtags") else [],
        "mentions": (mapped.get("mentions") or "").split(",")
        if mapped.get("mentions") else [],
        "engagement": {
            key: mapped[key] for key in (
                "likes", "comments", "shares", "plays",
                "like_count", "comment_count", "retweet_count",
                "quote_count", "reply_count", "impression_count",
                "play_count", "num_likes", "num_comments",
                "author_followers")
            if mapped.get(key) not in (None, "", -1)
        },
        "media_references": _media_refs(platform, mapped),
        "raw_ref": "",
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
            "transformations": ["laclaugpt-network-capture", "map_item-normalise"],
            "media_downloaded": None,
        },
    }


def _media_refs(platform: str, mapped: dict) -> list[dict]:
    """Uniform media references for the media downloader queue."""
    refs: list[dict] = []

    def add(kind: str, url: str, index: int) -> None:
        if url and isinstance(url, str) and url.startswith("http"):
            refs.append({"kind": kind, "url": url, "media_index": index})

    if platform == "tiktok":
        if mapped.get("video_url"):
            add("video", mapped["video_url"], 0)
        if mapped.get("thumbnail_url"):
            add("thumbnail", mapped["thumbnail_url"], 1)
    elif platform == "instagram":
        urls = mapped.get("media_urls") or ""
        display = mapped.get("image_urls") or ""
        for index, url in enumerate(value for value in urls.split(",") if value):
            add("video" if mapped.get("media_type") == "video" else "image", url, index)
        for index, url in enumerate(value for value in display.split(",") if value):
            add("image", url, 100 + index)
    elif platform == "x":
        for index, url in enumerate(
                value for value in (mapped.get("videos") or "").split(",") if value):
            add("video", url, index)
        for index, url in enumerate(
                value for value in (mapped.get("images") or "").split(",") if value):
            add("image", url, 10 + index)
        for index, url in enumerate(
                value for value in (mapped.get("quote_videos") or "").split(",") if value):
            add("quote_video", url, 20 + index)
        for index, url in enumerate(
                value for value in (mapped.get("quote_images") or "").split(",") if value):
            add("quote_image", url, 30 + index)
    return refs


def dedup_key(record: dict) -> tuple:
    """Identity of a post across runs: (platform, document_id)."""
    return (record["platform"], record["document_id"])
