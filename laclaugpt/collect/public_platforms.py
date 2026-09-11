"""Public API collectors for research sources with stable, open read paths.

These adapters deliberately stop at source acquisition.  They do not assign
ideology, discourse roles, sentiment or other interpretive labels.  All output
is normalised to :class:`CollectRecord` and therefore enters the same canonical
SourceItem/IngestionRecord spine as RSS, web and manual sources.

Only public, unauthenticated endpoints are used here:

* Mastodon account lookup + public statuses
* Bluesky public AppView handle resolution + author feed
* PeerTube public channel/video/caption endpoints

Private posts, followers, DMs, chats and credentials are out of scope.
"""
from __future__ import annotations

import html
import json
import re
from collections.abc import Callable, Iterable
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

from laclaugpt.collect import CollectRecord

USER_AGENT = "LaclauGPT-collect/1.0 (+public-research-source-adapter)"
JsonGetter = Callable[[str], object]
TextGetter = Callable[[str], str]


def _json_get(url: str) -> object:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _text_get(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _plain_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def _clean_instance(value: str) -> str:
    value = value.strip().rstrip("/")
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    parts = urlsplit(value)
    if not parts.netloc:
        raise ValueError(f"invalid instance URL: {value!r}")
    return f"{parts.scheme}://{parts.netloc}"


# ---------------------------------------------------------------------------
# Mastodon


def parse_mastodon_account_ref(account_ref: str) -> tuple[str, str]:
    """Return ``(instance_base_url, local_handle)`` from common account forms.

    Accepted examples:
    ``https://example.social/@alice``, ``example.social/@alice`` and
    ``@alice@example.social``.
    """
    value = account_ref.strip()
    if value.startswith(("http://", "https://")):
        parts = urlsplit(value)
        handle = next((p[1:] for p in parts.path.split("/") if p.startswith("@")), "")
        if not handle:
            raise ValueError(f"Mastodon account URL lacks @handle: {account_ref!r}")
        return f"{parts.scheme}://{parts.netloc}", handle

    if "/@" in value:
        instance, handle = value.split("/@", 1)
        return _clean_instance(instance), handle.strip("/")

    if value.startswith("@") and value.count("@") >= 2:
        handle, instance = value[1:].split("@", 1)
        return _clean_instance(instance), handle

    raise ValueError(
        "Mastodon account must be instance/@handle, a profile URL, or @handle@instance"
    )


def mastodon_status_to_record(status: dict, *, account_ref: str) -> CollectRecord:
    """Map one Mastodon Status payload to the canonical collection edge."""
    reblog = status.get("reblog") if isinstance(status.get("reblog"), dict) else None
    content_status = reblog or status
    account = status.get("account") or {}

    if reblog:
        relation_type = "boost"
    elif status.get("in_reply_to_id"):
        relation_type = "reply"
    else:
        relation_type = "original"

    tags = [tag.get("name") for tag in content_status.get("tags", []) if tag.get("name")]
    mentions = [
        mention.get("acct") or mention.get("username")
        for mention in content_status.get("mentions", [])
        if mention.get("acct") or mention.get("username")
    ]
    media = []
    for item in content_status.get("media_attachments", []) or []:
        media.append({
            "id": str(item.get("id") or ""),
            "type": item.get("type"),
            "url": item.get("url") or item.get("remote_url"),
            "description": item.get("description"),
        })

    return CollectRecord(
        source_type="mastodon",
        native_id=str(status.get("id") or ""),
        url=status.get("url") or status.get("uri"),
        author=account.get("acct") or account.get("username"),
        published_at=status.get("created_at"),
        text=_plain_html(content_status.get("content")) or None,
        language=content_status.get("language"),
        platform="mastodon",
        metadata={
            "account_ref": account_ref,
            "relation_type": relation_type,
            "content_html": content_status.get("content") or "",
            "content_warning": content_status.get("spoiler_text") or "",
            "hashtags": tags,
            "mentions": mentions,
            "media": media,
            "reply_to_native_id": status.get("in_reply_to_id"),
            "reply_to_account_id": status.get("in_reply_to_account_id"),
            "boosted_native_id": str(reblog.get("id")) if reblog else None,
            "edited_at": status.get("edited_at"),
            "engagement": {
                "replies": status.get("replies_count"),
                "boosts": status.get("reblogs_count"),
                "favourites": status.get("favourites_count"),
            },
            "source_modality": "text",
            "text_origin": "platform_text",
            "verification_state": "source_native",
        },
        collector="mastodon-public-api",
        imported_from=account_ref,
    )


def collect_mastodon_account(
    account_ref: str,
    *,
    since_id: str | None = None,
    max_pages: int = 1,
    json_get: JsonGetter = _json_get,
) -> list[CollectRecord]:
    """Resolve an account and fetch public statuses incrementally.

    ``since_id`` is the resume checkpoint.  Pagination walks older records with
    ``max_id`` and is intentionally bounded by ``max_pages``.
    """
    instance, handle = parse_mastodon_account_ref(account_ref)
    lookup_url = f"{instance}/api/v1/accounts/lookup?{urlencode({'acct': handle})}"
    account = json_get(lookup_url)
    if not isinstance(account, dict) or not account.get("id"):
        raise ValueError(f"Mastodon account could not be resolved: {account_ref}")

    records: list[CollectRecord] = []
    max_id: str | None = None
    for _ in range(max(1, max_pages)):
        params: dict[str, str | int] = {"limit": 40}
        if since_id:
            params["since_id"] = since_id
        if max_id:
            params["max_id"] = max_id
        url = f"{instance}/api/v1/accounts/{account['id']}/statuses?{urlencode(params)}"
        payload = json_get(url)
        if not isinstance(payload, list):
            raise ValueError("Mastodon statuses response is not a list")
        if not payload:
            break
        records.extend(
            mastodon_status_to_record(status, account_ref=account_ref)
            for status in payload
            if isinstance(status, dict) and status.get("id")
        )
        max_id = str(payload[-1].get("id") or "")
        if not max_id or len(payload) < 40:
            break
    return records


# ---------------------------------------------------------------------------
# Bluesky

BSKY_PUBLIC_API = "https://public.api.bsky.app/xrpc"


def bluesky_feed_item_to_record(
    feed_item: dict,
    *,
    requested_handle: str,
    resolved_did: str,
) -> CollectRecord:
    """Map one ``app.bsky.feed.getAuthorFeed`` item to a CollectRecord."""
    post = feed_item.get("post") or {}
    record = post.get("record") or {}
    author = post.get("author") or {}
    reason = feed_item.get("reason") or {}
    reply = record.get("reply") or {}
    embed = post.get("embed") or record.get("embed") or {}
    embed_type = str(embed.get("$type") or "")

    if str(reason.get("$type") or "").endswith("#reasonRepost"):
        relation_type = "repost"
    elif reply:
        relation_type = "reply"
    elif "record" in embed_type:
        relation_type = "quote"
    else:
        relation_type = "original"

    facets = record.get("facets") or []
    hashtags: list[str] = []
    mentions: list[str] = []
    links: list[str] = []
    for facet in facets:
        for feature in facet.get("features") or []:
            feature_type = str(feature.get("$type") or "")
            if feature_type.endswith("#tag") and feature.get("tag"):
                hashtags.append(feature["tag"])
            elif feature_type.endswith("#mention") and feature.get("did"):
                mentions.append(feature["did"])
            elif feature_type.endswith("#link") and feature.get("uri"):
                links.append(feature["uri"])

    uri = str(post.get("uri") or "")
    return CollectRecord(
        source_type="bluesky",
        native_id=uri or None,
        url=f"https://bsky.app/profile/{author.get('handle')}/post/{uri.rsplit('/', 1)[-1]}"
        if uri and author.get("handle") else None,
        author=author.get("handle") or requested_handle,
        published_at=record.get("createdAt") or post.get("indexedAt"),
        text=record.get("text") or None,
        language=(record.get("langs") or [None])[0],
        platform="bluesky",
        metadata={
            "requested_handle": requested_handle,
            "actor_did": author.get("did") or resolved_did,
            "cid": post.get("cid"),
            "at_uri": uri,
            "relation_type": relation_type,
            "parent_uri": (reply.get("parent") or {}).get("uri"),
            "root_uri": (reply.get("root") or {}).get("uri"),
            "hashtags": hashtags,
            "mentions": mentions,
            "links": links,
            "embed_type": embed_type or None,
            "engagement": {
                "replies": post.get("replyCount"),
                "reposts": post.get("repostCount"),
                "likes": post.get("likeCount"),
                "quotes": post.get("quoteCount"),
            },
            "source_modality": "text",
            "text_origin": "platform_text",
            "verification_state": "source_native",
        },
        collector="bluesky-public-appview",
        imported_from=requested_handle,
    )


def collect_bluesky_author(
    handle: str,
    *,
    cursor: str | None = None,
    max_pages: int = 1,
    json_get: JsonGetter = _json_get,
) -> tuple[list[CollectRecord], str | None]:
    """Resolve ``handle`` to a DID and fetch its public author feed."""
    resolve_url = f"{BSKY_PUBLIC_API}/com.atproto.identity.resolveHandle?{urlencode({'handle': handle})}"
    resolved = json_get(resolve_url)
    if not isinstance(resolved, dict) or not resolved.get("did"):
        raise ValueError(f"Bluesky handle could not be resolved: {handle}")
    did = str(resolved["did"])

    records: list[CollectRecord] = []
    next_cursor = cursor
    for _ in range(max(1, max_pages)):
        params: dict[str, str | int] = {"actor": did, "limit": 100}
        if next_cursor:
            params["cursor"] = next_cursor
        url = f"{BSKY_PUBLIC_API}/app.bsky.feed.getAuthorFeed?{urlencode(params)}"
        payload = json_get(url)
        if not isinstance(payload, dict):
            raise ValueError("Bluesky author feed response is not an object")
        feed = payload.get("feed") or []
        records.extend(
            bluesky_feed_item_to_record(item, requested_handle=handle, resolved_did=did)
            for item in feed
            if isinstance(item, dict) and (item.get("post") or {}).get("uri")
        )
        next_cursor = payload.get("cursor")
        if not next_cursor or not feed:
            break
    return records, next_cursor


# ---------------------------------------------------------------------------
# PeerTube


def _caption_rank(caption: dict, preferred_languages: Iterable[str]) -> tuple[int, int, str]:
    language = (caption.get("language") or {}).get("id") or ""
    preferred = list(preferred_languages)
    try:
        language_rank = preferred.index(language)
    except ValueError:
        language_rank = len(preferred) + 1
    generated_rank = 1 if caption.get("automaticallyGenerated") else 0
    return generated_rank, language_rank, language


def select_peertube_caption(
    captions_payload: dict | list,
    *,
    preferred_languages: Iterable[str] = ("en",),
) -> dict | None:
    """Choose creator captions first, then generated captions, then language."""
    if isinstance(captions_payload, dict):
        captions = captions_payload.get("data") or []
    else:
        captions = captions_payload
    captions = [c for c in captions if isinstance(c, dict)]
    if not captions:
        return None
    return sorted(captions, key=lambda c: _caption_rank(c, preferred_languages))[0]


def _vtt_to_text(vtt: str) -> str:
    """Conservative WebVTT-to-text conversion; preserve wording, drop timing."""
    lines: list[str] = []
    for raw in vtt.replace("\ufeff", "").splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT" or "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if line.startswith(("NOTE", "STYLE", "REGION")):
            continue
        line = _plain_html(re.sub(r"<v\s+[^>]+>", "", line))
        if line and (not lines or lines[-1] != line):
            lines.append(line)
    return "\n".join(lines).strip()


def peertube_video_to_record(
    video: dict,
    *,
    instance: str,
    caption: dict | None = None,
    transcript_text: str | None = None,
) -> CollectRecord:
    """Map a PeerTube video and optional selected caption to a CollectRecord."""
    instance = _clean_instance(instance)
    uuid = str(video.get("uuid") or video.get("shortUUID") or video.get("id") or "")
    channel = video.get("channel") or {}
    account = video.get("account") or {}
    language = video.get("language")
    if isinstance(language, dict):
        language = language.get("id")

    text_origin = "video_description"
    verification_state = "source_native"
    text = video.get("description") or None
    if transcript_text:
        text = transcript_text
        if caption and caption.get("automaticallyGenerated"):
            text_origin = "platform_auto_caption"
            verification_state = "machine_generated_unverified"
        else:
            text_origin = "creator_caption"
            verification_state = "source_native"

    return CollectRecord(
        source_type="peertube",
        native_id=uuid or None,
        url=video.get("url") or (f"{instance}/w/{uuid}" if uuid else None),
        title=video.get("name") or None,
        author=channel.get("displayName") or channel.get("name") or account.get("displayName"),
        published_at=video.get("publishedAt") or video.get("createdAt"),
        text=text,
        language=language,
        platform="peertube",
        metadata={
            "instance": instance,
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
            "caption": caption,
            "transcript_available": bool(transcript_text),
            "source_modality": "video",
            "text_origin": text_origin,
            "verification_state": verification_state,
            "multimodal_enabled": False,
            "asr_required": not bool(transcript_text),
            "engagement": {
                "views": video.get("views"),
                "likes": video.get("likes"),
                "dislikes": video.get("dislikes"),
            },
        },
        collector="peertube-public-api",
        imported_from=instance,
    )


def discover_peertube_channels(
    instance: str,
    *,
    start: int = 0,
    count: int = 100,
    json_get: JsonGetter = _json_get,
) -> list[dict]:
    """List public local/visible channels for researcher review."""
    instance = _clean_instance(instance)
    url = f"{instance}/api/v1/video-channels?{urlencode({'start': start, 'count': count})}"
    payload = json_get(url)
    if not isinstance(payload, dict):
        raise ValueError("PeerTube channel response is not an object")
    return [item for item in payload.get("data") or [] if isinstance(item, dict)]


def collect_peertube_channel(
    instance: str,
    channel_handle: str,
    *,
    start: int = 0,
    count: int = 25,
    preferred_languages: Iterable[str] = ("en",),
    include_captions: bool = True,
    json_get: JsonGetter = _json_get,
    text_get: TextGetter = _text_get,
) -> list[CollectRecord]:
    """Collect public video metadata and prefer existing captions as text.

    No audio download or ASR is attempted here.  If no caption is available,
    the record keeps the description and marks ``asr_required`` for a separate
    local transcription workflow.  Multimodal processing stays disabled.
    """
    instance = _clean_instance(instance)
    path_handle = channel_handle.strip().lstrip("@")
    url = (
        f"{instance}/api/v1/video-channels/{path_handle}/videos?"
        f"{urlencode({'start': start, 'count': count, 'sort': '-publishedAt'})}"
    )
    payload = json_get(url)
    if not isinstance(payload, dict):
        raise ValueError("PeerTube channel videos response is not an object")

    records: list[CollectRecord] = []
    for video in payload.get("data") or []:
        if not isinstance(video, dict):
            continue
        uuid = video.get("uuid") or video.get("shortUUID") or video.get("id")
        caption = None
        transcript = None
        if include_captions and uuid:
            captions_url = f"{instance}/api/v1/videos/{uuid}/captions"
            captions_payload = json_get(captions_url)
            caption = select_peertube_caption(
                captions_payload, preferred_languages=preferred_languages)
            if caption:
                caption_url = caption.get("fileUrl") or caption.get("captionPath")
                if caption_url:
                    transcript = _vtt_to_text(text_get(urljoin(instance + "/", caption_url)))
        records.append(
            peertube_video_to_record(
                video, instance=instance, caption=caption, transcript_text=transcript)
        )
    return records
