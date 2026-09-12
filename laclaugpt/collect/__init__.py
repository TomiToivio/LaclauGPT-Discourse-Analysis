# -*- coding: utf-8 -*-
"""Basic data-collection spine: one canonical ingestion, many input channels.

Issue: "Many sources, one canonical corpus." RSS, plain web pages,
Hermes Agent submissions, human-researcher submissions and Telegram
messages differ only at the collection edge — they converge immediately
into the canonical SourceItem / IngestionRecord / Provenance model
(laclaugpt.model) and the normal analysis pipeline.

Design rules (from the collection issue):
- reuse the canonical model; NO RSSDocument/WebDocument/TelegramDocument
  parallel ontology;
- collection source is explicit metadata (collector name + config),
  never an analytical category;
- deduplication via stable native identity (native ID / normalized URL),
  content hash only as fallback;
- config lives in collection-data/ (gitignored) — never commit feeds,
  channel lists or credentials;
- the AI-ideology project is just one consumer of this spine.
"""
from __future__ import annotations
import os

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from laclaugpt.model import IngestionRecord, Provenance, SourceItem

COLLECTOR_VERSION = "laclaugpt-collect-1.0"

# Directory roots (overridable for tests). Runtime data lives outside Git.
COLLECTION_ROOT = Path("collection-data")

# Default UA for RSS fetching. Some hosts (e.g. Reddit) return 429 for
# generic feedparser library user agents; an identifying research UA is
# both honest and compatible. Override with LACLAUGPT_RSS_USER_AGENT.
_DEFAULT_UA = "Mozilla/5.0 (compatible; LaclauGPT-research/1.0; +https://github.com/TomiToivio/LaclauGPT-Discourse-Analysis)"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_url(url: str | None) -> str | None:
    """Canonical URL for dedup: lowercase host, strip fragments/tracking."""
    if not url:
        return None
    parts = urlsplit(url.strip())
    if not parts.scheme:
        parts = urlsplit("https://" + url.strip())
    host = (parts.netloc or "").lower()
    path = parts.path or "/"
    query = parts.query
    if query:
        params = [p for p in sorted(query.split("&"))
                  if not p.startswith(("utm_", "fbclid=", "gclid="))]
        query = "&".join(params)
    return urlunsplit((parts.scheme, host, path, query, "")) or None


