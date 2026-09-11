"""DAIR public-source collectors; acquisition metadata is not ideology coding.

This module is the canonical source-group collector for the reviewed public
DAIR/AI26 profile.  It collects public source material only and immediately
maps it into the repository's canonical CollectRecord -> SourceItem /
IngestionRecord spine.  No discourse, ideology, sentiment or actor-position
classification happens here.
"""
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
from typing import Any

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
    """Small public HTTP client with rate limiting and Retry-After support."""

    def __init__(self, delay: float = 1.0, timeout: int = 30) -> None:
        self.delay = delay
        self.timeout = timeout
        self._last = 0.0

    def get(self, url: str, *, json_data: bool = True) -> HttpResponse:
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "LaclauGPT-DAIR/1.1",
                "Accept": "application/json" if json_data else "*/*",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                self._last = time.monotonic()
                return HttpResponse(
                    json.loads(body) if json_data else body,
                    response.geturl() or url,
                    response.status,
                    dict(response.headers.items()),
                )
        except urllib.error.HTTPError as exc:
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if exc.code in (429, 503) and retry_after:
                try:
                    delay = min(float(retry_after), 60.0)
                except ValueError:
                    delay = 5.0
                time.sleep(delay)
                return self.get(url, json_data=json_data)
            raise


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def discover_dair_links(index_url: str, page: str) -> list[str]:
    """Conservative same-site publication/blog link discovery."""
    parser = _Links()
    parser.feed(page)
    base = urllib.parse.urlsplit(index_url)
    section = base.path.rstrip("/") + "/"
    found: set[str] = set()
    for href in parser.links:
        url = normalize_url(urllib.parse.urljoin(index_url, href))
        if not url:
            continue
        parts = urllib.parse.urlsplit(url)
        if (
            parts.netloc == base.netloc
            and parts.path.startswith(section)
            and parts.path != section
        ):
            found.add(url)
    return sorted(found)


