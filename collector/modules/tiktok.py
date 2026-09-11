"""LaclauGPT-native TikTok parser.

The design follows the original 2024 LaclauGPT-TikTok-Scraper:
route captured TikTok responses by endpoint, parse native post objects in small
helpers, and map them into a stable LaclauGPT record.

Zeeschuimer is an architectural inspiration for browser/API-response capture,
but this module is an independent LaclauGPT implementation and is not a port of
Zeeschuimer source code.

Author: Tomi Toivio / LaclauGPT
License: CC0 1.0 Universal
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .common import as_string, first_value, unique

MODULE_NAME = "TikTok (posts)"
DOMAIN = "tiktok.com"

_SIGI_SCRIPT = re.compile(
    r"<script[^>]+id=[\"']SIGI_STATE[\"'][^>]*>([\s\S]*?)</script>",
    re.IGNORECASE,
)
_UNIVERSAL_SCRIPT = re.compile(
    r"<script[^>]+id=[\"']__UNIVERSAL_DATA_FOR_REHYDRATION__[\"'][^>]*>"
    r"([\s\S]*?)</script>",
    re.IGNORECASE,
)


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except (TypeError, ValueError):
        return ""


def _is_post(item: Any) -> bool:
    return isinstance(item, dict) and bool(item.get("id") or item.get("aweme_id")) and not item.get(
        "liveRoomInfo"
    )


def _item_list(data: dict) -> list[dict]:
    rows = data.get("itemList")
    if not isinstance(rows, list):
        rows = data.get("item_list")
    if not isinstance(rows, list):
        return []
    return [item for item in rows if _is_post(item)]


def _search_items(data: dict) -> list[dict]:
    rows: Any = data.get("data") or []
    if isinstance(rows, dict):
        rows = list(rows.values())
    if not isinstance(rows, list):
        return []

    posts: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = row.get("item") or row.get("itemStruct")
        if _is_post(item):
            posts.append(item)
    return posts


def _playlist_items(data: dict) -> list[dict]:
    rows = data.get("itemList") or data.get("item_list") or []
    if not isinstance(rows, list):
        return []
    posts: list[dict] = []
    for row in rows:
        item = row.get("item") if isinstance(row, dict) else None
        candidate = item or row
        if _is_post(candidate):
            posts.append(candidate)
    return posts


def _item_module(data: dict) -> list[dict]:
    module = data.get("ItemModule")
    if not isinstance(module, dict):
        return []
    return [item for item in module.values() if _is_post(item)]


def _universal_data(data: dict) -> list[dict]:
    scope = data.get("__DEFAULT_SCOPE__") or data.get("__DEFAULT_SCOPE")
    if not isinstance(scope, dict):
        return []

    posts: list[dict] = []
    updated = scope.get("webapp.updated-items")
    if isinstance(updated, list):
        for row in updated:
            item = row.get("itemStruct") if isinstance(row, dict) else None
            candidate = item or row
            if _is_post(candidate):
                posts.append(candidate)

    detail = (
        (scope.get("webapp.video-detail") or {})
        .get("itemInfo", {})
        .get("itemStruct")
    )
    if _is_post(detail):
        posts.append(detail)
    return posts


def _parse_html(html: str) -> list[dict]:
    posts: list[dict] = []
    for pattern, parser in ((_SIGI_SCRIPT, _item_module), (_UNIVERSAL_SCRIPT, _universal_data)):
        match = pattern.search(html)
        if not match:
            continue
        try:
            payload = json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            continue
        posts.extend(parser(payload))
    return posts


def _deduplicate(posts: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for post in posts:
        post_id = as_string(post.get("id") or post.get("aweme_id"))
        if not post_id or post_id in seen:
            continue
        seen.add(post_id)
        out.append(post)
    return out


def capture(response: Any, source_platform_url: str, source_url: str) -> list[dict]:
    """Extract native TikTok post objects from one captured response."""
    if _host(source_platform_url) != DOMAIN:
        return []
    if "api/preload/" in (source_url or ""):
        return []

    if isinstance(response, dict):
        data = response
    elif isinstance(response, str):
        text = response.strip()
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return _deduplicate(_parse_html(text))
    else:
        return []

    request_url = source_url or ""
    if "search/" in request_url:
        posts = _search_items(data)
    elif "user/playlist" in request_url:
        posts = _playlist_items(data)
    elif "item_list" in request_url:
        posts = _item_list(data)
    elif data.get("ItemModule"):
        posts = _item_module(data)
    elif data.get("__DEFAULT_SCOPE__") or data.get("__DEFAULT_SCOPE"):
        posts = _universal_data(data)
    elif isinstance(data.get("itemList"), list) or isinstance(data.get("item_list"), list):
        posts = _item_list(data)
    elif isinstance(data.get("data"), (list, dict)):
        posts = _search_items(data)
    else:
        posts = []
    return _deduplicate(posts)


def _iso_timestamp(value: Any) -> tuple[str, int]:
    try:
        unix_ts = int(str(value))
    except (TypeError, ValueError):
        return "", 0
    if unix_ts <= 0:
        return "", unix_ts
    try:
        return datetime.fromtimestamp(unix_ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), unix_ts
    except (OverflowError, OSError, ValueError):
        return "", 0


def _thumbnail(video: dict) -> str:
    candidates: list[str] = []
    share = video.get("shareCover")
    if isinstance(share, list):
        candidates.extend(str(url) for url in share if url)
    elif isinstance(share, str) and share:
        candidates.append(share)
    candidates.extend(
        str(url)
        for url in (video.get("cover"), video.get("dynamicCover"), video.get("originCover"))
        if url
    )
    if not candidates:
        return ""

    now = int(datetime.now(timezone.utc).timestamp())
    for url in reversed(candidates):
        try:
            query = urlparse(url).query
            expires = int(query.split("x-expires=", 1)[1].split("&", 1)[0])
        except (IndexError, TypeError, ValueError):
            return url
        if expires >= now:
            return url
    return ""


def map_item(post: dict, metadata: dict | None = None) -> dict:
    """Map one native TikTok object to the stable collector record shape."""
    metadata = metadata or {}
    author = post.get("author") if isinstance(post.get("author"), dict) else {}
    author_stats = post.get("authorStats") if isinstance(post.get("authorStats"), dict) else {}
    stats = post.get("stats") if isinstance(post.get("stats"), dict) else {}
    video = post.get("video") if isinstance(post.get("video"), dict) else {}
    music = post.get("music") if isinstance(post.get("music"), dict) else {}

    post_id = as_string(first_value(post.get("id"), post.get("aweme_id")))
    username = as_string(
        first_value(author.get("uniqueId"), author.get("unique_id"), post.get("author"))
    )
    timestamp, unix_ts = _iso_timestamp(first_value(post.get("createTime"), post.get("create_time")))

    hashtags = unique(
        as_string(first_value(row.get("hashtagName"), row.get("hashtag_name")))
        for row in (post.get("textExtra") or post.get("text_extra") or [])
        if isinstance(row, dict)
    )
    challenges = unique(
        as_string(row.get("title"))
        for row in (post.get("challenges") or [])
        if isinstance(row, dict)
    )
    effects = unique(
        as_string(row.get("name"))
        for row in (post.get("effectStickers") or [])
        if isinstance(row, dict)
    )
    warnings = unique(
        as_string(row.get("text"))
        for row in (post.get("warnInfo") or [])
        if isinstance(row, dict)
    )

    labels = post.get("diversificationLabels")
    if not isinstance(labels, list):
        labels = []

    canonical = (
        f"https://www.tiktok.com/@{username}/video/{post_id}"
        if username
        else f"https://www.tiktok.com/video/{post_id}"
    )
    duet_id = as_string((post.get("duetInfo") or {}).get("duetFromId"))

    return {
        "collected_from_url": metadata.get("source_platform_url", ""),
        "id": post_id,
        "thread_id": post_id,
        "author": username,
        "author_full": as_string(first_value(author.get("nickname"), post.get("nickname"))),
        "author_followers": first_value(
            author_stats.get("followerCount"), author_stats.get("follower_count"), ""
        ),
        "author_likes": first_value(
            author_stats.get("heartCount"), author_stats.get("heart"), author_stats.get("diggCount"), ""
        ),
        "author_videos": first_value(author_stats.get("videoCount"), author_stats.get("video_count"), ""),
        "author_avatar": as_string(
            first_value(author.get("avatarThumb"), author.get("avatarLarger"), author.get("avatarMedium"))
        ),
        "body": as_string(first_value(post.get("desc"), post.get("description"), "")),
        "stickers": "\n".join(
            " ".join(as_string(text) for text in row.get("stickerText", []) if text)
            for row in (post.get("stickersOnItem") or [])
            if isinstance(row, dict)
        ),
        "timestamp": timestamp,
        "unix_timestamp": unix_ts,
        "is_duet": "yes" if duet_id and duet_id != "0" else "no",
        "is_ad": "yes" if post.get("isAd") else "no",
        "is_paid_partnership": "yes" if post.get("adAuthorization") else "no",
        "is_sensitive": "yes" if post.get("maskType") == 3 else "no",
        "is_photosensitive": "yes" if post.get("maskType") == 4 else "no",
        "music_name": as_string(music.get("title")),
        "music_id": as_string(music.get("id")),
        "music_url": as_string(first_value(music.get("playUrl"), music.get("play_url"))),
        "music_thumbnail": as_string(
            first_value(music.get("coverLarge"), music.get("coverMedium"), music.get("coverThumb"))
        ),
        "music_author": as_string(first_value(music.get("authorName"), music.get("author"))),
        "video_url": as_string(
            first_value(video.get("downloadAddr"), video.get("download_addr"), video.get("playAddr"))
        ),
        "tiktok_url": as_string(first_value(post.get("shareUrl"), post.get("share_url"), canonical)),
        "thumbnail_url": _thumbnail(video),
        "likes": first_value(stats.get("diggCount"), stats.get("digg_count")),
        "comments": first_value(stats.get("commentCount"), stats.get("comment_count")),
        "shares": first_value(stats.get("shareCount"), stats.get("share_count")),
        "plays": first_value(stats.get("playCount"), stats.get("play_count")),
        "hashtags": ",".join(hashtags),
        "challenges": ",".join(challenges),
        "diversification_labels": ",".join(as_string(label) for label in labels if label),
        "location_created": as_string(first_value(post.get("locationCreated"), post.get("location_created"))),
        "effects": ",".join(effects),
        "warning": ",".join(warnings),
    }
