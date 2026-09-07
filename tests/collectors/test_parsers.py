"""Parser tests — Zeeschuimer-derived modules on synthetic fixtures.

Issue #20 required cases 1-4, 5 (exact-string X IDs), 6 (dedup),
13 (provenance), 14 (raw↔normalised linkage).
"""
from __future__ import annotations

import json

import pytest

from collector.modules import instagram, tiktok, twitter

PLATFORM_URLS = {
    "tiktok": "https://www.tiktok.com/@synthetic_user",
    "instagram": "https://www.instagram.com/synthetic_user/",
    "x": "https://x.com/synthetic_user",
}


# --- 1. TikTok parser --------------------------------------------------------

def test_tiktok_parser_normalizes_fields(tiktok_api_response, tiktok_item):
    items = tiktok.capture(tiktok_api_response, PLATFORM_URLS["tiktok"],
                           "https://www.tiktok.com/api/post/item_list/?count=1")
    assert len(items) == 1
    rec = tiktok.map_item(items[0], {"source_platform_url": PLATFORM_URLS["tiktok"]})
    assert rec["id"] == tiktok_item["id"]
    assert rec["author"] == "synthetic_user"
    assert rec["author_full"] == "Synthetic User"
    assert rec["body"] == tiktok_item["desc"]
    assert rec["timestamp"] == "2024-09-07T16:00:00Z"
    assert rec["tiktok_url"] == f"https://www.tiktok.com/@synthetic_user/video/{tiktok_item['id']}"
    assert rec["likes"] == 1234
    assert rec["plays"] == 90000
    assert rec["hashtags"] == "test,synthetic"
    assert rec["music_name"] == "Synthetic Anthem"
    assert rec["video_url"].startswith("https://example.com/")
    assert rec["thumbnail_url"]  # x-expires far in future -> valid
    assert rec["is_duet"] == "no"
    assert rec["location_created"] == "São Paulo, Brazil"


def test_tiktok_live_liveRoomInfo_filtered():
    data = {"itemList": [{"id": "1", "liveRoomInfo": {"x": 1}},
                         {"id": "2", "desc": "ok", "createTime": "0"}]}
    items = tiktok.capture(data, PLATFORM_URLS["tiktok"], "u")
    assert [i["id"] for i in items] == ["2"]


def test_tiktok_preload_ignored():
    data = {"itemList": [{"id": "3", "desc": "x", "createTime": "0"}]}
    items = tiktok.capture(data, PLATFORM_URLS["tiktok"],
                           "https://www.tiktok.com/api/preload/item_list/?x=1")
    assert items == []


# --- 2/3. Instagram post + reel/video parsers --------------------------------

def test_instagram_post_parser(instagram_itemlist_item):
    rec = instagram.map_item(dict(instagram_itemlist_item), {})
    assert rec["id"] == "SynPost001"
    assert rec["author"] == "synthetic_user"
    assert rec["author_id"] == "9876543210"
    assert rec["body"] == "Synthetic post caption #test"
    assert rec["media_type"] == "photo"
    assert rec["url"] == "https://www.instagram.com/p/SynPost001"
    assert rec["hashtags"] == "test"
    assert rec["num_likes"] == 500
    assert rec["location_name"] == "Praça da Sé"
    assert rec["location_latlong"] == "-23.55,-46.63"
    assert rec["timestamp"] == "2024-09-07T16:00:00Z"


def test_instagram_reel_parser(instagram_reel_item):
    rec = instagram.map_item(dict(instagram_reel_item), {})
    assert rec["id"] == "SynReel001"
    assert rec["media_type"] == "video"
    assert rec["media_urls"] == "https://example.com/reel.mp4"
    assert rec["image_urls"] == "https://example.com/reel_thumb.jpg"
    assert rec["play_count"] == 12000