def _configuration_fingerprint(cfg: dict) -> str:
    digest = hashlib.sha256(
        yaml.safe_dump(cfg, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return "sha256:" + digest


def _common(record: CollectRecord, cfg: dict, source: dict) -> CollectRecord:
    record.dataset_id = cfg["project"]
    record.metadata.update(
        {
            "configuration_fingerprint": _configuration_fingerprint(cfg),
            "project": cfg["project"],
            "arena": cfg["arena"],
            "source_group": cfg["source_group"],
            "source_key": source["key"],
            "selection_rationale": cfg["selection_rationale"],
            "classification_state": "unjudged",
            "multimodal_enabled": False,
        }
    )
    return record


def _html_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    return value.strip()


# ---------------------------------------------------------------------------
# Mastodon


def map_mastodon_status(status: dict, cfg: dict, source: dict) -> CollectRecord:
    """Map one public Mastodon status while preserving boost/reply relations."""
    boost = status.get("reblog") if isinstance(status.get("reblog"), dict) else None
    content_item = boost or status
    outer_account = status.get("account") or {}
    content_account = content_item.get("account") or {}

    if boost:
        relation = "boost"
    elif status.get("in_reply_to_id"):
        relation = "reply"
    else:
        relation = "original"

    stable_native_id = str(status.get("uri") or status.get("id") or "")
    if not stable_native_id:
        raise ValueError("Mastodon status lacks id/uri")

    metadata = {
        "actor_id": outer_account.get("url") or outer_account.get("uri"),
        "account": outer_account.get("acct") or outer_account.get("username"),
        "relation_type": relation,
        "original_html": content_item.get("content") or "",
        "content_warning": content_item.get("spoiler_text") or "",
        "parent_id": status.get("in_reply_to_id"),
        "parent_account_id": status.get("in_reply_to_account_id"),
        "conversation_id": status.get("conversation_id"),
        "tags": content_item.get("tags", []),
        "mentions": content_item.get("mentions", []),
        "media": content_item.get("media_attachments", []),
        "engagement": {
            key: status.get(key)
            for key in ("replies_count", "reblogs_count", "favourites_count")
        },
        "edited_at": status.get("edited_at"),
        "edit_history_available": bool(status.get("edited_at")),
        "source_modality": "text",
        "text_origin": "platform_text",
        "verification_state": "source_native",
    }
    if boost:
        metadata.update(
            {
                "boosted_status_id": boost.get("id"),
                "boosted_status_uri": boost.get("uri"),
                "boosted_actor_id": content_account.get("url")
                or content_account.get("uri"),
                "boosted_account": content_account.get("acct")
                or content_account.get("username"),
            }
        )

    return _common(
        CollectRecord(
            source_type="social",
            platform="mastodon",
            native_id=stable_native_id,
            url=status.get("url") or status.get("uri"),
            author=outer_account.get("acct") or outer_account.get("username"),
            published_at=status.get("created_at"),
            language=content_item.get("language"),
            text=_html_text(content_item.get("content")) or None,
            collector="dair-mastodon",
            imported_from=status.get("uri") or source.get("account"),
            metadata=metadata,
        ),
        cfg,
        source,
    )


def mastodon_pages(
    source: dict,
    client: PublicHttpClient,
    checkpoint: str | None = None,
):
    """Yield newest public statuses, using checkpoint as ``since_id``.

    Pagination inside a run uses ``max_id``; the persistent checkpoint is the
    newest status id from the first page.  This avoids resuming into older
    history and missing newly published statuses on the next run.
    """
    instance, handle = source["account"].split("/@", 1)
    lookup_url = (
        f"https://{instance}/api/v1/accounts/lookup?acct="
        + urllib.parse.quote(handle)
    )
    lookup = client.get(lookup_url).data
    if not isinstance(lookup, dict) or not lookup.get("id"):
        raise ValueError(f"Mastodon account could not be resolved: {source['account']}")

    max_pages = max(1, int(source.get("max_pages", 5)))
    max_id: str | None = None
    newest_id: str | None = None
    for _ in range(max_pages):
        params: dict[str, str | int] = {"limit": 40}
        if checkpoint:
            params["since_id"] = checkpoint
        if max_id:
            params["max_id"] = max_id
        url = (
            f"https://{instance}/api/v1/accounts/{lookup['id']}/statuses?"
            + urllib.parse.urlencode(params)
        )
        response = client.get(url).data
        if not isinstance(response, list):
            raise ValueError("malformed Mastodon statuses response")
        if not response:
            break
        if newest_id is None:
            newest_id = str(response[0].get("id") or "") or None
        yield response, newest_id
        if len(response) < 40:
            break
        max_id = str(response[-1].get("id") or "") or None
        if not max_id:
            break


# ---------------------------------------------------------------------------
# Bluesky


def map_bluesky_item(item: dict, cfg: dict, source: dict) -> CollectRecord:
    reason = item.get("reason") or {}
    post = item["post"]
    record = post.get("record") or {}
    reply = record.get("reply") or {}
    embed = record.get("embed") or post.get("embed") or {}
    embed_type = str(embed.get("$type") or "")

    if str(reason.get("$type") or "").endswith("reasonRepost"):
        relation = "repost"
    elif reply:
        relation = "reply"
    elif "record" in embed_type or "record" in embed:
        relation = "quote"
    else:
        relation = "original"

    author = post.get("author") or {}
    uri = str(post.get("uri") or "")
    if not uri:
        raise ValueError("Bluesky post lacks AT URI")
    handle = author.get("handle")
    post_key = uri.rsplit("/", 1)[-1]
    profile_ref = handle or author.get("did")

    return _common(
        CollectRecord(
            source_type="social",
            platform="bluesky",
            native_id=uri,
            url=f"https://bsky.app/profile/{profile_ref}/post/{post_key}"
            if profile_ref
            else None,
            author=handle,
            published_at=record.get("createdAt") or post.get("indexedAt"),
            language=(record.get("langs") or [None])[0],
            text=record.get("text"),
            collector="dair-bluesky",
            imported_from=uri,
            metadata={
                "actor_id": author.get("did"),
                "handle": handle,
                "cid": post.get("cid"),
                "at_uri": uri,
                "relation_type": relation,
                "parent_id": (reply.get("parent") or {}).get("uri"),
                "root_id": (reply.get("root") or {}).get("uri"),
                "facets": record.get("facets", []),
                "embed": embed,
                "engagement": {
                    key: post.get(key)
                    for key in ("replyCount", "repostCount", "likeCount", "quoteCount")
                },
                "source_modality": "text",
                "text_origin": "platform_text",
                "verification_state": "source_native",
            },
        ),
        cfg,
        source,
    )


def bluesky_pages(
    source: dict,
    client: PublicHttpClient,
    checkpoint: str | None = None,
):
    """Yield newest author-feed records until the previous top AT URI appears."""
    base = "https://public.api.bsky.app/xrpc/"
    handle = source["handle"]
    resolved = client.get(
        base
        + "com.atproto.identity.resolveHandle?handle="
        + urllib.parse.quote(handle)
    ).data
    did = resolved.get("did") if isinstance(resolved, dict) else None
    if not did:
        raise ValueError(f"Bluesky handle could not be resolved: {handle}")
    if source.get("did") and source["did"] != did:
        raise ValueError(f"Bluesky DID changed for {handle}")

    cursor: str | None = None
    newest_uri: str | None = None
    max_pages = max(1, int(source.get("max_pages", 5)))
    for _ in range(max_pages):
        params: dict[str, str | int] = {"limit": 100, "actor": did}
        if cursor:
            params["cursor"] = cursor
        data = client.get(
            base + "app.bsky.feed.getAuthorFeed?" + urllib.parse.urlencode(params)
        ).data
        feed = data.get("feed") if isinstance(data, dict) else None
        if feed is None:
            raise ValueError("malformed Bluesky author feed response")
        if not feed:
            break

        fresh: list[dict] = []
        hit_checkpoint = False
        for item in feed:
            uri = str((item.get("post") or {}).get("uri") or "")
            if newest_uri is None and uri:
                newest_uri = uri
            if checkpoint and uri == checkpoint:
                hit_checkpoint = True
                break
            fresh.append(item)
        if fresh:
            yield fresh, newest_uri
        if hit_checkpoint:
            break
        cursor = data.get("cursor")
        if not cursor:
            break


# ---------------------------------------------------------------------------
# PeerTube


def _caption_rank(caption: dict, preferred_languages: tuple[str, ...]) -> tuple[int, int, str]:
    language = (caption.get("language") or {}).get("id") or ""
    try:
        language_rank = preferred_languages.index(language)
    except ValueError:
        language_rank = len(preferred_languages) + 1
    generated_rank = 1 if caption.get("automaticallyGenerated") else 0
    return generated_rank, language_rank, language


def select_peertube_caption(
    payload: dict | list,
    preferred_languages: tuple[str, ...] = ("en",),
) -> dict | None:
    captions = payload.get("data", []) if isinstance(payload, dict) else payload
    usable = [caption for caption in captions if isinstance(caption, dict)]
    if not usable:
        return None
    return sorted(usable, key=lambda caption: _caption_rank(caption, preferred_languages))[0]


def _vtt_to_text(vtt: str) -> str:
    lines: list[str] = []
    for raw in vtt.replace("\ufeff", "").splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT" or "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if line.startswith(("NOTE", "STYLE", "REGION")):
            continue
        line = re.sub(r"<v\s+[^>]+>", "", line)
        line = _html_text(line)
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return "\n".join(lines).strip()


def discover_peertube_channels(source: dict, client: PublicHttpClient) -> list[dict]:
    """Discover channels owned by the configured DAIR PeerTube account."""
    instance = source["instance"].rstrip("/")
    account = urllib.parse.quote(source["account"], safe="@")
    url = f"{instance}/api/v1/accounts/{account}/video-channels?count=100"
    payload = client.get(url).data
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("malformed PeerTube account channel response")
    return [item for item in payload["data"] if isinstance(item, dict)]


def _peertube_caption(
    instance: str,
    video_id: str,
    source: dict,
    client: PublicHttpClient,
) -> tuple[dict | None, str | None]:
    captions = client.get(f"{instance}/api/v1/videos/{video_id}/captions").data
    caption = select_peertube_caption(
        captions,
        tuple(source.get("preferred_caption_languages") or ["en"]),
    )
    if not caption:
        return None, None
    caption_url = caption.get("fileUrl") or caption.get("captionPath")
    if not caption_url:
        return caption, None
    caption_url = urllib.parse.urljoin(instance + "/", caption_url)
    text = client.get(caption_url, json_data=False).data
    return caption, _vtt_to_text(text)


def map_peertube_video(
    video: dict,
    cfg: dict,
    source: dict,
    *,
    caption: dict | None = None,
    transcript: str | None = None,
) -> CollectRecord:
    """Map a DAIR-owned PeerTube video using transcript-first provenance."""
    instance = source["instance"].rstrip("/")
    native_id = str(video.get("uuid") or video.get("shortUUID") or video.get("id") or "")
    if not native_id:
        raise ValueError("PeerTube video lacks stable id")
    channel = video.get("channel") or {}
    account = video.get("account") or {}
    language = video.get("language")
    if isinstance(language, dict):
        language = language.get("id")

    text = transcript or video.get("description") or None
    if transcript and caption and caption.get("automaticallyGenerated"):
        text_origin = "platform_auto_caption"
        verification_state = "machine_generated_unverified"
        transcription_method = "peertube_auto_caption"
    elif transcript:
        text_origin = "creator_caption"
        verification_state = "creator_published"
        transcription_method = "publisher_supplied"
    else:
        text_origin = "video_description"
        verification_state = "source_native"
        transcription_method = None

    return _common(
        CollectRecord(
            source_type="video",
            platform="peertube",
            native_id=native_id,
            url=video.get("url") or f"{instance}/w/{native_id}",
            title=video.get("name"),
            author=channel.get("displayName")
            or channel.get("name")
            or account.get("displayName")
            or account.get("name"),
            published_at=video.get("publishedAt") or video.get("createdAt"),
            language=language,
            text=text,
            collector="dair-peertube",
            imported_from=instance,
            metadata={
                "source_modality": "video",
                "text_origin": text_origin,
                "transcription_method": transcription_method,
                "verification_state": verification_state,
                "transcript_available": bool(transcript),
                "asr_required": not bool(transcript),
                "caption": caption,
                "channel": {
                    "name": channel.get("name"),
                    "display_name": channel.get("displayName"),
                    "url": channel.get("url"),
                },
                "account": {
                    "name": account.get("name"),
                    "display_name": account.get("displayName"),
                    "url": account.get("url"),
                },
                "duration_seconds": video.get("duration"),
                "tags": video.get("tags") or [],
                "licence": video.get("licence"),
                "engagement": {
                    key: video.get(key) for key in ("views", "likes", "dislikes")
                },
            },
        ),
        cfg,
        source,
    )


def peertube_records(
    source: dict,
    client: PublicHttpClient,
    checkpoint: str | None = None,
):
    """Collect videos only from channels owned by the configured DAIR account.

    The persistent checkpoint is the newest ``publishedAt`` timestamp seen.  On
    later runs, each newest-first channel feed stops once it reaches that time.
    Existing captions are preferred; no audio ASR or multimodal processing is
    initiated by this source-acquisition function.
    """
    instance = source["instance"].rstrip("/")
    channels = discover_peertube_channels(source, client)
    if not channels:
        raise RuntimeError("DAIR PeerTube account returned zero channels")

    newest_published: str | None = None
    max_pages = max(1, int(source.get("max_pages_per_channel", 2)))
    count = min(max(1, int(source.get("page_size", 100))), 100)

    for channel in channels:
        handle = channel.get("name")
        if not handle:
            continue
        start = 0
        for _ in range(max_pages):
            params = {
                "start": start,
                "count": count,
                "sort": "-publishedAt",
            }
            url = (
                f"{instance}/api/v1/video-channels/"
                f"{urllib.parse.quote(handle, safe='@')}/videos?"
                + urllib.parse.urlencode(params)
            )
            payload = client.get(url).data
            videos = payload.get("data") if isinstance(payload, dict) else None
            if videos is None:
                raise ValueError("malformed PeerTube channel video response")
            if not videos:
                break

            stop_channel = False
            for summary in videos:
                published = summary.get("publishedAt") or summary.get("createdAt") or ""
                if checkpoint and published and published <= checkpoint:
                    stop_channel = True
                    break
                if published and (newest_published is None or published > newest_published):
                    newest_published = published
                video_id = str(
                    summary.get("uuid") or summary.get("shortUUID") or summary.get("id") or ""
                )
                if not video_id:
                    continue
                details = client.get(f"{instance}/api/v1/videos/{video_id}").data
                if not isinstance(details, dict):
                    raise ValueError("malformed PeerTube video response")
                caption, transcript = _peertube_caption(
                    instance, video_id, source, client
                )
                yield {
                    "video": details,
                    "caption": caption,
                    "transcript": transcript,
                    "checkpoint": newest_published,
                    "channel": channel,
                }
            if stop_channel or len(videos) < count:
                break
            start += count


# ---------------------------------------------------------------------------
# Publisher transcript source


def extract_buzzsprout_transcript(page: str) -> str | None:
    """Extract publisher transcript from Buzzsprout static episode HTML."""
    patterns = [
        r'<div[^>]+class="[^"]*episode-transcript[^"]*"[^>]*>(.*?)</div>\s*</div>',
        r"Copy Transcript\s*</[^>]+>\s*(.*?)(?:</main>|</article>|<footer)",
    ]
    for pattern in patterns:
        match = re.search(pattern, page, re.I | re.S)
        if match:
            text = html.unescape(re.sub(r"<[^>]+>", "\n", match.group(1)))
            text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
            if len(text) > 100:
                return text
    return None


def map_buzzsprout_entry(entry: Any, page: str, cfg: dict, source: dict) -> CollectRecord:
    transcript = extract_buzzsprout_transcript(page)
    if not transcript:
        raise ValueError(f"publisher transcript missing for {entry.link}")
    native_id = getattr(entry, "id", None) or entry.link
    return _common(
        CollectRecord(
            source_type="podcast",
            platform="buzzsprout",
            native_id=native_id,
            url=entry.link,
            title=getattr(entry, "title", None),
            author=getattr(entry, "author", None),
            text=transcript,
            collector="dair-buzzsprout",
            imported_from=source["feed_url"],
            metadata={
                "source_modality": "audio",
                "text_origin": "creator_transcript",
                "transcription_method": "publisher_supplied",
                "verification_state": "creator_published",
                "audio_url": next(
                    (
                        enclosure.get("href")
                        for enclosure in getattr(entry, "enclosures", [])
                        if enclosure.get("href")
                    ),
                    None,
                ),
                "duration": getattr(entry, "itunes_duration", None),
                "transcript_page": entry.link,
            },
        ),
        cfg,
        source,
    )


# ---------------------------------------------------------------------------
# Profile orchestration


def load_profile(path: str | Path = DEFAULT_CONFIG) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    sources = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(sources, list) or any(
        not isinstance(source, dict) or not source.get("key") for source in sources
    ):
        raise ValueError("DAIR profile requires a list of keyed sources")
    keys = [source["key"] for source in sources]
    if len(keys) != len(set(keys)):
        raise ValueError("DAIR profile source keys must be unique")
    return data


def collect_profile(
    config_path: str | Path = DEFAULT_CONFIG,
    *,
    selected: list[str] | None = None,
    root: Path | None = None,
    dry_run: bool = False,
    client: PublicHttpClient | None = None,
) -> dict[str, int]:
    """Collect enabled DAIR sources independently and fail on unexpected zeroes."""
    import feedparser

    cfg = load_profile(config_path)
    store = CollectionStore(root)
    client = client or PublicHttpClient()
    wanted = set(selected or [])
    sources = [
        source for source in cfg["sources"] if not wanted or source["key"] in wanted
    ]
    known = {source["key"] for source in sources}
    if wanted - known:
        raise ValueError("unknown source selection")

    enabled = [source for source in sources if source.get("enabled", False)]
    disabled = len(sources) - len(enabled)
    if dry_run:
        return {"planned": len(enabled), "disabled": disabled, "saved": 0, "duplicates": 0}

    counts = {"saved": 0, "duplicates": 0, "disabled": disabled}
    for source in enabled:
        records: list[CollectRecord] = []
        key = source["key"]
        kind = source["kind"]

        if kind == "page":
            response = client.get(source["url"], json_data=False)
            raw_ref = store.save_raw(
                "website", key, {"url": response.url, "html": response.data}
            )
            rec = _common(
                collect_web(
                    response.url,
                    html_text=response.data,
                    http_status=response.status,
                ),
                cfg,
                source,
            )
            rec.raw_payload_ref = raw_ref
            rec.metadata.update(
                {"section": source.get("section"), "retrieval_method": "direct-page"}
            )
            records.append(rec)

        elif kind == "website":
            index_response = client.get(source["index_url"], json_data=False)
            links = discover_dair_links(source["index_url"], index_response.data)
            for url in links:
                response = client.get(url, json_data=False)
                raw_ref = store.save_raw(
                    "website",
                    url,
                    {"url": response.url, "html": response.data},
                )
                rec = _common(
                    collect_web(
                        response.url,
                        html_text=response.data,
                        http_status=response.status,
                    ),
                    cfg,
                    source,
                )
                rec.raw_payload_ref = raw_ref
                rec.metadata.update(
                    {"section": source["section"], "retrieval_method": "html-index"}
                )
                records.append(rec)

        elif kind == "mastodon":
            checkpoint = store.get_checkpoint(key)
            newest: str | None = None
            for payload, page_checkpoint in mastodon_pages(source, client, checkpoint):
                newest = page_checkpoint or newest
                for item in payload:
                    raw_key = str(item.get("uri") or item.get("id") or key)
                    raw_ref = store.save_raw("mastodon", raw_key, item)
                    rec = map_mastodon_status(item, cfg, source)
                    rec.raw_payload_ref = raw_ref
                    records.append(rec)
            if newest:
                store.set_checkpoint(key, newest)

        elif kind == "bluesky":
            checkpoint = store.get_checkpoint(key)
            newest: str | None = None
            for payload, page_checkpoint in bluesky_pages(source, client, checkpoint):
                newest = page_checkpoint or newest
                for item in payload:
                    post = item.get("post") or {}
                    raw_key = str(post.get("uri") or key)
                    raw_ref = store.save_raw("bluesky", raw_key, item)
                    rec = map_bluesky_item(item, cfg, source)
                    rec.raw_payload_ref = raw_ref
                    records.append(rec)
            if newest:
                store.set_checkpoint(key, newest)

        elif kind == "peertube":
            checkpoint = store.get_checkpoint(key)
            newest: str | None = None
            for item in peertube_records(source, client, checkpoint):
                video = item["video"]
                raw_key = str(
                    video.get("uuid") or video.get("shortUUID") or video.get("id") or key
                )
                raw_ref = store.save_raw(
                    "peertube",
                    raw_key,
                    {
                        "video": video,
                        "caption": item["caption"],
                        "transcript": item["transcript"],
                        "channel": item["channel"],
                    },
                )
                rec = map_peertube_video(
                    video,
                    cfg,
                    source,
                    caption=item["caption"],
                    transcript=item["transcript"],
                )
                rec.raw_payload_ref = raw_ref
                records.append(rec)
                newest = item["checkpoint"] or newest
            if newest:
                store.set_checkpoint(key, newest)

        elif kind == "buzzsprout":
            feed = feedparser.parse(source["feed_url"])
            for entry in feed.entries:
                response = client.get(entry.link, json_data=False)
                native_id = getattr(entry, "id", None) or entry.link
                raw_ref = store.save_raw(
                    "buzzsprout",
                    str(native_id),
                    {"url": entry.link, "html": response.data},
                )
                rec = map_buzzsprout_entry(entry, response.data, cfg, source)
                rec.raw_payload_ref = raw_ref
                records.append(rec)

        else:
            raise ValueError(f"unsupported enabled source kind: {kind}")

        if not records:
            # No new records after a valid checkpoint is normal.  A first run
            # returning zero records is suspicious and should fail visibly.
            if store.get_checkpoint(key):
                continue
            raise RuntimeError(f"enabled source returned zero records: {key}")

        saved, duplicates = store.save_many(records)
        counts["saved"] += saved
        counts["duplicates"] += duplicates

    return counts
