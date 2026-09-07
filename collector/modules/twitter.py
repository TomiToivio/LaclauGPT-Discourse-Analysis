"""X/Twitter parsing module.

Adapted from Zeeschuimer's modules/twitter.js
(https://github.com/digitalmethodsinitiative/zeeschuimer),
Copyright (c) Stijn Peeters, Mozilla Public License 2.0.

Modifications for LaclauGPT (2026):
- translated capture() (endpoint allowlist by GraphQL operation name,
  TimelineAddEntries/TimelinePinEntry traversal, TimelineTimelineModule
  replies, adaptive fallback) and both map_item parsers (modern/legacy)
  from JavaScript to Python;
- post IDs stay EXACT STRINGS (they exceed JS Number.MAX_SAFE_INTEGER);
- map_item() emits plain dicts.

This file is MPL-2.0 like the upstream it adapts; see modules/README.md.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .common import py_get, strip_tags

MODULE_NAME = "X/Twitter"
DOMAIN = "x.com"
MODULE_ID = "twitter.com"

# API endpoints that carry posts. Matched as substrings of the request
# URL; GraphQL operation names are stable across query-ID changes.
POST_BEARING_ENDPOINTS = (
    "adaptive.json", "HomeTimeline", "HomeLatestTimeline",
    "ListLatestTweetsTimeline", "SearchTimeline", "TweetDetail",
    "UserTweets", "UserOriginalsTimeline", "UserRepliesTimeline",
    "UserRepostsTimeline", "UserPhotoTimeline", "UserVideoTimeline",
    "ExplorePage", "Likes",
)


def capture(response: Any, source_platform_url: str, source_url: str) -> list[dict]:
    """Extract X/Twitter tweet objects from one captured response."""
    try:
        domain = urlparse(source_platform_url).netloc.lower().replace("www.", "")
    except ValueError:
        return []
    if domain != "x.com" or not any(
            ep in (source_url or "") for ep in POST_BEARING_ENDPOINTS):
        return []

    if isinstance(response, dict):
        data = response
    else:
        try:
            data = json.loads(response)
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    tweets: list[dict] = []

    def traverse(obj: Any) -> None:
        if isinstance(obj, list):
            # upstream JS for...in walks arrays too (e.g. instructions lists)
            for sub in obj:
                traverse(sub)
            return
        if not isinstance(obj, dict):
            return
        # upstream checks the traversed object itself: an instruction dict
        # carrying `entries` (TimelineAddEntries) or a TimelinePinEntry
        entries = None
        is_entries = ((("type" in obj and obj["type"] == "TimelineAddEntries")
                       or ("type" not in obj and len(obj) == 1))
                      and "entries" in obj)
        if is_entries:
            entries = obj["entries"]
        elif obj.get("type") == "TimelinePinEntry":
            entries = [obj["entry"]] if obj.get("entry") else None

        if entries:
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                content = entry.get("content") or {}
                item_content = content.get("itemContent")
                if item_content:
                    if "Cursor" in (item_content.get("itemType") or ""):
                        continue
                    tweet_results = item_content.get("tweet_results")
                    if not tweet_results:
                        continue
                    tweet = tweet_results.get("result")
                    if not tweet or tweet.get("__typename") == "TweetUnavailable":
                        continue
                    if "tweet" in tweet:
                        tweet = tweet["tweet"]
                    tweet["id"] = tweet.get("legacy", {}).get("id_str", "")
                    tweet["promoted"] = "promotedMetadata" in item_content
                    tweets.append(tweet)
                elif content.get("__typename") == "TimelineTimelineModule":
                    for item in content.get("items") or []:
                        item_content = (item or {}).get("item", {}).get("itemContent")
                        if not item_content or item_content.get("__typename") not in (
                                "Tweet", "TimelineTweet"):
                            continue
                        reply = (item_content.get("tweet_results") or {}).get("result")
                        if not reply or reply.get("__typename") == "TweetUnavailable":
                            continue
                        if "tweet" in reply:
                            reply = reply["tweet"]
                        if not reply.get("rest_id"):
                            continue
                        # keep the id a string: post ids passed 2^53 long ago
                        tweets.append({**reply, "id": reply["rest_id"]})
                else:
                    entry_id = entry.get("entryId") or ""
                    if entry_id.startswith("tweet-"):
                        tweet_id = entry_id.split("-")[1]
                    elif entry_id.startswith("sq-I-t-"):
                        tweet_id = entry_id.split("-")[3]
                    else:
                        continue
                    legacy_tweet = (data.get("globalObjects") or {}).get(
                        "tweets", {}).get(tweet_id)
                    if not legacy_tweet:
                        continue
                    tweet = {"id": str(tweet_id), "legacy": legacy_tweet,
                             "type": "adaptive"}
                    tweet["user"] = (data.get("globalObjects") or {}).get(
                        "users", {}).get(legacy_tweet.get("user_id_str", ""))
                    tweets.append(tweet)
            return

        for child in obj.values():
            if not child:
                continue
            if isinstance(child, (dict, list)):
                traverse(child)
    traverse(data)
    return tweets


def _map_user(user_result: Any) -> dict:
    if not isinstance(user_result, dict):
        user_result = {}
    core = user_result.get("core") or {}
    legacy = user_result.get("legacy") or {}
    avatar = user_result.get("avatar") or {}
    banner = user_result.get("banner") or {}
    counts = user_result.get("relationship_counts") or {}
    profile_bio = user_result.get("profile_bio") or {}
    location = user_result.get("location") or {}

    def first(*values: Any) -> Any:
        for v in values:
            if v is not None and v != "":
                return v
        return ""

    return {
        "screen_name": core.get("screen_name") or legacy.get("screen_name") or "",
        "fullname": core.get("name") or legacy.get("name") or "",
        "avatar_url": avatar.get("image_url") or legacy.get("profile_image_url_https") or "",
        "banner_url": banner.get("image_url") or legacy.get("profile_banner_url") or "",
        "verified": user_result.get("is_blue_verified", ""),
        "followers": first(counts.get("followers"), legacy.get("followers_count")),
        "following": first(counts.get("following"), legacy.get("friends_count")),
        "bio": first((profile_bio or {}).get("description"), legacy.get("description")),
        "location": first((location or {}).get("location"), legacy.get("location")),
    }


def _note_result(tweet: dict) -> dict:
    note = tweet.get("note_tweet") or {}
    return (note.get("note_tweet_results") or {}).get("result") or {}


def _full_text(tweet: dict) -> str:
    text = py_get(tweet, "legacy.full_text", "")
    note_text = py_get(_note_result(tweet), "text", "")
    return note_text if len(note_text or "") > len(text or "") else (text or "")


def _entities(tweet: dict) -> dict:
    entities = py_get(tweet, "legacy.entities", {}) or {}
    note = _note_result(tweet)
    note_entities = note.get("entity_set")
    if not note_entities:
        return entities
    legacy_text = py_get(tweet, "legacy.full_text", "") or ""
    note_text = note.get("text") or ""
    if len(note_text) <= len(legacy_text):
        return entities
    combined = dict(note_entities)
    if entities.get("media"):
        combined["media"] = entities["media"]
    return combined


def _media_lists(tweet: dict) -> tuple[list[str], list[str]]:
    images: list[str] = []
    videos: list[str] = []
    legacy = tweet.get("legacy") or {}
    media_items: list[dict] = []
    for container in ("extended_entities", "entities"):
        arr = (legacy.get(container) or {}).get("media") or []
        if isinstance(arr, list):
            media_items.extend(m for m in arr if isinstance(m, dict))
    for media in media_items:
        if not media.get("media_url_https"):
            continue
        images.append(media["media_url_https"])
        if media.get("type") not in ("video", "animated_gif"):
            continue
        variants = (media.get("video_info") or {}).get("variants") or []
        video_variants = [v for v in variants
                          if str(v.get("content_type", "")).startswith("video/")]
        if video_variants:
            video_variants.sort(key=lambda v: v.get("bitrate") or 0, reverse=True)
            videos.append(video_variants[0]["url"])
    # dedupe preserving order
    return list(dict.fromkeys(images)), list(dict.fromkeys(videos))


def _screen_name_from_url(url: Any) -> str:
    if not isinstance(url, str):
        return ""
    m = re.match(r"^https?://(?:x|twitter)\.com/([^/]+)/status/", url)
    return m.group(1) if m else ""


def _screen_name_from_media(legacy_obj: Any) -> str:
    if not isinstance(legacy_obj, dict):
        return ""
    for container in ("extended_entities", "entities"):
        media = (legacy_obj.get(container) or {}).get("media") or []
        for m in media:
            url = m.get("expanded_url", "") if isinstance(m, dict) else ""
            screen = _screen_name_from_url(url)
            if screen:
                return screen
    return ""


def _centroid(box: Any) -> str:
    try:
        ring = box[0]
        if not isinstance(ring, list) or len(ring) < 2 or not ring[0] or not ring[1]:
            return ""
        lon = str(round((ring[0][0] + ring[1][0]) / 2, 6))
        lat = str(round((ring[0][1] + ring[1][1]) / 2, 6))
        return f"{lon},{lat}"
    except (TypeError, IndexError, KeyError):
        return ""


def _fmt_ts(createdAt: str) -> tuple[str, int]:
    try:
        dt = datetime.strptime(createdAt, "%a %b %d %H:%M:%S %z %Y")
        unix = int(dt.timestamp())
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), unix
    except (TypeError, ValueError):
        return "", 0


def _map_item_modern(tweet: dict, metadata: dict) -> dict:
    author = _map_user((tweet.get("core") or {}).get("user_results", {}).get("result"))
    author_screen = author["screen_name"] or _screen_name_from_media(
        tweet.get("legacy") or {})
    rest_id = tweet.get("rest_id") or tweet.get("id") or ""
    tweet_link = (f"https://x.com/{author_screen}/status/{rest_id}"
                  if author_screen else f"https://x.com/i/web/status/{rest_id}")

    created = py_get(tweet, "legacy.created_at", "")
    timestamp, unix_ts = _fmt_ts(created)

    body = _full_text(tweet)
    retweet_obj = py_get(tweet, "legacy.retweeted_status_result")
    retweeted_user = ""
    withheld = False
    if retweet_obj:
        rt = retweet_obj.get("result") or {}
        if isinstance(rt, dict) and "tweet" in rt:
            rt = rt["tweet"]
        rt_user = _map_user((rt.get("core") or {}).get("user_results", {}).get("result")
                            if isinstance(rt, dict) else {})
        retweeted_user = rt_user["screen_name"] or _screen_name_from_media(
            rt.get("legacy") if isinstance(rt, dict) else {})
        if isinstance(rt, dict) and py_get(rt, "legacy.withheld_scope"):
            withheld = True
            body = _full_text(rt)
        else:
            body = f"RT @{retweeted_user}: {_full_text(rt) if isinstance(rt, dict) else ''}"

    quote_tweet = tweet.get("quoted_status_result")
    if isinstance(quote_tweet, dict) and isinstance(quote_tweet.get("result"), dict) \
            and "tweet" in quote_tweet["result"]:
        quote_tweet = {**quote_tweet, "result": quote_tweet["result"]["tweet"]}
    quote_withheld = bool(isinstance(quote_tweet, dict) and isinstance(
        quote_tweet.get("result"), dict) and quote_tweet["result"].get("tombstone"))

    quote_author = quote_body = ""
    quote_images: list[str] = []
    quote_videos: list[str] = []
    quote_id = py_get(tweet, "legacy.quoted_status_id_str", "")
    if quote_tweet and not quote_withheld:
        quote_result = quote_tweet.get("result") or {}
        quote_user = _map_user((quote_result.get("core") or {}).get(
            "user_results", {}).get("result"))
        quote_author = quote_user["screen_name"] or _screen_name_from_media(
            quote_result.get("legacy"))
        quote_body = _full_text(quote_result)
        quote_images, quote_videos = _media_lists(quote_result)
        quote_id = quote_id or quote_result.get("rest_id", "")
    if not quote_author:
        permalink = py_get(tweet, "legacy.quoted_status_permalink.expanded", "")
        quote_author = _screen_name_from_url(permalink)

    images, videos = _media_lists(tweet)
    entities = _entities(tweet)
    legacy = tweet.get("legacy") or {}
    place = legacy.get("place") or {}

    return {
        "collected_from_url": metadata.get("source_platform_url", ""),
        "id": rest_id,
        "thread_id": py_get(tweet, "legacy.conversation_id_str", ""),
        "timestamp": timestamp,
        "unix_timestamp": unix_ts,
        "link": tweet_link,
        "body": body,
        "author": author_screen,
        "author_fullname": author["fullname"],
        "author_id": py_get(tweet, "legacy.user_id_str", ""),
        "author_avatar_url": author["avatar_url"],
        "author_banner_url": author["banner_url"],
        "author_followers": author["followers"],
        "author_following": author["following"],
        "author_bio": author["bio"],
        "author_location": author["location"],
        "verified": author["verified"],
        "source": strip_tags(tweet.get("source", "")),
        "language_guess": py_get(tweet, "legacy.lang", ""),
        "possibly_sensitive": "yes" if (
            tweet.get("possibly_sensitive")
            or py_get(tweet, "legacy.possibly_sensitive", False)) else "no",
        "retweet_count": py_get(tweet, "legacy.retweet_count", ""),
        "reply_count": py_get(tweet, "legacy.reply_count", ""),
        "like_count": py_get(tweet, "legacy.favorite_count", ""),
        "quote_count": py_get(tweet, "legacy.quote_count", ""),
        "impression_count": py_get(tweet, "views.count", ""),
        "is_retweet": "yes" if retweet_obj else "no",
        "retweeted_user": retweeted_user,
        "is_quote_tweet": "yes" if (quote_id or quote_tweet
                                    or py_get(tweet, "legacy.is_quote_status")) else "no",
        "quote_tweet_id": str(quote_id or ""),
        "quote_author": quote_author,
        "quote_body": quote_body,
        "quote_images": ",".join(quote_images),
        "quote_videos": ",".join(quote_videos),
        "is_quote_withheld": "yes" if quote_withheld else "no",
        "is_reply": "yes" if str(py_get(tweet, "legacy.conversation_id_str", "")) != str(rest_id) else "no",
        "replied_author": py_get(tweet, "legacy.in_reply_to_screen_name", ""),
        "is_withheld": "yes" if withheld else "no",
        "hashtags": ",".join(h["text"] for h in (entities.get("hashtags") or [])
                             if isinstance(h, dict) and h.get("text")),
        "urls": ",".join((u.get("expanded_url") or u.get("display_url") or "")
                         for u in (entities.get("urls") or []) if isinstance(u, dict)),
        "images": ",".join(images),
        "videos": ",".join(videos),
        "mentions": ",".join(m["screen_name"] for m in (entities.get("user_mentions") or [])
                             if isinstance(m, dict) and m.get("screen_name")),
        "long_lat": _centroid((place.get("bounding_box") or {}).get("coordinates")) if place else "",
        "place_name": place.get("full_name", ""),
    }


def _map_item_legacy(tweet: dict, metadata: dict) -> dict:
    legacy = tweet.get("legacy") or {}
    user = tweet.get("user") or {}
    tweet_id = py_get(tweet, "legacy.id_str", "")
    timestamp, unix_ts = _fmt_ts(py_get(tweet, "legacy.created_at", ""))

    body = py_get(tweet, "legacy.full_text", "") or ""
    retweet_obj = py_get(tweet, "legacy.retweeted_status_result")
    withheld = False
    retweeted_user = ""
    if retweet_obj:
        rt = retweet_obj.get("result") or {}
        rt_legacy = rt.get("legacy") or {} if isinstance(rt, dict) else {}
        if rt_legacy.get("withheld_status"):
            withheld = True
            body = rt_legacy.get("full_text") or ""
        else:
            rt_user = _map_user((rt.get("core") or {}).get("user_results", {}).get("result")
                                if isinstance(rt, dict) else {})
            retweeted_user = rt_user["screen_name"] or py_get(rt, "legacy.screen_name", "")
            body = f"RT @{retweeted_user} {rt_legacy.get('full_text', '')}"

    quote_tweet = tweet.get("quoted_status_result")
    if isinstance(quote_tweet, dict) and isinstance(quote_tweet.get("result"), dict) \
            and "tweet" in quote_tweet["result"]:
        quote_tweet = {**quote_tweet, "result": quote_tweet["result"]["tweet"]}
    quote_id = py_get(tweet, "legacy.quoted_status_id_str", "")
    if not quote_id and isinstance(quote_tweet, dict):
        quote_id = py_get(quote_tweet, "result.rest_id", "")
    is_quote = bool(quote_id or quote_tweet or py_get(tweet, "legacy.is_quote_status"))
    quote_author = ""
    if isinstance(quote_tweet, dict):
        quote_user = _map_user(py_get(quote_tweet, "result.core.user_results.result", {}))
        quote_author = quote_user["screen_name"]
    if not quote_author:
        quote_author = _screen_name_from_url(
            py_get(tweet, "legacy.quoted_status_permalink.expanded", ""))

    extended_media = (legacy.get("extended_entities") or {}).get("media") or []
    entity_media = (legacy.get("entities") or {}).get("media") or []
    all_media = [m for m in (extended_media + entity_media) if isinstance(m, dict)]
    place = legacy.get("place") or {}

    return {
        "collected_from_url": metadata.get("source_platform_url", ""),
        "id": tweet_id,
        "thread_id": py_get(tweet, "legacy.conversation_id_str", ""),
        "timestamp": timestamp,
        "unix_timestamp": unix_ts,
        "link": f"https://x.com/{user.get('screen_name', '')}/status/{tweet_id}",
        "body": body,
        "author": user.get("screen_name", ""),
        "author_fullname": user.get("name", ""),
        "author_id": user.get("id_str", ""),
        "author_avatar_url": "",
        "author_banner_url": "",
        "author_followers": user.get("followers_count", ""),
        "author_following": user.get("friends_count", ""),
        "author_bio": user.get("description", ""),
        "author_location": user.get("location", ""),
        "verified": "",
        "source": strip_tags(legacy.get("source", "")),
        "language_guess": legacy.get("lang", ""),
        "possibly_sensitive": "yes" if legacy.get("possibly_sensitive") else "no",
        "retweet_count": legacy.get("retweet_count", ""),
        "reply_count": legacy.get("reply_count", ""),
        "like_count": legacy.get("favorite_count", ""),
        "quote_count": legacy.get("quote_count", ""),
        "impression_count": py_get(tweet, "ext_views.count", ""),
        "is_retweet": "yes" if retweet_obj else "no",
        "retweeted_user": retweeted_user,
        "is_quote_tweet": "yes" if is_quote else "no",
        "quote_tweet_id": str(quote_id or ""),
        "quote_author": quote_author,
        "quote_body": "",
        "quote_images": "",
        "quote_videos": "",
        "is_quote_withheld": "",
        "is_reply": "yes" if str(py_get(tweet, "legacy.conversation_id_str", "")) != tweet_id else "no",
        "replied_author": py_get(tweet, "legacy.in_reply_to_screen_name", ""),
        "is_withheld": "yes" if withheld else "no",
        "hashtags": ",".join(h["text"] for h in (legacy.get("entities") or {}).get(
            "hashtags", []) if isinstance(h, dict) and h.get("text")),
        "urls": ",".join((u.get("expanded_url") or u.get("display_url") or "")
                         for u in (legacy.get("entities") or {}).get("urls", [])
                         if isinstance(u, dict)),
        "images": ",".join(m["media_url_https"] for m in all_media
                           if m.get("type") == "photo" and m.get("media_url_https")),
        "videos": ",".join(((m.get("video_info") or {}).get("variants") or [{}])[0].get("url", "")
                           for m in all_media if m.get("type") == "video"),
        "mentions": ",".join(m["screen_name"] for m in (legacy.get("entities") or {}).get(
            "user_mentions", []) if isinstance(m, dict) and m.get("screen_name")),
        "long_lat": _centroid((place.get("bounding_box") or {}).get("coordinates")) if place else "",
        "place_name": place.get("full_name", ""),
    }


def map_item(item: dict, metadata: dict | None = None) -> dict:
    """Route one tweet object to the correct parser (upstream logic)."""
    metadata = metadata or {}
    if item.get("rest_id"):
        return _map_item_modern(item, metadata)
    if item.get("type") == "adaptive":
        return _map_item_legacy(item, metadata)
    raise ValueError("Unsupported item shape")