def test_instagram_polaris_parser(instagram_polaris_item):
    rec = instagram.map_item(dict(instagram_polaris_item), {})
    assert rec["id"] == "SynPolaris01"
    assert rec["media_type"] == "photo"  # XIGPolarisImageMedia
    assert rec["image_urls"] == "https://example.com/polaris.jpg"
    assert rec["body"] == "Synthetic polaris caption"


def test_instagram_capture_user_page(instagram_itemlist_item):
    """Graphql response on a user page with timeline connection yields media."""
    envelope = {
        "data": {
            "xdt_api__v1__feed__user_timeline_graphql_connection": {
                "edges": [{"node": {"id": instagram_itemlist_item["id"],
                                    "user": instagram_itemlist_item["user"],
                                    **instagram_itemlist_item}}],
            }
        }
    }
    out = instagram.capture(envelope, PLATFORM_URLS["instagram"],
                            "https://www.instagram.com/api/graphql/query/")
    assert len(out) == 1
    assert out[0]["code"] == "SynPost001"
    assert out[0]["_zs_instagram_view"] == "user_posts"


def test_instagram_capture_drops_prefetch(instagram_itemlist_item):
    """Graphql response on a NON-allowlisted view (single reel) is dropped."""
    envelope = {"items": [{"id": "1", "media_type": 1,
                           "user": {"username": "x"}}]}
    out = instagram.capture(envelope, "https://www.instagram.com/reel/SynCode001/",
                            "https://www.instagram.com/api/graphql/query")
    assert out == []


def test_instagram_partial_full_upgrade():
    partial = {"id": "1", "user": {"username": "u"}, "media_type": 2,
               "_zs_partial": True}
    full = {**partial, "caption": {"text": "x"}, "video_versions": [{"url": "v"}],
            "_zs_partial": False}
    assert instagram.overwrite_partial(full, partial) is True
    assert instagram.overwrite_partial(partial, full) is False


# --- 4/5. X parser + exact-string IDs ----------------------------------------

def test_x_post_parser_modern(x_modern_tweet):
    rec = twitter.map_item(dict(x_modern_tweet), {})
    assert rec["id"] == "1800000000000000001"
    assert rec["author"] == "synthetic_user"
    assert rec["author_fullname"] == "Synthetic User"
    assert rec["body"].startswith("Synthetic tweet")
    assert rec["timestamp"] == "2026-09-07T12:00:00Z"
    assert rec["thread_id"] == "1800000000000000001"
    assert rec["like_count"] == 42
    assert rec["hashtags"] == "tag1"
    assert rec["mentions"] == "mention"
    assert rec["images"] == "https://example.com/twimg.jpg,https://example.com/twimg2.jpg"
    assert rec["videos"] == "https://example.com/twvid.mp4"  # highest bitrate mp4
    assert rec["language_guess"] == "pt"
    assert rec["source"] == "Synthetic App"


def test_x_id_remains_exact_string(x_graphql_envelope):
    """X IDs exceed 2^53 — JS parseInt silently rounds them; ours stay strings."""
    big_id = "2090457220026626468"  # upstream's example: int(x) -> ...468 rounds in JS float64
    # proof of the hazard in JS semantics: Number(big_id) loses the tail
    assert float(big_id) != int(big_id) or str(int(float(big_id))) != big_id
    tweet = json.loads(json.dumps(x_graphql_envelope))
    entry = tweet["data"]["user"]["result"]["timeline_v2"]["timeline"][
        "instructions"][0]["entries"][0]
    entry["entryId"] = f"tweet-{big_id}"
    entry["content"]["itemContent"]["tweet_results"]["result"] = {
        "__typename": "Tweet", "rest_id": big_id,
        "legacy": {"id_str": big_id, "full_text": "big",
                   "created_at": "Sun Sep 07 12:00:00 +0000 2026"}}
    tweets = twitter.capture(tweet, PLATFORM_URLS["x"],
                             "https://x.com/i/api/graphql/queryId/UserTweets?variables=1")
    assert len(tweets) == 1
    rec = twitter.map_item(tweets[0], {})
    assert rec["id"] == big_id
    assert isinstance(rec["id"], str)


