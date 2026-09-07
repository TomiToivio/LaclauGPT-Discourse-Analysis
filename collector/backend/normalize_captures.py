# -*- coding: utf-8 -*-
"""Convert autoscraper NDJSON captures into clean per-platform records.

Each captured API response becomes flat item dicts: id, author, body,
timestamp, engagement — merged per account into LaclauGPT-ready JSONL
that z4sync/pipeline can consume directly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def flatten_tiktok(payload: dict) -> list[dict]:
    out = []
    data = payload.get("data") or payload
    items = data.get("itemList") or data.get("item_list") or []
    for it in items:
        author = it.get("author") or {}
        stats = it.get("stats") or it.get("statistics") or {}
        out.append({
            "platform": "tiktok",
            "id": it.get("id") or it.get("aweme_id") or it.get("video_id"),
            "author": author.get("uniqueId") or author.get("unique_id"),
            "body": it.get("desc") or it.get("description"),
            "timestamp": it.get("createTime") or it.get("create_time"),
            "likes": stats.get("diggCount") or stats.get("digg_count"),
            "comments": stats.get("commentCount") or stats.get("comment_count"),
            "shares": stats.get("shareCount") or stats.get("share_count"),
            "plays": stats.get("playCount") or stats.get("play_count"),
        })
    return out


def flatten_x(payload: dict) -> list[dict]:
    """X GraphQL responses are deeply nested; walk to tweet results."""
    out = []

    def walk(node):
        if isinstance(node, dict):
            if "tweet_results" in node:
                res = node["tweet_results"].get("result", {})
                legacy = res.get("legacy", {})
                core = res.get("core", {}).get("user_results", {}) \
                    .get("result", {})
                if legacy.get("id_str"):
                    out.append({
                        "platform": "x",
                        "id": legacy["id_str"],
                        "author": core.get("legacy", {}).get("screen_name"),
                        "body": legacy.get("full_text"),
                        "timestamp": legacy.get("created_at"),
                        "likes": legacy.get("favorite_count"),
                        "comments": legacy.get("reply_count"),
                        "shares": legacy.get("retweet_count"),
                    })
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    return out


def flatten_instagram(payload: dict) -> list[dict]:
    out = []
    data = payload if isinstance(payload, dict) else {}
    items = (data.get("data") or {}).get("user", {}) \
        .get("edge_owner_to_timeline_media", {}).get("edges", [])
    if not items:
        items = data.get("items", []) or []
    for edge in items:
        node = edge.get("node", edge)
        if not node.get("id") and not node.get("pk"):
            continue
        out.append({
            "platform": "instagram",
            "id": node.get("id") or node.get("pk"),
            "author": (node.get("owner") or {}).get("username"),
            "body": (node.get("edge_caption_to_comment") or {}) and
                    (node.get("accessibility_caption") or ""),
            "timestamp": node.get("taken_at_timestamp") or node.get("taken_at"),
            "likes": (node.get("edge_liked_by") or {}).get("count")
                     or node.get("like_count"),
            "comments": (node.get("edge_media_to_comment") or {}).get("count"),
            "shares": None,
        })
    return out


FLATTENERS = {"tiktok": flatten_tiktok, "x": flatten_x,
              "instagram": flatten_instagram}


def clean_capture_dir(root: Path, out_root: Path) -> int:
    total = 0
    for platform_dir in sorted(root.iterdir()):
        if not platform_dir.is_dir():
            continue
        platform = platform_dir.name
        flattener = FLATTENERS.get(platform)
        if not flattener:
            continue
        for handle_dir in sorted(platform_dir.iterdir()):
            if not handle_dir.is_dir():
                continue
            seen: set = set()
            records: list[dict] = []
            for ndjson in sorted(handle_dir.glob("*.ndjson")):
                for line in open(ndjson, encoding="utf-8"):
                    try:
                        cap = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    for rec in flattener(cap.get("data") or {}):
                        if rec["id"] and rec["id"] not in seen:
                            seen.add(rec["id"])
                            rec["candidate_source"] = handle_dir.name
                            records.append(rec)
            if records:
                out_file = out_root / f"{platform}_{handle_dir.name}.jsonl"
                out_file.parent.mkdir(parents=True, exist_ok=True)
                with open(out_file, "w", encoding="utf-8") as fh:
                    for rec in records:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                total += len(records)
                print(f"{platform:10} @{handle_dir.name:22} -> {len(records)} items -> {out_file.name}")
    return total


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python clean_captures.py <ndjson_root> <out_root>")
        sys.exit(1)
    n = clean_capture_dir(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"total: {n} unique items")