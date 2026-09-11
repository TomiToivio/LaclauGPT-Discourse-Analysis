"""LaclauGPT-native X/Twitter parser.

The parser follows the original LaclauGPT scraper pattern: recognise post-bearing
API responses, route them through small native-object parsers, and map them to a
stable LaclauGPT record. Query IDs are intentionally ignored because X changes
those frequently; stable operation names and payload structure are used instead.

Zeeschuimer is an architectural inspiration for browser/API-response capture,
but this module is an independent LaclauGPT implementation and is not a port of
Zeeschuimer source code.

IMPORTANT: post IDs are always strings.

Author: Tomi Toivio / LaclauGPT
License: CC0 1.0 Universal
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from .common import as_string, first_value, strip_tags, unique

MODULE_NAME = "X/Twitter"
DOMAIN = "x.com"
MODULE_ID = "twitter.com"

POST_OPERATIONS = (
    "adaptive.json",
    "HomeTimeline",
    "HomeLatestTimeline",
    "ListLatestTweetsTimeline",
    "SearchTimeline",
    "TweetDetail",
    "UserTweets",
    "UserTweetsAndReplies",
    "UserOriginalsTimeline",
    "UserRepliesTimeline",
    "UserRepostsTimeline",
    "UserPhotoTimeline",
    "UserVideoTimeline",
    "ExplorePage",
    "Likes",
)


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except (TypeError, ValueError):
        return ""


def _endpoint_carries_posts(url: str) -> bool:
    if not url:
        return True
    return any(operation in url for operation in POST_OPERATIONS)


def _unwrap_tweet(value: Any) -> dict | None:
    current = value
    for _ in range(3):
        if not isinstance(current, dict):
            return None
        if current.get("__typename") == "TweetUnavailable":
            return None
        nested = current.get("tweet")
        if isinstance(nested, dict):
            current = nested
            continue
        break
    return current if isinstance(current, dict) else None


def _tweet_id(tweet: dict) -> str:
    legacy = tweet.get("legacy") if isinstance(tweet.get("legacy"), dict) else {}
    return as_string(first_value(tweet.get("rest_id"), tweet.get("id"), legacy.get("id_str")))


def _copy_with_id(tweet: dict) -> dict:
    copied = dict(tweet)
    copied["id"] = _tweet_id(tweet)
    return copied


def _timeline_candidates(root: Any) -> list[dict]:
    """Collect tweet results from timeline instructions without mirroring query IDs."""
    found: list[dict] = []
    seen_objects: set[int] = set()

    def take_entry(entry: Any) -> None:
        if not isinstance(entry, dict):
            return
        content = entry.get("content") or entry.get("item") or entry
        if not isinstance(content, dict):
            return
        item_content = content.get("itemContent")
        if not isinstance(item_content, dict):
            nested_item = content.get("item")
            item_content = nested_item.get("itemContent") if isinstance(nested_item, dict) else None

        result = (
            (item_content.get("tweet_results") or {}).get("result")
            if isinstance(item_content, dict)
            else None
        )
        if result:
            tweet = _unwrap_tweet(result)
            if tweet and _tweet_id(tweet):
                found.append(_copy_with_id(tweet))

        for module_item in content.get("items") or []:
            if not isinstance(module_item, dict):
                continue
            nested = (module_item.get("item") or {}).get("itemContent") or module_item.get("itemContent")
            if not isinstance(nested, dict):
                continue
            result = (nested.get("tweet_results") or {}).get("result")
            tweet = _unwrap_tweet(result)
            if tweet and _tweet_id(tweet):
                found.append(_copy_with_id(tweet))

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

        if node.get("type") == "TimelineAddEntries" and isinstance(node.get("entries"), list):
            for entry in node["entries"]:
                take_entry(entry)
            return
        if node.get("type") == "TimelinePinEntry" and node.get("entry"):
            take_entry(node["entry"])
            return
        if isinstance(node.get("entries"), list) and any(
            isinstance(entry, dict) and (entry.get("entryId") or entry.get("content"))
            for entry in node["entries"]
        ):
            for entry in node["entries"]:
                take_entry(entry)

        direct = node.get("tweet_results")
        if isinstance(direct, dict) and direct.get("result"):
            tweet = _unwrap_tweet(direct["result"])
            if tweet and _tweet_id(tweet):
                found.append(_copy_with_id(tweet))
            return

        for key, value in node.items():
            if key in {"legacy", "entities", "extended_entities", "user_results"}:
                continue
            if isinstance(value, (dict, list)):
                walk(value)

    walk(root)
    return found


def _adaptive_candidates(data: dict) -> list[dict]:
    global_objects = data.get("globalObjects") if isinstance(data.get("globalObjects"), dict) else {}
    tweets = global_objects.get("tweets") if isinstance(global_objects.get("tweets"), dict) else {}
    users = global_objects.get("users") if isinstance(global_objects.get("users"), dict) else {}
    found: list[dict] = []

    for tweet_id, legacy in tweets.items():
        if not isinstance(legacy, dict):
            continue
        copied = {
            "id": as_string(tweet_id),
            "type": "adaptive",
            "legacy": legacy,
        }
        user = users.get(as_string(legacy.get("user_id_str")))
        if isinstance(user, dict):
            copied["user"] = user
        found.append(copied)
    return found


def _deduplicate(tweets: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for tweet in tweets:
        tweet_id = _tweet_id(tweet)
        if not tweet_id:
            continue
        previous = by_id.get(tweet_id)
        current_text = as_string((tweet.get("legacy") or {}).get("full_text"))
        previous_text = as_string((previous.get("legacy") or {}).get("full_text")) if previous else ""
        if previous is None or len(current_text) >= len(previous_text):
            copied = dict(tweet)
            copied["id"] = tweet_id
            by_id[tweet_id] = copied
    return list(by_id.values())


def capture(response: Any, source_platform_url: str, source_url: str) -> list[dict]:
    """Extract native tweet objects from one captured X/Twitter response."""
    if _host(source_platform_url) not in {"x.com", "twitter.com"}:
        return []
    if not _endpoint_carries_posts(source_url or ""):
        return []

    if isinstance(response, dict):
        data = response
    elif isinstance(response, str):
        try:
            data = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            return []
    else:
        return []

    if isinstance(data.get("globalObjects"), dict) and isinstance(
        data["globalObjects"].get("tweets"), dict
    ):
        return _deduplicate(_adaptive_candidates(data))
    return _deduplicate(_timeline_candidates(data))


def _user_from_modern(tweet: dict) -> dict:
    core = tweet.get("core") if isinstance(tweet.get("core"), dict) else {}
    user_results = core.get("user_results") if isinstance(core.get("user_results"), dict) else {}
    result = user_results.get("result") if isinstance(user_results.get("result"), dict) else {}
    if not result and isinstance(tweet.get("user"), dict):
        result = tweet["user"]

    result_core = result.get("core") if isinstance(result.get("core"), dict) else {}
    legacy = result.get("legacy") if isinstance(result.get("legacy"), dict) else result
    counts = result.get("relationship_counts") if isinstance(result.get("relationship_counts"), dict) else {}
    avatar = result.get("avatar") if isinstance(result.get("avatar"), dict) else {}
    banner = result.get("banner") if isinstance(result.get("banner"), dict) else {}
    profile_bio = result.get("profile_bio") if isinstance(result.get("profile_bio"), dict) else {}
    location_obj = result.get("location") if isinstance(result.get("location"), dict) else {}

    return {
        "id": as_string(first_value(result.get("rest_id"), legacy.get("id_str"))),
        "screen_name": as_string(first_value(result_core.get("screen_name"), legacy.get("screen_name"), result.get("screen_name"))),
        "name": as_string(first_value(result_core.get("name"), legacy.get("name"), result.get("name"))),
        "avatar": as_string(first_value(avatar.get("image_url"), legacy.get("profile_image_url_https"))),
        "banner": as_string(first_value(banner.get("image_url"), legacy.get("profile_banner_url"))),
        "followers": first_value(counts.get("followers"), legacy.get("followers_count"), ""),
        "following": first_value(counts.get("following"), legacy.get("friends_count"), ""),
        "bio": as_string(first_value(profile_bio.get("description"), legacy.get("description"), result.get("description"))),
        "location": as_string(first_value(location_obj.get("location"), legacy.get("location"), result.get("location"))),
        "verified": first_value(result.get("is_blue_verified"), legacy.get("verified"), result.get("verified"), ""),
    }


def _user_from_legacy(tweet: dict) -> dict:
    user = tweet.get("user") if isinstance(tweet.get("user"), dict) else {}
    return {
        "id": as_string(first_value(user.get("id_str"), user.get("id"))),
        "screen_name": as_string(user.get("screen_name")),
        "name": as_string(user.get("name")),
        "avatar": as_string(user.get("profile_image_url_https")),
        "banner": as_string(user.get("profile_banner_url")),
        "followers": first_value(user.get("followers_count"), ""),
        "following": first_value(user.get("friends_count"), ""),
        "bio": as_string(user.get("description")),
        "location": as_string(user.get("location")),
        "verified": first_value(user.get("verified"), ""),
    }


def _tweet_text(tweet: dict) -> str:
    note = tweet.get("note_tweet") if isinstance(tweet.get("note_tweet"), dict) else {}
    note_results = note.get("note_tweet_results") if isinstance(note.get("note_tweet_results"), dict) else {}
    note_result = note_results.get("result") if isinstance(note_results.get("result"), dict) else {}
    legacy = tweet.get("legacy") if isinstance(tweet.get("legacy"), dict) else tweet
    return as_string(first_value(note_result.get("text"), legacy.get("full_text"), legacy.get("text"), tweet.get("text"), ""))


def _entities(tweet: dict) -> dict:
    legacy = tweet.get("legacy") if isinstance(tweet.get("legacy"), dict) else tweet
    entities = legacy.get("entities") if isinstance(legacy.get("entities"), dict) else {}
    note = tweet.get("note_tweet") if isinstance(tweet.get("note_tweet"), dict) else {}
    note_result = ((note.get("note_tweet_results") or {}).get("result") or {}) if note else {}
    note_entities = note_result.get("entity_set") if isinstance(note_result, dict) else None
    if not isinstance(note_entities, dict):
        return entities
    if len(as_string(note_result.get("text"))) <= len(as_string(legacy.get("full_text"))):
        return entities
    merged = dict(note_entities)
    if entities.get("media"):
        merged["media"] = entities["media"]
    return merged


def _media(tweet: dict) -> tuple[list[str], list[str]]:
    legacy = tweet.get("legacy") if isinstance(tweet.get("legacy"), dict) else tweet
    rows: list[dict] = []
    for container in ("extended_entities", "entities"):
        block = legacy.get(container)
        media = block.get("media") if isinstance(block, dict) else None
        if isinstance(media, list):
            rows.extend(row for row in media if isinstance(row, dict))

    images: list[str] = []
    videos: list[str] = []
    for row in rows:
        if row.get("media_url_https"):
            images.append(as_string(row["media_url_https"]))
        variants = (row.get("video_info") or {}).get("variants") if isinstance(row.get("video_info"), dict) else []
        if not isinstance(variants, list):
            continue
        mp4 = [
            variant
            for variant in variants
            if isinstance(variant, dict)
            and as_string(variant.get("content_type")).startswith("video/")
            and variant.get("url")
        ]
        if mp4:
            best = max(mp4, key=lambda variant: int(variant.get("bitrate") or 0))
            videos.append(as_string(best["url"]))
    return unique(images), unique(videos)


def _timestamp(created_at: Any) -> tuple[str, int]:
    if not created_at:
        return "", 0
    try:
        dt = datetime.strptime(as_string(created_at), "%a %b %d %H:%M:%S %z %Y")
    except (TypeError, ValueError):
        return "", 0
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), int(dt.timestamp())


def _quote_data(tweet: dict) -> tuple[str, str, str, list[str], list[str]]:
    legacy = tweet.get("legacy") if isinstance(tweet.get("legacy"), dict) else {}
    quote_id = as_string(legacy.get("quoted_status_id_str"))
    quote_result = tweet.get("quoted_status_result")
    if isinstance(quote_result, dict):
        quote_result = quote_result.get("result")
    quote = _unwrap_tweet(quote_result)
    if not quote:
        return quote_id, "", "", [], []

    quote_id = quote_id or _tweet_id(quote)
    user = _user_from_modern(quote)
    images, videos = _media(quote)
    return quote_id, user["screen_name"], _tweet_text(quote), images, videos


def map_item(tweet: dict, metadata: dict | None = None) -> dict:
    """Map one native tweet object to the stable collector record shape."""
    metadata = metadata or {}
    legacy = tweet.get("legacy") if isinstance(tweet.get("legacy"), dict) else tweet
    adaptive = tweet.get("type") == "adaptive"
    user = _user_from_legacy(tweet) if adaptive else _user_from_modern(tweet)

    tweet_id = _tweet_id(tweet)
    timestamp, unix_ts = _timestamp(legacy.get("created_at"))
    entities = _entities(tweet)
    images, videos = _media(tweet)
    hashtags = unique(as_string(row.get("text")) for row in entities.get("hashtags") or [] if isinstance(row, dict) and row.get("text"))
    mentions = unique(as_string(row.get("screen_name")) for row in entities.get("user_mentions") or [] if isinstance(row, dict) and row.get("screen_name"))
    urls = unique(as_string(first_value(row.get("expanded_url"), row.get("unwound_url"), row.get("url"))) for row in entities.get("urls") or [] if isinstance(row, dict))

    author = user["screen_name"]
    link = f"https://x.com/{author}/status/{tweet_id}" if author else f"https://x.com/i/web/status/{tweet_id}"
    reply_to = as_string(legacy.get("in_reply_to_status_id_str"))
    conversation = as_string(first_value(legacy.get("conversation_id_str"), tweet_id))
    quote_id, quote_author, quote_body, quote_images, quote_videos = _quote_data(tweet)
    retweet_obj = legacy.get("retweeted_status_result") or tweet.get("retweeted_status_result")
    is_quote = bool(quote_id or legacy.get("is_quote_status"))

    body = _tweet_text(tweet)
    retweeted_user = ""
    if isinstance(retweet_obj, dict):
        retweeted = _unwrap_tweet(retweet_obj.get("result") or retweet_obj)
        if retweeted:
            rt_user = _user_from_modern(retweeted)
            retweeted_user = rt_user["screen_name"]
            rt_text = _tweet_text(retweeted)
            body = f"RT @{retweeted_user}: {rt_text}" if retweeted_user else rt_text

    return {
        "collected_from_url": metadata.get("source_platform_url", ""),
        "id": tweet_id,
        "thread_id": conversation,
        "timestamp": timestamp,
        "unix_timestamp": unix_ts,
        "link": link,
        "body": body,
        "author": author,
        "author_fullname": user["name"],
        "author_id": as_string(first_value(legacy.get("user_id_str"), user["id"])),
        "author_avatar_url": user["avatar"],
        "author_banner_url": user["banner"],
        "author_followers": user["followers"],
        "author_following": user["following"],
        "author_bio": user["bio"],
        "author_location": user["location"],
        "verified": user["verified"],
        "source": strip_tags(as_string(tweet.get("source") or legacy.get("source"))),
        "language_guess": as_string(legacy.get("lang")),
        "possibly_sensitive": "yes" if legacy.get("possibly_sensitive") or tweet.get("possibly_sensitive") else "no",
        "retweet_count": first_value(legacy.get("retweet_count"), ""),
        "reply_count": first_value(legacy.get("reply_count"), ""),
        "like_count": first_value(legacy.get("favorite_count"), ""),
        "quote_count": first_value(legacy.get("quote_count"), ""),
        "impression_count": first_value((tweet.get("views") or {}).get("count"), ""),
        "is_retweet": "yes" if retweet_obj else "no",
        "retweeted_user": retweeted_user,
        "is_quote_tweet": "yes" if is_quote else "no",
        "quote_tweet_id": quote_id,
        "quote_author": quote_author,
        "quote_body": quote_body,
        "quote_images": ",".join(quote_images),
        "quote_videos": ",".join(quote_videos),
        "is_reply": "yes" if reply_to else "no",
        "reply_to_tweet_id": reply_to,
        "hashtags": ",".join(hashtags),
        "mentions": ",".join(mentions),
        "urls": ",".join(urls),
        "images": ",".join(images),
        "videos": ",".join(videos),
    }
