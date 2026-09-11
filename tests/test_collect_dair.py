from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from laclaugpt.collect import CollectionStore
from laclaugpt.collect.dair import (
    HttpResponse,
    bluesky_pages,
    discover_dair_links,
    discover_peertube_channels,
    extract_buzzsprout_transcript,
    load_profile,
    map_bluesky_item,
    map_buzzsprout_entry,
    map_mastodon_status,
    map_peertube_video,
    mastodon_pages,
    peertube_records,
    select_peertube_caption,
)

CFG = {
    "project": "ai26",
    "arena": "elites",
    "source_group": "dair-critical-ai",
    "selection_rationale": "provisional sampling",
}
SOURCE = {"key": "synthetic"}


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return HttpResponse(next(self.responses), url)


def test_website_discovery_is_same_section_and_deduplicated():
    page = (
        '<a href="/blog/a/">A</a>'
        '<a href="https://dair-institute.org/blog/a/#x">A</a>'
        '<a href="/publications/no">No</a>'
        '<a href="https://other.test/blog/x">X</a>'
    )
    assert discover_dair_links("https://dair-institute.org/blog/", page) == [
        "https://dair-institute.org/blog/a/"
    ]


def test_mastodon_resolution_pagination_and_incremental_checkpoint():
    statuses = [{"id": str(100 - i)} for i in range(40)]
    client = FakeClient([{"id": "acct1"}, statuses, []])
    pages = list(
        mastodon_pages(
            {"account": "example.social/@researcher", "max_pages": 2},
            client,
            "77",
        )
    )
    assert pages[0][1] == "100"
    assert "since_id=77" in client.urls[1]
    assert "max_id=61" in client.urls[2]
    assert "since_id=77" in client.urls[2]


def test_mastodon_unresolved_and_malformed_fail():
    with pytest.raises(ValueError):
        list(mastodon_pages({"account": "x.test/@n"}, FakeClient([{}])))
    with pytest.raises(ValueError):
        list(
            mastodon_pages(
                {"account": "x.test/@n"},
                FakeClient([{"id": "1"}, {}]),
            )
        )


def test_mastodon_reply_mapping_retains_context_html_and_global_identity():
    status = {
        "id": "10",
        "url": "https://x/@a/10",
        "uri": "https://x/users/a/statuses/10",
        "created_at": "2026-01-01T00:00:00Z",
        "content": "<p>Hello <b>world</b></p>",
        "spoiler_text": "CW",
        "language": "en",
        "in_reply_to_id": "9",
        "in_reply_to_account_id": "2",
        "conversation_id": "c",
        "account": {"acct": "a", "url": "https://x/@a"},
        "tags": [],
        "mentions": [],
        "media_attachments": [],
        "replies_count": 1,
        "reblogs_count": 2,
        "favourites_count": 3,
    }
    rec = map_mastodon_status(status, CFG, SOURCE)
    assert rec.native_id == "https://x/users/a/statuses/10"
    assert rec.metadata["relation_type"] == "reply"
    assert rec.metadata["original_html"].startswith("<p>")
    assert rec.text == "Hello world"
    assert rec.metadata["classification_state"] == "unjudged"
    assert rec.metadata["text_origin"] == "platform_text"


def test_mastodon_boost_keeps_booster_and_boosted_actor_separate():
    original = {
        "id": "9",
        "uri": "https://remote/users/b/statuses/9",
        "content": "boosted",
        "account": {"acct": "b", "url": "https://remote/@b"},
    }
    outer = {
        "id": "10",
        "uri": "https://x/users/a/statuses/10",
        "url": "https://x/@a/10",
        "account": {"acct": "a", "url": "https://x/@a"},
        "reblog": original,
    }
    rec = map_mastodon_status(outer, CFG, SOURCE)
    assert rec.author == "a"
    assert rec.metadata["relation_type"] == "boost"
    assert rec.metadata["boosted_account"] == "b"
    assert rec.metadata["boosted_status_uri"].endswith("/9")


def _bsky(record=None, embed=None, reason=None, uri=None):
    item = {
        "post": {
            "uri": uri or "at://did:plc:a/app.bsky.feed.post/1",
            "cid": "c1",
            "author": {"did": "did:plc:a", "handle": "a.test"},
            "record": record
            or {"text": "post", "createdAt": "2026-01-01T00:00:00Z"},
            "replyCount": 1,
            "repostCount": 2,
            "likeCount": 3,
            "quoteCount": 4,
        }
    }
    if embed is not None:
        item["post"]["record"]["embed"] = embed
    if reason is not None:
        item["reason"] = reason
    return item