def test_x_post_parser_legacy(x_legacy_tweet):
    rec = twitter.map_item(dict(x_legacy_tweet), {})
    assert rec["id"] == "1800000000000000002"
    assert rec["body"] == "Legacy synthetic tweet"
    assert rec["timestamp"] == "2026-09-08T10:30:00Z"
    assert rec["author_followers"] == 4321


def test_x_capture_operation_name_allowlist(x_graphql_envelope):
    """Only post-bearing operation names are captured (not query IDs)."""
    tweets = twitter.capture(x_graphql_envelope, PLATFORM_URLS["x"],
                             "https://x.com/i/api/graphql/abc123/UserOriginalsTimeline?variables=1")
    assert len(tweets) == 1
    assert tweets[0]["id"] == "1800000000000000001"
    # non-post-bearing endpoint dropped
    tweets2 = twitter.capture(x_graphql_envelope, PLATFORM_URLS["x"],
                              "https://x.com/i/api/graphql/abc123/UnknownOp?variables=1")
    assert tweets2 == []


# --- normalisation layer ------------------------------------------------------

def test_normalise_record_provenance(tiktok_item):
    from collector import normalize

    mapped = tiktok.map_item(tiktok_item, {"source_platform_url": "u"})
    rec = normalize.normalise(
        "tiktok", mapped, tiktok_item,
        {"captured_at": "2026-09-07T10:00:00Z", "collector_version": "0.1.0",
         "git_commit": "abc1234", "source_platform_url": "https://www.tiktok.com/@u",
         "source_url": "https://api.example/item_list", "capture_id": "cap-1",
         "account": "Lula:lulaoficial"})
    assert rec["document_id"] == tiktok_item["id"]
    assert rec["platform"] == "tiktok"
    assert rec["source_url"] == f"https://www.tiktok.com/@synthetic_user/video/{tiktok_item['id']}"
    prov = rec["collection_provenance"]
    assert prov["collector_version"] == "0.1.0"
    assert prov["git_commit"] == "abc1234"
    assert prov["visited_url"] == "https://www.tiktok.com/@u"
    assert prov["api_url"] == "https://api.example/item_list"
    assert prov["capture_id"] == "cap-1"
    assert "zeeschuimer-capture" in prov["transformations"]


def test_normalise_media_refs(tiktok_item, x_modern_tweet):
    from collector import normalize

    mapped = tiktok.map_item(tiktok_item, {})
    rec = normalize.normalise("tiktok", mapped, tiktok_item, {})
    kinds = {r["kind"] for r in rec["media_references"]}
    assert "video" in kinds and "thumbnail" in kinds
    xrec = normalize.normalise("x", twitter.map_item(dict(x_modern_tweet), {}),
                               x_modern_tweet, {})
    xkinds = [r["kind"] for r in xrec_media(xrec)]
    assert "image" in xkinds and "video" in xkinds


def xrec_media(rec):
    return rec["media_references"]


# --- store layer: dedup + raw linkage -----------------------------------------

def test_store_dedup_and_raw_link(tmp_path, tiktok_item):
    from collector import normalize
    from collector.store import Store

    mapped = tiktok.map_item(tiktok_item, {})
    record = normalize.normalise("tiktok", mapped, tiktok_item, {})
    store = Store(tmp_path / "data")
    raw_ref = store.append_raw("tiktok", tiktok_item)
    assert store.upsert_post(record, raw_ref) is True
    # duplicate ignored
    assert store.upsert_post(record, raw_ref) is False
    assert store.seen_count("tiktok") == 1
    # raw representation linked to the normalised record
    lines = open(store.normalized_dir / "tiktok.jsonl", encoding="utf-8").readlines()
    stored = json.loads(lines[-1])
    assert stored["raw_ref"] == raw_ref
    # raw payload reconstructs the record
    raw = json.loads((store.root / raw_ref).read_text(encoding="utf-8"))
    assert raw == tiktok_item
    store.close()