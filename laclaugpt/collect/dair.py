"""DAIR public-source collectors; acquisition metadata is not ideology coding."""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

import yaml

from laclaugpt.collect import CollectRecord, CollectionStore, collect_web, normalize_url

DEFAULT_CONFIG = Path("config/sources/dair-critical-ai.yaml")


@dataclass
class HttpResponse:
    data: Any
    url: str
    status: int = 200
    headers: dict[str, str] | None = None


class PublicHttpClient:
    """Small public HTTP client with an explicit delay and Retry-After support."""
    def __init__(self, delay: float = 1.0, timeout: int = 30) -> None:
        self.delay, self.timeout, self._last = delay, timeout, 0.0

    def get(self, url: str, *, json_data: bool = True) -> HttpResponse:
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        request = urllib.request.Request(url, headers={"User-Agent": "LaclauGPT-DAIR/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                self._last = time.monotonic()
                return HttpResponse(json.loads(body) if json_data else body,
                                    response.geturl() or url, response.status,
                                    dict(response.headers.items()))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and exc.headers.get("Retry-After"):
                time.sleep(min(float(exc.headers["Retry-After"]), 60.0))
                return self.get(url, json_data=json_data)
            raise


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.links: list[str] = []
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href: self.links.append(href)


def discover_dair_links(index_url: str, page: str) -> list[str]:
    """Conservative same-site publication/blog link discovery."""
    parser = _Links(); parser.feed(page)
    base = urllib.parse.urlsplit(index_url)
    section = base.path.rstrip("/") + "/"
    found = set()
    for href in parser.links:
        url = normalize_url(urllib.parse.urljoin(index_url, href))
        if not url: continue
        parts = urllib.parse.urlsplit(url)
        if parts.netloc == base.netloc and parts.path.startswith(section) and parts.path != section:
            found.add(url)
    return sorted(found)


def _common(record: CollectRecord, cfg: dict, source: dict) -> CollectRecord:
    record.dataset_id = cfg["project"]
    fingerprint = hashlib.sha256(yaml.safe_dump(cfg, sort_keys=True).encode("utf-8")).hexdigest()
    record.metadata.update({
        "configuration_fingerprint": "sha256:" + fingerprint,
        "project": cfg["project"], "arena": cfg["arena"],
        "source_group": cfg["source_group"], "source_key": source["key"],
        "selection_rationale": cfg["selection_rationale"],
        "classification_state": "unjudged", "multimodal_enabled": False,
    })
    return record


def map_mastodon_status(status: dict, cfg: dict, source: dict) -> CollectRecord:
    boost = status.get("reblog")
    item = boost or status
    relation = "boost" if boost else ("reply" if item.get("in_reply_to_id") else "original")
    account = item.get("account") or {}
    return _common(CollectRecord(
        source_type="social", platform="mastodon", native_id=str(status["id"]),
        url=status.get("url") or status.get("uri"), author=account.get("acct"),
        published_at=status.get("created_at"), language=item.get("language"),
        text=html.unescape(re.sub(r"<[^>]+>", " ", item.get("content", ""))).strip(),
        collector="dair-mastodon", imported_from=status.get("uri"),
        metadata={
            "actor_id": account.get("url") or account.get("uri"), "account": account.get("acct"),
            "relation_type": relation, "original_html": item.get("content"),
            "content_warning": item.get("spoiler_text"), "parent_id": item.get("in_reply_to_id"),
            "root_id": item.get("in_reply_to_account_id"), "conversation_id": item.get("conversation_id"),
            "tags": item.get("tags", []), "mentions": item.get("mentions", []),
            "media": item.get("media_attachments", []),
            "engagement": {k: item.get(k) for k in ("replies_count", "reblogs_count", "favourites_count")},
            "edited_at": item.get("edited_at"), "edit_history_available": bool(item.get("edited_at")),
        }), cfg, source)


def mastodon_pages(source: dict, client: PublicHttpClient, checkpoint: str | None = None):
    instance, handle = source["account"].split("/@", 1)
    lookup = client.get(f"https://{instance}/api/v1/accounts/lookup?acct={urllib.parse.quote(handle)}").data
    if not lookup.get("id"): raise ValueError(f"Mastodon account could not be resolved: {source['account']}")
    max_id = checkpoint
    while True:
        url = f"https://{instance}/api/v1/accounts/{lookup['id']}/statuses?limit=40"
        if max_id: url += "&max_id=" + urllib.parse.quote(max_id)
        response = client.get(url).data
        if not isinstance(response, list): raise ValueError("malformed Mastodon statuses response")
        if not response: break
        yield response, str(response[-1]["id"])
        if len(response) < 40: break
        max_id = str(response[-1]["id"])


def map_bluesky_item(item: dict, cfg: dict, source: dict) -> CollectRecord:
    reason = item.get("reason") or {}
    post = item["post"]; record = post.get("record") or {}
    reply = record.get("reply") or {}; embed = record.get("embed") or post.get("embed") or {}
    relation = "repost" if reason.get("$type", "").endswith("reasonRepost") else (
        "reply" if reply else ("quote" if "record" in embed else "original"))
    author = post.get("author") or {}
    return _common(CollectRecord(
        source_type="social", platform="bluesky", native_id=post["uri"],
        url=f"https://bsky.app/profile/{author.get('did')}/post/{post['uri'].rsplit('/',1)[-1]}",
        author=author.get("handle"), published_at=record.get("createdAt"),
        language=(record.get("langs") or [None])[0], text=record.get("text"),
        collector="dair-bluesky", imported_from=post["uri"],
        metadata={"actor_id": author.get("did"), "handle": author.get("handle"),
                  "cid": post.get("cid"), "at_uri": post["uri"], "relation_type": relation,
                  "parent_id": (reply.get("parent") or {}).get("uri"),
                  "root_id": (reply.get("root") or {}).get("uri"),
                  "facets": record.get("facets", []), "embed": embed,
                  "engagement": {k: post.get(k) for k in ("replyCount", "repostCount", "likeCount", "quoteCount")}},
    ), cfg, source)


def bluesky_pages(source: dict, client: PublicHttpClient, checkpoint: str | None = None):
    base = "https://public.api.bsky.app/xrpc/"
    handle = source["handle"]
    resolved = client.get(base + "com.atproto.identity.resolveHandle?handle=" + urllib.parse.quote(handle)).data
    did = resolved.get("did")
    if not did: raise ValueError(f"Bluesky handle could not be resolved: {handle}")
    if source.get("did") and source["did"] != did: raise ValueError(f"Bluesky DID changed for {handle}")
    cursor = checkpoint
    while True:
        url = base + "app.bsky.feed.getAuthorFeed?limit=100&actor=" + urllib.parse.quote(did)
        if cursor: url += "&cursor=" + urllib.parse.quote(cursor)
        data = client.get(url).data
        feed = data.get("feed") if isinstance(data, dict) else None
        if feed is None: raise ValueError("malformed Bluesky author feed response")
        if not feed: break
        yield feed, data.get("cursor")
        cursor = data.get("cursor")
        if not cursor: break


def extract_buzzsprout_transcript(page: str) -> str | None:
    """Extract publisher transcript from Buzzsprout static episode HTML."""
    patterns = [
        r'<div[^>]+class="[^"]*episode-transcript[^"]*"[^>]*>(.*?)</div>\s*</div>',
        r'Copy Transcript\s*</[^>]+>\s*(.*?)(?:</main>|</article>|<footer)',
    ]
    for pattern in patterns:
        match = re.search(pattern, page, re.I | re.S)
        if match:
            text = html.unescape(re.sub(r"<[^>]+>", "\n", match.group(1)))
            text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
            if len(text) > 100: return text
    return None


def map_buzzsprout_entry(entry: Any, page: str, cfg: dict, source: dict) -> CollectRecord:
    transcript = extract_buzzsprout_transcript(page)
    if not transcript: raise ValueError(f"publisher transcript missing for {entry.link}")
    native_id = getattr(entry, "id", None) or entry.link
    return _common(CollectRecord(
        source_type="podcast", platform="buzzsprout", native_id=native_id,
        url=entry.link, title=getattr(entry, "title", None),
        author=getattr(entry, "author", None), text=transcript,
        collector="dair-buzzsprout", imported_from=source["feed_url"],
        metadata={"source_modality": "audio", "text_origin": "creator_transcript",
                  "transcription_method": "publisher_supplied", "verification_state": "creator_published",
                  "audio_url": next((x.get("href") for x in getattr(entry, "enclosures", []) if x.get("href")), None),
                  "duration": getattr(entry, "itunes_duration", None), "transcript_page": entry.link},
    ), cfg, source)


def load_profile(path: str | Path = DEFAULT_CONFIG) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    sources = data.get("sources")
    if not isinstance(sources, list) or any(not isinstance(s, dict) or not s.get("key") for s in sources):
        raise ValueError("DAIR profile requires a list of keyed sources")
    return data


def collect_profile(config_path: str | Path = DEFAULT_CONFIG, *, selected: list[str] | None = None,
                    root: Path | None = None, dry_run: bool = False,
                    client: PublicHttpClient | None = None) -> dict[str, int]:
    """Collect enabled DAIR sources independently; fail on unexpected zero results."""
    import feedparser
    cfg = load_profile(config_path); store = CollectionStore(root); client = client or PublicHttpClient()
    counts = {"saved": 0, "duplicates": 0, "disabled": 0}; wanted = set(selected or [])
    sources = [s for s in cfg["sources"] if not wanted or s["key"] in wanted]
    if wanted - {s["key"] for s in sources}: raise ValueError("unknown source selection")
    for source in sources:
        if not source.get("enabled", False): counts["disabled"] += 1; continue
        records: list[CollectRecord] = []; key = source["key"]
        if source["kind"] == "website":
            page = client.get(source["index_url"], json_data=False).data
            links = discover_dair_links(source["index_url"], page)
            for url in links:
                response = client.get(url, json_data=False)
                rec = _common(collect_web(response.url, html_text=response.data, http_status=response.status), cfg, source)
                rec.metadata.update({"section": source["section"], "retrieval_method": "html-index"})
                if not dry_run:
                    rec.raw_payload_ref = store.save_raw("website", rec.native_id or key,
                                                         {"url": response.url, "html": response.data})
                records.append(rec)
        elif source["kind"] == "mastodon":
            cp = store.get_checkpoint(key)
            for payload, cursor in mastodon_pages(source, client, cp):
                for item in payload:
                    rec = map_mastodon_status(item, cfg, source)
                    if not dry_run: rec.raw_payload_ref = store.save_raw("mastodon", rec.native_id or key, item)
                    records.append(rec)
                if not dry_run: store.set_checkpoint(key, cursor)
        elif source["kind"] == "bluesky":
            cp = store.get_checkpoint(key)
            for payload, cursor in bluesky_pages(source, client, cp):
                for item in payload:
                    rec = map_bluesky_item(item, cfg, source)
                    if not dry_run: rec.raw_payload_ref = store.save_raw("bluesky", rec.native_id or key, item)
                    records.append(rec)
                if not dry_run: store.set_checkpoint(key, cursor)
        elif source["kind"] == "buzzsprout":
            feed = feedparser.parse(source["feed_url"])
            for entry in feed.entries:
                response = client.get(entry.link, json_data=False)
                rec = map_buzzsprout_entry(entry, response.data, cfg, source)
                if not dry_run: rec.raw_payload_ref = store.save_raw("buzzsprout", rec.native_id or key, {"url": entry.link, "html": response.data})
                records.append(rec)
        else:
            raise ValueError(f"unsupported enabled source kind: {source['kind']}")
        if not records: raise RuntimeError(f"enabled source returned zero records: {key}")
        if dry_run: counts["saved"] += len(records)
        else:
            saved, duplicates = store.save_many(records); counts["saved"] += saved; counts["duplicates"] += duplicates
    return counts