def test_bluesky_resolves_did_and_stops_at_previous_top_uri():
    newest = _bsky(uri="at://did:plc:a/app.bsky.feed.post/3")
    old_top = _bsky(uri="at://did:plc:a/app.bsky.feed.post/2")
    older = _bsky(uri="at://did:plc:a/app.bsky.feed.post/1")
    client = FakeClient(
        [
            {"did": "did:plc:abc"},
            {"feed": [newest, old_top, older], "cursor": "next"},
        ]
    )
    pages = list(
        bluesky_pages(
            {"handle": "a.test", "max_pages": 5},
            client,
            "at://did:plc:a/app.bsky.feed.post/2",
        )
    )
    assert pages == [([newest], "at://did:plc:a/app.bsky.feed.post/3")]
    assert "actor=did%3Aplc%3Aabc" in client.urls[1]
    assert len(client.urls) == 2


@pytest.mark.parametrize(
    ("item", "relation"),
    [
        (_bsky(), "original"),
        (
            _bsky(
                {
                    "text": "r",
                    "reply": {
                        "parent": {"uri": "p"},
                        "root": {"uri": "r"},
                    },
                }
            ),
            "reply",
        ),
        (_bsky(embed={"$type": "app.bsky.embed.record"}), "quote"),
        (
            _bsky(reason={"$type": "app.bsky.feed.defs#reasonRepost"}),
            "repost",
        ),
    ],
)
def test_bluesky_relation_mapping(item, relation):
    rec = map_bluesky_item(item, CFG, SOURCE)
    assert rec.metadata["relation_type"] == relation
    assert rec.metadata["actor_id"] == "did:plc:a"
    assert rec.native_id.startswith("at://")
    rec.to_source_item()


def test_peertube_discovers_only_configured_account_channels():
    source = {"instance": "https://video.test", "account": "dair"}
    client = FakeClient([{"data": [{"name": "events"}, {"name": "podcast"}]}])
    channels = discover_peertube_channels(source, client)
    assert [channel["name"] for channel in channels] == ["events", "podcast"]
    assert "/api/v1/accounts/dair/video-channels?count=100" in client.urls[0]


def test_peertube_caption_priority_prefers_creator_over_auto():
    payload = {
        "data": [
            {
                "language": {"id": "en"},
                "automaticallyGenerated": True,
                "fileUrl": "https://video.test/auto.vtt",
            },
            {
                "language": {"id": "fi"},
                "automaticallyGenerated": False,
                "fileUrl": "https://video.test/creator-fi.vtt",
            },
        ]
    }
    caption = select_peertube_caption(payload, ("en", "fi"))
    assert caption is not None
    assert caption["automaticallyGenerated"] is False


def test_peertube_auto_caption_is_machine_generated_and_multimodal_off():
    video = {
        "uuid": "v1",
        "name": "Synthetic video",
        "description": "description",
        "publishedAt": "2026-09-10T00:00:00Z",
        "channel": {"name": "events", "displayName": "Events"},
        "account": {"name": "dair"},
        "language": {"id": "en"},
    }
    caption = {
        "language": {"id": "en"},
        "automaticallyGenerated": True,
        "fileUrl": "https://video.test/auto.vtt",
    }
    source = {"key": "peertube", "instance": "https://video.test"}
    rec = map_peertube_video(
        video,
        CFG,
        source,
        caption=caption,
        transcript="machine caption",
    )
    assert rec.text == "machine caption"
    assert rec.metadata["source_modality"] == "video"
    assert rec.metadata["text_origin"] == "platform_auto_caption"
    assert rec.metadata["verification_state"] == "machine_generated_unverified"
    assert rec.metadata["multimodal_enabled"] is False
    assert rec.metadata["asr_required"] is False


