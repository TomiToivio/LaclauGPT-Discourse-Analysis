from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from laclaugpt.collect import CollectionStore
from laclaugpt.collect.dair import (
    HttpResponse, bluesky_pages, discover_dair_links, extract_buzzsprout_transcript,
    load_profile, map_bluesky_item, map_buzzsprout_entry, map_mastodon_status,
    mastodon_pages,
)

CFG = {"project": "ai26", "arena": "elites", "source_group": "dair-critical-ai",
       "selection_rationale": "provisional sampling"}
SOURCE = {"key": "synthetic"}

class FakeClient:
    def __init__(self, responses): self.responses = iter(responses); self.urls = []
    def get(self, url, **kwargs):
        self.urls.append(url); return HttpResponse(next(self.responses), url)


def test_website_discovery_is_same_section_and_deduplicated():
    html = '<a href="/blog/a/">A</a><a href="https://dair-institute.org/blog/a/#x">A</a><a href="/publications/no">No</a><a href="https://other.test/blog/x">X</a>'
    assert discover_dair_links("https://dair-institute.org/blog/", html) == ["https://dair-institute.org/blog/a/"]


def test_mastodon_resolution_pagination_and_checkpoint():
    statuses = [{"id": str(i)} for i in range(40)]
    client = FakeClient([{"id": "acct1"}, statuses, []])
    pages = list(mastodon_pages({"account": "example.social/@researcher"}, client, "older"))
    assert pages[0][1] == "39"
    assert "max_id=older" in client.urls[1]
    assert "max_id=39" in client.urls[2]


def test_mastodon_unresolved_and_malformed_fail():
    with pytest.raises(ValueError): list(mastodon_pages({"account": "x.test/@n"}, FakeClient([{}])))
    with pytest.raises(ValueError): list(mastodon_pages({"account": "x.test/@n"}, FakeClient([{"id": "1"}, {}])))


def test_mastodon_reply_mapping_retains_context_and_html():
    status = {"id": "10", "url": "https://x/@a/10", "uri": "tag:10", "created_at": "2026-01-01T00:00:00Z",
              "content": "<p>Hello <b>world</b></p>", "spoiler_text": "CW", "language": "en",
              "in_reply_to_id": "9", "in_reply_to_account_id": "2", "conversation_id": "c",
              "account": {"acct": "a", "url": "https://x/@a"}, "tags": [], "mentions": [],
              "media_attachments": [], "replies_count": 1, "reblogs_count": 2, "favourites_count": 3}
    rec = map_mastodon_status(status, CFG, SOURCE)
    assert rec.metadata["relation_type"] == "reply"
    assert rec.metadata["original_html"].startswith("<p>")
    assert rec.text == "Hello  world"
    assert rec.metadata["classification_state"] == "unjudged"


def test_mastodon_boost_mapping():
    original = {"id": "9", "content": "boosted", "account": {"acct": "b"}}
    rec = map_mastodon_status({"id": "10", "url": "https://x/10", "reblog": original}, CFG, SOURCE)
    assert rec.metadata["relation_type"] == "boost"


def test_bluesky_resolves_stable_did_and_pages():
    feed = [{"post": {"uri": "at://did/a/1", "record": {"text": "x"}}}]
    client = FakeClient([{"did": "did:plc:abc"}, {"feed": feed, "cursor": "next"}, {"feed": []}])
    pages = list(bluesky_pages({"handle": "a.test", "did": "did:plc:abc"}, client))
    assert pages == [(feed, "next")]
    assert "actor=did%3Aplc%3Aabc" in client.urls[1]


def _bsky(record=None, embed=None, reason=None):
    item = {"post": {"uri": "at://did:plc:a/app.bsky.feed.post/1", "cid": "c1",
                     "author": {"did": "did:plc:a", "handle": "a.test"},
                     "record": record or {"text": "post", "createdAt": "2026-01-01T00:00:00Z"},
                     "replyCount": 1, "repostCount": 2, "likeCount": 3, "quoteCount": 4}}
    if embed is not None: item["post"]["record"]["embed"] = embed
    if reason is not None: item["reason"] = reason
    return item


@pytest.mark.parametrize(("item", "relation"), [
    (_bsky(), "original"),
    (_bsky({"text": "r", "reply": {"parent": {"uri": "p"}, "root": {"uri": "r"}}}), "reply"),
    (_bsky(embed={"record": {"uri": "q"}}), "quote"),
    (_bsky(reason={"$type": "app.bsky.feed.defs#reasonRepost"}), "repost"),
])
def test_bluesky_relation_mapping(item, relation):
    rec = map_bluesky_item(item, CFG, SOURCE)
    assert rec.metadata["relation_type"] == relation
    assert rec.metadata["actor_id"] == "did:plc:a"
    rec.to_source_item()


def test_buzzsprout_creator_transcript_provenance():
    page = '<main><button>Copy Transcript</button><div>Alex: ' + ('Public transcript sentence. ' * 8) + '</div></main>'
    entry = SimpleNamespace(id="episode-1", link="https://example.test/e/1", title="Episode", author="Hosts",
                            enclosures=[{"href": "https://cdn.test/audio.mp3"}], itunes_duration="42:00")
    rec = map_buzzsprout_entry(entry, page, CFG, {"key": "pod", "feed_url": "https://feeds.test/rss"})
    assert rec.metadata["text_origin"] == "creator_transcript"
    assert rec.metadata["transcription_method"] == "publisher_supplied"
    assert rec.metadata["verification_state"] == "creator_published"
    assert rec.metadata["multimodal_enabled"] is False
    assert rec.metadata["audio_url"].endswith(".mp3")


def test_missing_transcript_fails_instead_of_silent_asr():
    assert extract_buzzsprout_transcript("<html>No transcript</html>") is None
    entry = SimpleNamespace(id="1", link="https://example.test/e/1")
    with pytest.raises(ValueError): map_buzzsprout_entry(entry, "<html></html>", CFG, {"key": "p", "feed_url": "f"})


def test_checkpoint_raw_capture_and_dedup(tmp_path: Path):
    store = CollectionStore(tmp_path)
    ref = store.save_raw("mastodon", "native-1", {"id": "native-1"})
    assert json.loads((tmp_path / ref).read_text(encoding="utf-8"))["id"] == "native-1"
    store.set_checkpoint("source", "cursor")
    assert CollectionStore(tmp_path).get_checkpoint("source") == "cursor"
    rec = map_mastodon_status({"id": "1", "content": "x", "account": {}}, CFG, SOURCE)
    rec.raw_payload_ref = ref
    first = store.save(rec)
    assert first is not None and first[1].raw_payload_ref == ref and first[1].dataset_id == "ai26"
    assert store.save(rec) is None


def test_profile_switches_and_public_hygiene():
    profile = load_profile()
    enabled = {s["key"] for s in profile["sources"] if s["enabled"]}
    assert {"dair-publications", "mastodon-alex", "bluesky-alex", "maiht3k-podcast"} <= enabled
    assert not next(s for s in profile["sources"] if s["key"] == "linkedin-dair")["enabled"]
    serialized = yaml.safe_dump(profile).lower()
    assert not any(secret in serialized for secret in ("api_key", "password", "bearer ", "c:\\users", "/scratch/"))


def test_empty_or_malformed_account_lists(tmp_path: Path):
    bad = tmp_path / "bad.yaml"; bad.write_text("sources: {}\n", encoding="utf-8")
    with pytest.raises(ValueError): load_profile(bad)