"""LaclauGPT-native Instagram parser.

This parser follows the original LaclauGPT-TikTok-Scraper style: identify the
visited view and captured request, collect native media objects, then normalise
one object at a time. It supports several current Instagram API/GraphQL shapes
without mirroring another collector's parser structure.

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

MODULE_NAME = "Instagram (posts & reels)"
DOMAIN = "instagram.com"

_HASHTAG_RE = re.compile(r"#([\wÀ-ÖØ-öø-ÿ]+)", re.UNICODE)
_RESERVED_PATHS = {
    "p", "reel", "reels", "explore", "stories", "direct", "accounts",
    "popular", "about", "legal", "developer", "web",
}


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except (TypeError, ValueError):
        return ""


def _page_context(url: str) -> tuple[str, str | None, str | None]:
    """Return (view, profile_handle, requested_shortcode)."""
    try:
        path = [part for part in urlparse(url).path.split("/") if part]
    except (TypeError, ValueError):
        return "unknown", None, None
    if not path:
        return "frontpage", None, None
    head = path[0].lower()
    if head == "explore":
        return "explore", None, None
    if head == "p" and len(path) > 1:
        return "single_post", None, path[1]
    if head in {"reel", "reels"} and len(path) > 1:
        return "single_reel", None, path[1]
    if head not in _RESERVED_PATHS:
        if len(path) > 1 and path[1].lower() == "reels":
            return "user_reels", head, None
        if len(path) > 1 and path[1].lower() == "tagged":
            return "user_tagged", head, None
        return "user_posts", head, None
    return head, None, None


def _caption_text(item: dict) -> str:
    caption = item.get("caption")
    if isinstance(caption, str):
        return caption
    if isinstance(caption, dict):
        return as_string(caption.get("text"))
    if isinstance(caption, list) and caption and isinstance(caption[0], dict):
        return as_string(caption[0].get("text"))
    try:
        return as_string(item["edge_media_to_caption"]["edges"][0]["node"]["text"])
    except (KeyError, IndexError, TypeError):
        return ""


def _looks_like_media(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    identity = first_value(item.get("pk"), item.get("id"), item.get("code"), item.get("shortcode"))
    if not identity:
        return False
    typename = as_string(item.get("__typename"))
    return bool(
        item.get("media_type")
        or item.get("code")
        or item.get("shortcode")
        or item.get("image_versions2")
        or item.get("video_versions")
        or item.get("display_url")
        or item.get("display_uri")
        or item.get("edge_media_to_caption")
        or "Polaris" in typename
    )


def _collect_media(root: Any) -> list[dict]:
    """Collect post/reel objects while treating carousel children as media assets."""
    found: list[dict] = []
    seen_objects: set[int] = set()

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return
        marker = id(node)
        if marker in seen_objects:
            return
        seen_objects.add(marker)

        if _looks_like_media(node):
            found.append(node)
            return

        for key, value in node.items():
            if key in {
                "user", "owner", "caption", "audio", "music_metadata", "image_versions2",
                "video_versions", "carousel_media", "edge_sidecar_to_children",
            }:
                continue
            if isinstance(value, (dict, list)):
                walk(value)

    walk(root)
    return found


def _parse_html(text: str) -> list[dict]:
    payloads: list[dict] = []
    for match in re.finditer(
        r"<script[^>]*type=[\"']application/json[\"'][^>]*>([\s\S]*?)</script>",
        text,
        re.IGNORECASE,
    ):
        try:
            value = json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            payloads.append(value)
    return [item for payload in payloads for item in _collect_media(payload)]


def _is_ad(item: dict) -> bool:
    link = item.get("link")
    return bool(
        item.get("product_type") == "ad"
        or item.get("ad_action") is not None
        or (isinstance(link, str) and link.startswith("https://www.facebook.com/ads/"))
    )


def _author_name(item: dict) -> str:
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
    return as_string(first_value(user.get("username"), owner.get("username"), item.get("owner_username")))


def _decorate(item: dict, view: str, embedded: bool) -> dict:
    copied = dict(item)
    copied["_laclaugpt_partial"] = not bool(
        _caption_text(item)
        and (
            item.get("video_versions")
            or item.get("image_versions2")
            or item.get("display_url")
            or item.get("display_uri")
        )
    )
    copied["_laclaugpt_instagram_view"] = view
    copied["_laclaugpt_embedded_json"] = embedded
    return copied


def _deduplicate(items: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for item in items:
        item_id = as_string(first_value(item.get("pk"), item.get("id"), item.get("code"), item.get("shortcode")))
        if not item_id:
            continue
        previous = by_id.get(item_id)
        if previous is None or (previous.get("_laclaugpt_partial") and not item.get("_laclaugpt_partial")):
            by_id[item_id] = item
    return list(by_id.values())


def capture(response: Any, source_platform_url: str, source_url: str) -> list[dict]:
    """Extract native Instagram post/reel objects from one captured response."""
    if _host(source_platform_url) != DOMAIN:
        return []

    view, visited_handle, requested_shortcode = _page_context(source_platform_url)
    request_url = source_url or ""
    if re.search(r"logging_client_events|lightspeed_web_request_for_igd|injected_story_units", request_url):
        return []

    embedded = False
    if isinstance(response, dict):
        items = _collect_media(response)
    elif isinstance(response, str):
        body = response.strip()
        if not body:
            return []
        if body.startswith("for (;;);"):
            body = body[len("for (;;);"):]
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            embedded = True
            items = _parse_html(body)
        else:
            items = _collect_media(payload)
    else:
        return []

    collected: list[dict] = []
    for item in items:
        if _is_ad(item):
            continue
        shortcode = as_string(first_value(item.get("code"), item.get("shortcode")))
        if requested_shortcode and shortcode != requested_shortcode:
            continue
        author = _author_name(item).lower()
        if visited_handle and author and author != visited_handle.lower():
            continue
        collected.append(_decorate(item, view, embedded))
    return _deduplicate(collected)


def overwrite_partial(incoming: dict, existing: dict | None) -> bool:
    """Allow a full payload to replace an earlier partial payload, never reverse."""
    if not existing:
        return False
    return bool(existing.get("_laclaugpt_partial")) and not bool(
        incoming.get("_laclaugpt_partial")
    )


def _media_type(item: dict) -> str:
    typename = as_string(item.get("__typename"))
    if item.get("media_type") == 8 or item.get("carousel_media") or item.get("edge_sidecar_to_children"):
        return "carousel"
    if item.get("media_type") == 2 or item.get("is_video") or "VideoMedia" in typename:
        return "video"
    return "photo"


def _image_urls(item: dict) -> list[str]:
    urls: list[str] = []
    for key in ("display_url", "display_uri", "display_src"):
        if item.get(key):
            urls.append(as_string(item[key]))
    image_versions = item.get("image_versions2")
    if isinstance(image_versions, dict):
        for candidate in image_versions.get("candidates") or []:
            if isinstance(candidate, dict) and candidate.get("url"):
                urls.append(as_string(candidate["url"]))

    children = item.get("carousel_media") or []
    if isinstance(children, list):
        for child in children:
            if isinstance(child, dict):
                urls.extend(_image_urls(child))
    return unique(urls)


def _video_urls(item: dict) -> list[str]:
    urls: list[str] = []
    if item.get("video_url"):
        urls.append(as_string(item["video_url"]))
    for version in item.get("video_versions") or []:
        if isinstance(version, dict) and version.get("url"):
            urls.append(as_string(version["url"]))
    children = item.get("carousel_media") or []
    if isinstance(children, list):
        for child in children:
            if isinstance(child, dict):
                urls.extend(_video_urls(child))
    return unique(urls)


def _timestamp(item: dict) -> tuple[str, int]:
    value = first_value(item.get("taken_at"), item.get("taken_at_timestamp"), item.get("created_time"))
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


def _location(item: dict) -> tuple[str, str, str, str]:
    loc = item.get("location") if isinstance(item.get("location"), dict) else {}
    name = as_string(loc.get("name"))
    city = as_string(first_value(loc.get("city"), loc.get("city_name")))
    location_id = as_string(first_value(loc.get("pk"), loc.get("id")))
    lat = first_value(loc.get("lat"), loc.get("latitude"))
    lng = first_value(loc.get("lng"), loc.get("longitude"))
    latlong = f"{lat},{lng}" if lat is not None and lng is not None else ""
    return name, latlong, city, location_id


def map_item(item: dict, metadata: dict | None = None) -> dict:
    """Map one native Instagram object to the stable collector record shape."""
    metadata = metadata or {}
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
    author = {**owner, **{key: value for key, value in user.items() if value is not None}}

    shortcode = as_string(first_value(item.get("code"), item.get("shortcode")))
    native_id = as_string(first_value(item.get("pk"), item.get("id"), shortcode))
    record_id = shortcode or native_id
    media_type = _media_type(item)
    caption = _caption_text(item)
    timestamp, unix_ts = _timestamp(item)
    image_urls = _image_urls(item)
    video_urls = _video_urls(item)
    location_name, location_latlong, location_city, location_id = _location(item)

    if shortcode:
        route = "reel" if media_type == "video" else "p"
        permalink = f"https://www.instagram.com/{route}/{shortcode}"
    else:
        permalink = as_string(first_value(item.get("permalink"), item.get("link")))

    hashtags = unique(match.group(1) for match in _HASHTAG_RE.finditer(caption))
    likes = first_value(
        item.get("like_count"),
        (item.get("edge_media_preview_like") or {}).get("count"),
        (item.get("edge_liked_by") or {}).get("count"),
    )
    comments = first_value(
        item.get("comment_count"),
        (item.get("edge_media_to_comment") or {}).get("count"),
        (item.get("edge_media_to_parent_comment") or {}).get("count"),
    )
    plays = first_value(item.get("play_count"), item.get("view_count"), item.get("video_view_count"))

    return {
        "collected_from_url": metadata.get("source_platform_url", ""),
        "id": record_id,
        "native_id": native_id,
        "thread_id": record_id,
        "parent_id": "",
        "author": as_string(first_value(author.get("username"), item.get("owner_username"))),
        "author_full": as_string(first_value(author.get("full_name"), author.get("name"))),
        "author_id": as_string(first_value(author.get("pk"), author.get("id"))),
        "author_avatar": as_string(
            first_value(author.get("profile_pic_url"), author.get("profile_pic_url_hd"))
        ),
        "verified": author.get("is_verified", ""),
        "body": caption,
        "timestamp": timestamp,
        "unix_timestamp": unix_ts,
        "url": permalink,
        "media_type": media_type,
        "media_urls": ",".join(video_urls),
        "image_urls": ",".join(image_urls),
        "hashtags": ",".join(hashtags),
        "num_likes": likes if likes is not None else -1,
        "num_comments": comments if comments is not None else -1,
        "like_count": likes if likes is not None else -1,
        "comment_count": comments if comments is not None else -1,
        "play_count": plays if plays is not None else -1,
        "location_name": location_name,
        "location_latlong": location_latlong,
        "location_city": location_city,
        "location_id": location_id,
        "product_type": as_string(item.get("product_type")),
        "partial": bool(item.get("_laclaugpt_partial")),
        "instagram_view": as_string(item.get("_laclaugpt_instagram_view")),
    }