def test_peertube_records_fetch_creator_caption_before_asr():
    source = {
        "key": "peertube",
        "instance": "https://video.test",
        "account": "dair",
        "page_size": 100,
        "max_pages_per_channel": 1,
        "preferred_caption_languages": ["en"],
    }
    summary = {
        "uuid": "v1",
        "publishedAt": "2026-09-10T00:00:00Z",
    }
    details = {
        **summary,
        "name": "Captioned",
        "description": "description",
        "channel": {"name": "events", "displayName": "Events"},
        "account": {"name": "dair"},
    }
    client = FakeClient(
        [
            {"data": [{"name": "events"}]},
            {"data": [summary]},
            details,
            {
                "data": [
                    {
                        "language": {"id": "en"},
                        "automaticallyGenerated": False,
                        "captionPath": "/captions/v1.vtt",
                    }
                ]
            },
            "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nCreator caption text\n",
        ]
    )
    items = list(peertube_records(source, client))
    assert len(items) == 1
    assert items[0]["transcript"] == "Creator caption text"
    rec = map_peertube_video(
        details,
        CFG,
        source,
        caption=items[0]["caption"],
        transcript=items[0]["transcript"],
    )
    assert rec.metadata["text_origin"] == "creator_caption"
    assert rec.metadata["asr_required"] is False


def test_buzzsprout_creator_transcript_provenance():
    page = (
        '<main><button>Copy Transcript</button><div>Alex: '
        + ("Public transcript sentence. " * 8)
        + "</div></main>"
    )
    entry = SimpleNamespace(
        id="episode-1",
        link="https://example.test/e/1",
        title="Episode",
        author="Hosts",
        enclosures=[{"href": "https://cdn.test/audio.mp3"}],
        itunes_duration="42:00",
    )
    rec = map_buzzsprout_entry(
        entry,
        page,
        CFG,
        {"key": "pod", "feed_url": "https://feeds.test/rss"},
    )
    assert rec.metadata["text_origin"] == "creator_transcript"
    assert rec.metadata["transcription_method"] == "publisher_supplied"
    assert rec.metadata["verification_state"] == "creator_published"
    assert rec.metadata["multimodal_enabled"] is False
    assert rec.metadata["audio_url"].endswith(".mp3")


def test_missing_transcript_fails_instead_of_silent_asr():
    assert extract_buzzsprout_transcript("<html>No transcript</html>") is None
    entry = SimpleNamespace(id="1", link="https://example.test/e/1")
    with pytest.raises(ValueError):
        map_buzzsprout_entry(
            entry,
            "<html></html>",
            CFG,
            {"key": "p", "feed_url": "f"},
        )


def test_checkpoint_raw_capture_and_dedup(tmp_path: Path):
    store = CollectionStore(tmp_path)
    ref = store.save_raw("mastodon", "native-1", {"id": "native-1"})
    assert json.loads((tmp_path / ref).read_text(encoding="utf-8"))["id"] == "native-1"
    store.set_checkpoint("source", "cursor")
    assert CollectionStore(tmp_path).get_checkpoint("source") == "cursor"
    rec = map_mastodon_status(
        {"id": "1", "uri": "tag:synthetic:1", "content": "x", "account": {}},
        CFG,
        SOURCE,
    )
    rec.raw_payload_ref = ref
    first = store.save(rec)
    assert first is not None
    assert first[1].raw_payload_ref == ref
    assert first[1].dataset_id == "ai26"
    assert store.save(rec) is None


def test_private_profile_switches_and_hygiene(tmp_path: Path):
    profile_path = tmp_path / "dair-private.yaml"
    synthetic = {
        **CFG,
        "sources": [
            {
                "key": "synthetic-enabled",
                "kind": "page",
                "enabled": True,
                "url": "https://example.org/enabled",
            },
            {
                "key": "synthetic-disabled",
                "kind": "page",
                "enabled": False,
                "url": "https://example.org/disabled",
            },
        ],
    }
    profile_path.write_text(yaml.safe_dump(synthetic), encoding="utf-8")
    profile = load_profile(profile_path)
    enabled = {source["key"] for source in profile["sources"] if source["enabled"]}
    assert enabled == {"synthetic-enabled"}
    assert not next(
        source for source in profile["sources"] if source["key"] == "synthetic-disabled"
    )["enabled"]
    serialized = yaml.safe_dump(profile).lower()
    assert "classification_state" not in serialized or "unjudged" in serialized
    assert not any(
        secret in serialized
        for secret in ("api_key", "password", "bearer ", r"c:\users", "/scratch/")
    )

def test_empty_duplicate_or_malformed_source_lists(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("sources: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_profile(bad)

    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text(
        "project: ai26\narena: elites\nsource_group: x\n"
        "sources:\n  - {key: same}\n  - {key: same}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_profile(duplicate)
