"""Instagram parsing module.

Adapted from Zeeschuimer's modules/instagram.js
(https://github.com/digitalmethodsinitiative/zeeschuimer),
Copyright (c) Stijn Peeters, Mozilla Public License 2.0.

Modifications for LaclauGPT (2026):
- translated capture() (view allowlist, edge traversal, ad filters,
  requested-reel scoping) and the three map_item parsers (Polaris /
  Graph / itemlist) from JavaScript to Python;
- map_item() emits plain dicts; MissingMappedField sentinel mirrors the
  upstream 4CAT sentinel so exports keep stable shapes;
- overwrite_partial() (partial→full upgrade, full→partial protection)
  is ported for the store layer.

This file is MPL-2.0 like the upstream it adapts; see modules/README.md.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .common import MissingMappedField, py_get

MODULE_NAME = "Instagram (posts & reels)"
DOMAIN = "instagram.com"

# Instagram serves a view's real content AND prefetch over the same
# /graphql/query endpoint; only the open view tells them apart. Upstream
# allowlist (each entry verified upstream 2026-08): responses kept only
# when the visited view is listed here.
VIEWS_SERVING_OWN_POSTS = [
    "frontpage", "explore", "location", "search", "user_posts",
    "user_reels", "user_tagged", "user_reposts",
]

_POSSIBLE_ITEM_LISTS = (
    "items", "edges", "repost_grid_items", "medias", "feed_items",
    "fill_items", "two_by_two_item",
)
_MEDIA_TYPENAMES = ("XIGPolarisVideoMedia", "XIGPolarisImageMedia")
_HASHTAG_RE = re.compile(r"#([^\s!@#$%ˆ&*()_+{}:\"|<>?\[\];',./`~'‘’]+)")

MEDIA_TYPE_PHOTO = 1
MEDIA_TYPE_VIDEO = 2
MEDIA_TYPE_CAROUSEL = 8


def _detect_view(path: list[str], source_url: str) -> str | None:
    """Upstream view classification; None means "drop response"."""
    if path and path[0] in ("direct", "account", "directory", "lite", "legal",
                            "static_resources", "logging_client_events"):
        return None
    if "injected_story_units" in source_url:
        return None
    if not path:
        return "frontpage"
    if path[0] == "explore":
        if len(path) > 1 and path[1] == "locations":
            return "location"
        if len(path) > 1 and path[1] == "search":
            return "search"
        return "explore"
    if path[0] == "popular":
        return "popular"
    if path[0] == "reels":
        return "reels_audio" if len(path) > 1 and path[1] == "audio" else "reels"
    if path[0] == "stories":
        # highlight objects are misleading/incomplete upstream; skipped
        return None
    if path[0] in ("reel", "p"):
        return "single_reel" if path[0] == "reel" else "single_post"
    if len(path) == 1:
        return "user_posts"
    sub = path[1] if len(path) > 1 else ""
    if sub == "tagged":
        return "user_tagged"
    if sub == "reels":
        return "user_reels"
    if sub == "reposts":
        return "user_reposts"
    if sub == "saved":
        return "user_saved"
    if sub == "p":
        return "single_post"
    if sub == "reel":
        return "single_reel"
    return "unknown"


def capture(response: Any, source_platform_url: str, source_url: str) -> list[dict]:
    """Extract Instagram media objects from one captured response."""
    try:
        domain = urlparse(source_platform_url).netloc.lower().replace("www.", "")
    except ValueError:
        return []
    if domain != "instagram.com":
        return []

    path = [p for p in urlparse(source_platform_url).path.split("/") if p]
    view = _detect_view(path, source_url)
    if view is None:
        return []

    # graphql responses are only trusted for views that serve their own
    # posts (prefetch otherwise) — upstream allowlist logic
    if view not in VIEWS_SERVING_OWN_POSTS and (
            source_url.endswith("graphql") or source_url.endswith("graphql/query")):
        return []

    if "/api/v1/discover/web/explore_grid/" in source_url and view != "explore":
        return []

    if isinstance(response, dict):
        datas: list[Any] = [response]
        response_is_json = True
    else:
        if isinstance(response, str) and response.startswith("for (;;);"):
            response = response[len("for (;;);"):]
        datas = []
        response_is_json = False
        try:
            datas.append(json.loads(response))
            response_is_json = True
        except (json.JSONDecodeError, TypeError):
            datas = _extract_embedded_json(response or "")

    if not datas:
        return []
    if (len(datas) == 1 and isinstance(datas[0], dict)
            and "lightspeed_web_request_for_igd" in datas[0]
            and source_url.endswith("graphql")):
        datas = []

    edges: list[dict] = []

    def _take_items(prop: str, holder: dict) -> list | None:
        """Upstream per-property item extraction. Returns item list or None."""
        val: Any = holder[prop]
        if prop in ("edges", "repost_grid_items"):
            nodes = [e.get("node") if isinstance(e, dict) else None
                     for e in (val or [])]
            medias = [n["media"] for n in nodes
                      if isinstance(n, dict) and n.get("media")]
            if medias:
                return medias
            node_media_like = [n for n in nodes
                               if isinstance(n, dict) and "id" in n
                               and ("media_type" in n
                                    or n.get("__typename") in _MEDIA_TYPENAMES)]
            if node_media_like:
                return node_media_like
            nested = [it for n in nodes
                      if isinstance(n, dict) and isinstance(n.get("items"), list)
                      for it in n["items"]]
            if nested:
                return nested
            return val
        if prop in ("medias", "fill_items"):
            if view in ("explore", "search"):
                found: list[Any] = []
                for wrapper in val or []:
                    if not isinstance(wrapper, dict):
                        continue
                    if wrapper.get("media"):
                        found.append(wrapper["media"])
                    clips = wrapper.get("clips")
                    if isinstance(clips, dict) and isinstance(clips.get("items"), list):
                        found.extend(c["media"] for c in clips["items"]
                                     if isinstance(c, dict) and c.get("media"))
                return found
            return None
        if prop == "feed_items":
            return [m.get("media_or_ad") for m in val if isinstance(m, dict)]
        if prop == "items" and isinstance(val, list) and val and all(
                isinstance(i, dict) and "media" in i for i in val):
            if view == "explore" or any(ep in source_url for ep in
                                        ("api/v1/clips/music/", "api/v1/feed/saved/")):
                return [m["media"] for m in val]
            return None
        if prop == "two_by_two_item":
            return [(val.get("channel") or {}).get("media")]
        return val  # generic single-reel popup etc.

    def traverse(obj: Any) -> None:
        if not isinstance(obj, dict):
            return
        for prop, val in obj.items():
            if prop == "xdt_api__v1__feed__timeline__connection":
                if view == "frontpage":
                    for edge in (val or {}).get("edges") or []:
                        node = edge.get("node") if isinstance(edge, dict) else None
                        if not isinstance(node, dict):
                            continue
                        if (node.get("media") is None
                                and isinstance(node.get("explore_story"), dict)
                                and node["explore_story"].get("media")):
                            node = node["explore_story"]
                        media = node.get("media")
                        if (isinstance(media, dict) and "id" in media
                                and isinstance(media.get("user"), dict)
                                and media["user"]):
                            edges.append(media)
                # non-frontpage = background feed request; drop
                continue
            if prop in _POSSIBLE_ITEM_LISTS:
                if isinstance(val, list) and not val:
                    continue
                items = _take_items(prop, obj)
                if not items:
                    continue
                for item in items:
                    if (isinstance(item, dict) and "id" in item
                            and ("media_type" in item
                                 or item.get("__typename") in _MEDIA_TYPENAMES)
                            and "user" in item
                            and ("is_seen" not in item or item["is_seen"] is not False)
                            and item.get("product_type") != "ad"
                            and not (isinstance(item.get("link"), str)
                                     and item["link"].startswith(
                                         "https://www.facebook.com/ads/"))):
                        edges.append(item)
            elif prop in ("xdt_api__v1__feed__user_timeline_graphql_connection",
                          "xdt_location_get_web_info_tab"):
                for edge in (val or {}).get("edges") or []:
                    node = edge.get("node") if isinstance(edge, dict) else None
                    if (isinstance(node, dict) and "id" in node
                            and isinstance(node.get("user"), dict) and node["user"]
                            and node.get("product_type") != "ad"
                            and node.get("ad_action") is None
                            and not (isinstance(node.get("link"), str)
                                     and node["link"].startswith(
                                         "https://www.facebook.com/ads/"))):
                        edges.append(node)
            elif isinstance(val, dict):
                traverse(val)

    for data in datas:
        if data:
            traverse(data)

    if not edges:
        return []

    collected = []
    for edge in edges:
        edge = dict(edge)
        edge["_zs_partial"] = not all(k in edge for k in
                                      ("caption", "video_versions", "media_type"))
        edge["_zs_instagram_view"] = view
        edge["_zs_html_embedded_json"] = not response_is_json
        if edge.get("product_type") != "ad":
            collected.append(edge)

    # a URL naming one specific reel yields only that reel (upstream)
    requested_reel = None
    if path and path[0] == "reel" and len(path) > 1:
        requested_reel = path[1]
    elif path and path[0] == "reels" and len(path) > 1 and path[1] != "audio":
        requested_reel = path[1]
    if requested_reel:
        collected = [e for e in collected if e.get("code") == requested_reel]
    return collected


def _extract_embedded_json(response: str) -> list:
    """Port of upstream extractEmbeddedInstagramJSON (HTML-embedded JSON)."""
    datas: list[Any] = []
    js_prefixes = [
        "{\"require\":[[\"ScheduledServerJS\",\"handle\",null,[{\"__bbox\":{\"require\":[[\"RelayPrefetchedStreamCache\",\"next\",[],[",
        "{\"require\":[[\"ScheduledServerJS\",\"handle\",null,[{\"__bbox\":{\"require\":[[\"PolarisQueryPreloaderCache\",\"add\",[],[",
    ]
    while js_prefixes:
        prefix = js_prefixes.pop(0)
        for line in (response or "").split("\n"):
            if prefix not in line:
                continue
            json_bit = line.split(prefix[:-1])[1].split("</script>")[0].strip()
            if json_bit.endswith(";"):
                json_bit = json_bit[:-1]
            if "adp_PolarisDesktopPostPageRelatedMediaGrid" in json_bit:
                continue
            if "additionalDataLoaded" in prefix:
                json_bit = json_bit[:-1]
            elif not js_prefixes:
                json_bit = json_bit.split("]]}}")[0]
            json_bit = json_bit.split('],["CometResourceScheduler"')[0]
            try:
                extracted = json.loads(json_bit)

                def _unwrap(obj: Any) -> Any:
                    if not isinstance(obj, dict):
                        return None
                    for prop, val in obj.items():
                        if prop == "result" and isinstance(val, dict) and "response" in val:
                            try:
                                return json.loads(val["response"])
                            except (json.JSONDecodeError, TypeError):
                                return None
                        if isinstance(val, dict):
                            res = _unwrap(val)
                            if res is not None:
                                return res
                    return None

                explorer = _unwrap(extracted)
                datas.append(explorer if explorer is not None else extracted)
            except json.JSONDecodeError:
                continue
    return datas


def overwrite_partial(incoming: dict, existing: dict | None) -> bool:
    """Upstream overwrite_partial: partial→full upgrade, never downgrade."""
    if not existing:
        return False
    existing_partial = existing.get("_zs_partial") is True
    incoming_partial = incoming.get("_zs_partial") is True
    return existing_partial and not incoming_partial


def _extract_hashtags(caption: Any) -> str:
    if isinstance(caption, MissingMappedField):
        return ""
    return ",".join(m.group(1) for m in _HASHTAG_RE.finditer(caption or ""))


def _get_author(node: dict) -> dict:
    user = node.get("user") or {}
    owner = node.get("owner") or {}
    if (user.get("username") and owner.get("username")
            and user["username"] != owner["username"]):
        raise ValueError("Unable to parse item: different user and owner")
    author = dict(owner)
    for key, val in user.items():
        if val is not None:
            author[key] = val
    return author


def _get_author_id(node: dict, author: dict) -> Any:
    author_id = author.get("id") or author.get("pk")
    if author_id:
        return author_id
    item_id = node.get("id")
    if isinstance(item_id, str) and "_" in item_id:
        return item_id.split("_")[1]
    return MissingMappedField("")


def _get_image_url(candidates: Any) -> str:
    if not isinstance(candidates, list):
        return ""
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("url"):
            return candidate["url"]
    return ""


def _fmt_ts(unix: Any) -> Any:
    try:
        return datetime.fromtimestamp(int(unix), timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError, OSError):
        return MissingMappedField(0)


def _value_or_missing(obj: dict, key: str, default: Any) -> Any:
    val = obj.get(key)
    return val if val is not None else MissingMappedField(default)


def _location_fields(node: dict, taken_style: str) -> dict:
    """Shared location extraction for the Graph and itemlist parsers."""
    out = {"name": "", "latlong": "", "city": "", "location_id": ""}
    if node.get("location"):
        loc = node["location"]
        out = {
            "name": loc.get("name") or "",
            "location_id": str(loc.get("pk") or ""),
            "latlong": (f"{loc['lat']},{loc['lng']}" if loc.get("lat") else ""),
            "city": loc.get("city") or "",
        }
    return out


def _parse_polaris_item(node: dict) -> dict:
    caption: Any
    if "caption" not in node:
        caption = MissingMappedField("")
    elif not node["caption"]:
        caption = ""
    else:
        caption = node["caption"].get("text", "")
    author = _get_author(node)
    if author.get("is_verified") is None:
        is_verified: Any = MissingMappedField(False)
    else:
        is_verified = bool(author.get("is_verified"))
    type_map = {"XIGPolarisPhotoMedia": "photo", "XIGPolarisVideoMedia": "video",
                "XIGPolarisImageMedia": "photo", "XIGPolarisCarouselMedia": "photo"}
    media_type = type_map.get(node.get("__typename") or "", "unknown")
    num_media = (1 if node.get("__typename") != "XIGPolarisCarouselMedia"
                 else len(node.get("carousel_media") or []))
    video_versions = node.get("video_versions") or []
    if video_versions and isinstance(video_versions[0], dict):
        media_urls: Any = video_versions[0].get("url", "")
    else:
        media_urls = MissingMappedField("")
    return {
        "collected_from_url": py_get(node, "__import_meta.source_platform_url", ""),
        "collected_from_view": node.get("_zs_instagram_view", ""),
        "partial_item": node.get("_zs_partial", False),
        "id": node.get("code"),
        "timestamp": MissingMappedField(0),
        "thread_id": node.get("code"),
        "parent_id": node.get("code"),
        "url": f"https://www.instagram.com/p/{node.get('code', '')}",
        "body": caption,
        "author_id": _get_author_id(node, author),
        "author": _value_or_missing(author, "username", ""),
        "author_fullname": _value_or_missing(author, "full_name", ""),
        "verified": is_verified,
        "author_avatar_url": _value_or_missing(author, "profile_pic_url", ""),
        "media_type": media_type,
        "num_media": num_media,
        "image_urls": _value_or_missing(node, "display_uri", ""),
        "media_urls": media_urls,
        "hashtags": _extract_hashtags(caption),
        "play_count": _value_or_missing(node, "play_count", -1),
        "likes_hidden": MissingMappedField(""),
        "num_likes": MissingMappedField(-1),
        "num_comments": MissingMappedField(-1),
        "location_name": MissingMappedField(""),
        "location_id": MissingMappedField(""),
        "location_latlong": MissingMappedField(""),
        "location_city": MissingMappedField(""),
        "unix_timestamp": MissingMappedField(0),
        "missing_media": None,
    }


def _parse_graph_item(node: dict) -> dict:
    caption: Any = MissingMappedField("")
    try:
        caption = node["edge_media_to_caption"]["edges"][0]["node"]["text"]
    except (KeyError, IndexError, TypeError):
        pass
    sidecar = node.get("edge_sidecar_to_children")
    num_media = ((len(sidecar["edges"]) if sidecar else 0)
                 if node.get("__typename") == "GraphSidecar" else 1)
    media_node = sidecar["edges"][0]["node"] if sidecar else node
    if media_node.get("__typename") == "GraphVideo":
        media_url = media_node.get("video_url") or ""
    elif media_node.get("__typename") == "GraphImage":
        resources = media_node.get("display_resources") or media_node.get(
            "thumbnail_resources") or []
        media_url = (resources[-1].get("src", "") if resources
                     else media_node.get("display_url") or "")
    else:
        media_url = media_node.get("display_url") or ""
    type_map = {"GraphSidecar": "photo", "GraphVideo": "video"}
    if node.get("__typename") != "GraphSidecar":
        media_type = type_map.get(node.get("__typename"), "unknown")
    else:
        types = {e["node"].get("__typename") for e in (sidecar or {}).get("edges", [])
                 if isinstance(e, dict) and isinstance(e.get("node"), dict)}
        media_type = ("mixed" if len(types) > 1
                      else type_map.get(next(iter(types), ""), "unknown"))
    location = _location_fields(node, "graph")
    no_likes = bool(node.get("like_and_view_counts_disabled"))
    author = _get_author(node)
    if node.get("view_count") is not None:
        play_count: Any = node["view_count"]
    elif node.get("play_count") is not None:
        play_count = node["play_count"]
    else:
        play_count = MissingMappedField(-1)
    preview_like = node.get("edge_media_preview_like") or {}
    preview_comment = node.get("edge_media_preview_comment") or {}
    return {
        "id": node.get("shortcode"),
        "collected_from_url": py_get(node, "__import_meta.source_platform_url", ""),
        "collected_from_view": _value_or_missing(node, "_zs_instagram_view", ""),
        "partial_item": _value_or_missing(node, "_zs_partial", ""),
        "timestamp": _fmt_ts(node.get("taken_at_timestamp")),
        "thread_id": node.get("shortcode"),
        "parent_id": node.get("shortcode"),
        "url": f"https://www.instagram.com/p/{node.get('shortcode', '')}",
        "body": caption,
        "author_id": _get_author_id(node, author),
        "author": _value_or_missing(author, "username", ""),
        "author_fullname": _value_or_missing(author, "full_name", ""),
        "verified": bool(author.get("is_verified")),
        "author_avatar_url": _value_or_missing(author, "profile_pic_url", ""),
        "media_type": media_type,
        "num_media": num_media,
        "image_urls": node.get("display_url") or "",
        "media_urls": media_url,
        "hashtags": _extract_hashtags(caption),
        "usertags": ",".join(
            e["node"]["user"]["username"]
            for e in (node.get("edge_media_to_tagged_user") or {}).get("edges", [])
            if isinstance(e, dict) and isinstance(e.get("node"), dict)
            and e["node"].get("user", {}).get("username")),
        "play_count": play_count,
        "likes_hidden": "yes" if no_likes else "no",
        "num_likes": preview_like.get("count", -1) if not no_likes
        else MissingMappedField(-1),
        "num_comments": preview_comment.get("count", -1),
        "location_name": location["name"],
        "location_id": location["location_id"],
        "location_latlong": location["latlong"],
        "location_city": location["city"],
        "unix_timestamp": node.get("taken_at_timestamp"),
        "missing_media": None,
    }


def _parse_itemlist_item(node: dict) -> dict:
    code = node.get("code")
    if not code:
        raise ValueError("Unable to parse item: no post code to identify the post by")
    caption: Any
    if "caption" not in node:
        caption = MissingMappedField("")
    elif not node["caption"]:
        caption = ""
    else:
        caption = node["caption"].get("text", "")
    display_urls: list[str] = []
    media_urls: list[str] = []
    missing_media: Any = None
    type_map = {MEDIA_TYPE_PHOTO: "photo", MEDIA_TYPE_VIDEO: "video"}
    media_types: set[str] = set()
    carousel = node.get("carousel_media") or []
    if node.get("media_type") == MEDIA_TYPE_CAROUSEL:
        num_media = len(carousel) or py_get(node, "carousel_media_count") or 1
    else:
        num_media = 1
    media_nodes = carousel or [node]
    for media_node in media_nodes:
        thumbnail = _get_image_url((media_node.get("image_versions2") or {}).get("candidates"))
        video_versions = media_node.get("video_versions") or []
        video_url = (video_versions[0].get("url", "")
                     if video_versions and isinstance(video_versions[0], dict) else "")
        mtype = media_node.get("media_type")
        if mtype == MEDIA_TYPE_VIDEO:
            if thumbnail:
                display_urls.append(thumbnail)
            elif video_url:
                display_urls.append(video_url)
            if video_url:
                media_urls.append(video_url)
            else:
                missing_media = MissingMappedField("")
        elif mtype == MEDIA_TYPE_PHOTO and thumbnail:
            display_urls.append(thumbnail)
            media_urls.append(thumbnail)
        else:
            missing_media = MissingMappedField("")
        media_types.add({MEDIA_TYPE_PHOTO: "photo",
                         MEDIA_TYPE_VIDEO: "video"}.get(mtype, "unknown"))
    media_type = ("mixed" if len(media_types) > 1
                  else (next(iter(media_types), "unknown")))
    if node.get("comment_count") is not None:
        num_comments: Any = node["comment_count"]
    elif isinstance(node.get("comments"), list):
        num_comments = len(node["comments"])
    else:
        num_comments = MissingMappedField(-1)
    location = _location_fields(node, "itemlist")
    author = _get_author(node)
    if author.get("is_verified") is None:
        is_verified = MissingMappedField(False)
    else:
        is_verified = bool(author.get("is_verified"))
    coauthors, coauthor_fullnames, coauthor_ids = [], [], []
    for co in (node.get("coauthor_producers") or []):
        coauthors.append(co.get("username") or "")
        coauthor_fullnames.append(co.get("full_name") or "")
        coauthor_ids.append(co.get("id") or "")
    no_likes = bool(node.get("like_and_view_counts_disabled"))
    if not no_likes and node.get("like_count") is not None:
        num_likes: Any = node["like_count"]
    else:
        num_likes = MissingMappedField(-1)
    if node.get("view_count") is not None:
        play_count = node["view_count"]
    elif node.get("play_count") is not None:
        play_count = node["play_count"]
    else:
        play_count = MissingMappedField(-1)
    usertags = ""
    if "usertags" in node:
        usertags = ",".join(
            t["user"]["username"]
            for t in ((node.get("usertags") or {}).get("in") or [])
            if isinstance(t, dict) and isinstance(t.get("user"), dict)
            and t["user"].get("username"))
    return {
        "collected_from_url": py_get(node, "__import_meta.source_platform_url", ""),
        "collected_from_view": node.get("_zs_instagram_view", ""),
        "partial_item": node.get("_zs_partial", ""),
        "id": code,
        "timestamp": _fmt_ts(node.get("taken_at")),
        "thread_id": code,
        "parent_id": code,
        "url": f"https://www.instagram.com/p/{code}",
        "body": caption,
        "author_id": _get_author_id(node, author),
        "author": _value_or_missing(author, "username", ""),
        "author_fullname": _value_or_missing(author, "full_name", ""),
        "verified": is_verified,
        "author_avatar_url": _value_or_missing(author, "profile_pic_url", ""),
        "coauthors": ",".join(c for c in coauthors if c),
        "coauthor_fullnames": ",".join(c for c in coauthor_fullnames if c),
        "coauthor_ids": ",".join(c for c in coauthor_ids if c),
        "media_type": media_type,
        "num_media": num_media,
        "image_urls": ",".join(display_urls),
        "media_urls": ",".join(media_urls),
        "hashtags": _extract_hashtags(caption),
        "usertags": usertags,
        "play_count": play_count,
        "likes_hidden": "yes" if no_likes else "no",
        "num_likes": num_likes,
        "num_comments": num_comments,
        "location_name": location["name"],
        "location_id": location["location_id"],
        "location_latlong": location["latlong"],
        "location_city": location["city"],
        "unix_timestamp": _fmt_ts(node.get("taken_at")),
        "missing_media": missing_media,
    }


def map_item(item: dict, metadata: dict | None = None) -> dict:
    """Route one Instagram media object to the correct parser (upstream)."""
    link = py_get(item, "link", "")
    if item.get("product_type") == "ad" or (
            link and str(link).startswith("https://www.facebook.com/ads/ig_redirect")):
        raise ValueError("appears to be Instagram ad; raw data kept for audit")
    typename = py_get(item, "__typename", "")
    if typename and "polaris" in typename.lower():
        return _parse_polaris_item(item)
    if typename and typename.startswith("Graph"):
        return _parse_graph_item(item)
    return _parse_itemlist_item(item)