def content_hash(text: str | None) -> str | None:
    """Fallback identity when no native ID / URL exists."""
    if not text:
        return None
    return "sha256:" + hashlib.sha256(
        re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()[:32]


@dataclass
class CollectRecord:
    """Edge-neutral collection result; converts to canonical model objects."""
    source_type: str                      # rss|web|hermes|manual|telegram
    native_id: str | None = None
    url: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: str | None = None
    collected_at: str = field(default_factory=utcnow_iso)
    text: str | None = None
    language: str | None = None
    platform: str | None = None
    metadata: dict = field(default_factory=dict)
    # Provenance inputs
    collector: str = "unknown"
    imported_from: str | None = None
    raw_payload_ref: str | None = None
    dataset_id: str | None = None

    @property
    def dedup_id(self) -> str:
        """Stable identity: native id > normalized URL > content hash."""
        if self.native_id:
            return f"{self.source_type}:{self.native_id}"
        norm = normalize_url(self.url)
        if norm:
            return f"{self.source_type}:url:{norm}"
        ch = content_hash(self.text)
        if ch:
            return f"{self.source_type}:hash:{ch}"
        return f"{self.source_type}:ts:{self.collected_at}"

    def to_source_item(self) -> SourceItem:
        return SourceItem(
            source_type=self.source_type,
            platform=self.platform,
            source_url=self.url,
            normalized_source_url=normalize_url(self.url),
            native_id=self.native_id,
            title=self.title,
            author_text=self.author,
            published_at=self.published_at,
            collected_at=self.collected_at,
            language=self.language,
            raw_text=self.text,
            metadata={"dedup_id": self.dedup_id, **self.metadata},
        )

    def to_ingestion(self, source: SourceItem) -> IngestionRecord:
        prov = Provenance(method=f"collect:{self.collector}",
                          imported_from=self.imported_from)
        return IngestionRecord(
            source_id=source.source_id,
            collector=self.collector,
            collector_version=COLLECTOR_VERSION,
            collected_at=self.collected_at,
            raw_metadata=self.metadata,
            raw_payload_ref=self.raw_payload_ref,
            dataset_id=self.dataset_id,
            provenance_id=prov.provenance_id,
        )


class CollectionStore:
    """JSONL append store with dedup ledger.

    Deliberately boring: the same normalized/ JSONL layout the existing
    collector writes, readable by pandas / the legacy CSV adapter path.
    Swap for Mongo/S3 later without touching the collectors.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or COLLECTION_ROOT)
        self.raw_dir = self.root / "raw"
        self.normalized_dir = self.root / "normalized"
        self.normalized_dir.mkdir(parents=True, exist_ok=True)
        self._ledger = self.root / "seen.jsonl"
        self._checkpoints = self.root / "checkpoints.json"
        self._seen: set[str] = set()
        if self._ledger.exists():
            for line in self._ledger.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._seen.add(json.loads(line)["dedup_id"])

    def is_seen(self, dedup_id: str) -> bool:
        return dedup_id in self._seen

    def save_raw(self, source: str, native_id: str, payload: object) -> str:
        """Retain a permitted API/page capture before normalization."""
        digest = hashlib.sha256(native_id.encode("utf-8")).hexdigest()[:24]
        path = self.raw_dir / source / f"{digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path.relative_to(self.root).as_posix()

    def get_checkpoint(self, source: str) -> str | None:
        if not self._checkpoints.exists():
            return None
        return json.loads(self._checkpoints.read_text(encoding="utf-8")).get(source)

    def set_checkpoint(self, source: str, value: str | None) -> None:
        data = {}
        if self._checkpoints.exists():
            data = json.loads(self._checkpoints.read_text(encoding="utf-8"))
        if value is None:
            data.pop(source, None)
        else:
            data[source] = value
        self._checkpoints.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._checkpoints.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._checkpoints)
    def save(self, record: CollectRecord) -> tuple[SourceItem, IngestionRecord] | None:
        """Insert one record; returns None when it is a duplicate."""
        dedup_id = record.dedup_id
        if self.is_seen(dedup_id):
            return None
        source = record.to_source_item()
        ingestion = record.to_ingestion(source)
        out = self.normalized_dir / f"{record.source_type}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": source.model_dump(mode="json"),
            "ingestion": ingestion.model_dump(mode="json"),
        }
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        with open(self._ledger, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"dedup_id": dedup_id,
                                 "first_seen": record.collected_at}) + "\n")
        self._seen.add(dedup_id)
        return source, ingestion

    def save_many(self, records: list[CollectRecord]) -> tuple[int, int]:
        saved = skipped = 0
        for rec in records:
            if self.save(rec) is None:
                skipped += 1
            else:
                saved += 1
        return saved, skipped


# ── source adapters ──────────────────────────────────────────────────

def collect_rss(feed_url: str, *, feed_name: str | None = None,
                fetch_article: bool = False,
                user_agent: str | None = None) -> list[CollectRecord]:
    """RSS/Atom feed entries → records. feedparser is a collector dep."""
    import feedparser  # local import: only RSS path needs it
    agent = user_agent or os.environ.get("LACLAUGPT_RSS_USER_AGENT") or _DEFAULT_UA
    parsed = feedparser.parse(feed_url, agent=agent)
    records: list[CollectRecord] = []
    for entry in parsed.entries:
        published = ""
        for attr in ("published_parsed", "updated_parsed"):
            dt = getattr(entry, attr, None)
            if dt:
                import calendar
                published = datetime.fromtimestamp(
                    calendar.timegm(dt), tz=timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ")
                break
        records.append(CollectRecord(
            source_type="rss",
            native_id=getattr(entry, "id", None) or getattr(entry, "link", None),
            url=getattr(entry, "link", None) or feed_url,
            title=(getattr(entry, "title", "") or "")[:300] or None,
            author=_entry_author(entry),
            published_at=published or None,
            text=_strip_html(getattr(entry, "summary", "") or "") or None,
            metadata={"feed_url": feed_url, "feed_name": feed_name or feed_url,
                      "fetch_article": fetch_article},
            collector="rss", imported_from=feed_url,
        ))
    return records


def _entry_author(entry) -> str | None:
    authors = getattr(entry, "authors", None) or []
    names = [a.get("name", "") for a in authors if isinstance(a, dict)]
    if not names and getattr(entry, "author", None):
        names = [entry.author]
    return ", ".join(n for n in names if n) or None


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    import html as html_mod
    return html_mod.unescape(text)


def collect_web(url: str, *, html_text: str | None = None,
                http_status: int | None = None) -> CollectRecord:
    """One webpage → record. Network fetch stays OUTSIDE this function
    (tests inject html_text; CLI fetches with the collector HTTP helper).
    Main-text extraction: trafilatura when available, HTML-strip fallback.
    """
    text = None
    try:
        import trafilatura
        text = trafilatura.extract(html_text or "", include_comments=False,
                                   include_tables=False)
    except ImportError:
        text = None
    if not text and html_text:
        text = _strip_html(re.sub(
            r"<(script|style)[^>]*>.*?</\1>", " ", html_text,
            flags=re.S | re.I))[:20000]
    title = None
    if html_text:
        m = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.S | re.I)
        if m:
            title = _strip_html(m.group(1))[:300]
    return CollectRecord(
        source_type="web", native_id=normalize_url(url), url=url,
        title=title, text=text,
        metadata={"http_status": http_status,
                  "extraction": "trafilatura" if text else "html-strip"},
        collector="web", imported_from=url,
    )


def collect_manual(*, url: str | None = None, text: str | None = None,
                   title: str | None = None, author: str | None = None,
                   file_path: str | None = None,
                   notes: str | None = None) -> CollectRecord:
    """Human-researcher submission. Deliberately boring; never bypasses
    provenance — method=collect:manual, collector=manual."""
    if file_path:
        text = Path(file_path).read_text(encoding="utf-8")
    return CollectRecord(
        source_type="manual", url=url, title=title, author=author,
        text=text, metadata={"notes": notes} if notes else {},
        collector="manual", imported_from=url,
    )


def collect_hermes(payload: dict) -> list[CollectRecord]:
    """Hermes Agent submission contract (JSON).

    Expected shape:
      {"items": [{
          "source_type": "web"|"text"|..., "url": ..., "title": ...,
          "text": ..., "author": ..., "published_at": ..., "tags": [...],
          "hermes_metadata": {...}, "hermes_commentary": "..."
      }]}
    Only SOURCE CONTENT enters the corpus. Hermes metadata and analytical
    commentary are preserved as metadata, never as source text — Hermes
    interpretation is not source truth.
    """
    out: list[CollectRecord] = []
    for item in payload.get("items", []):
        meta = {
            "hermes_metadata": item.get("hermes_metadata") or {},
            "hermes_commentary": item.get("hermes_commentary"),
            "tags": item.get("tags") or [],
        }
        out.append(CollectRecord(
            source_type="hermes",
            native_id=item.get("native_id"),
            url=item.get("url"), title=item.get("title"),
            author=item.get("author"),
            published_at=item.get("published_at"),
            text=item.get("text"),
            metadata=meta, collector="hermes",
            imported_from="hermes-agent",
        ))
    return out


def collect_telegram_message(msg: dict) -> CollectRecord:
    """Normalize one event from an external Telegram collector.

    The live Telegram collector, its host, database/collection names, session
    material and channel/watch-list settings are deployment-private. This public
    adapter only defines the portable event boundary and does not reimplement
    Telegram collection.
    """
    return CollectRecord(
        source_type="telegram",
        native_id=str(msg.get("message_id") or msg.get("_id") or ""),
        url=msg.get("url") or msg.get("message_url"),
        title=None, author=msg.get("channel") or msg.get("author"),
        published_at=msg.get("published_at") or msg.get("date"),
        text=msg.get("text") or msg.get("message"),
        platform="telegram",
        metadata={"channel": msg.get("channel"),
                  "upstream_source": "external-telegram-event"},
        collector="telegram",
        imported_from="external-telegram-collector",
    )