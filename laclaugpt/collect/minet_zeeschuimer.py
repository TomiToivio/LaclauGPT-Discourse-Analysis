# -*- coding: utf-8 -*-
"""Minet + Zeeschuimer ingestion into the canonical collection spine.

Reuses what exists:
- minet: the upstream web-mining layer per docs/INTEROPERABILITY_SPEC.md
  §12 — this module wraps `minet_adapter.import_minet_extract` /
  `import_minet_collector` (CSV) so minet output joins the same
  SourceItem/IngestionRecord spine as RSS/web/hermes/manual/telegram.
  minet itself is an OPTIONAL dependency (`pip install minet`); the
  adapter works from minet-produced CSVs without importing minet.
- Zeeschuimer: browser-extension captures exported as NDJSON (one JSON
  item per line, Zeeschuimer's documented export format: data, timestamp,
  platform, source, search, complete). The importer is platform-agnostic:
  it reads the wrapper fields, keeps the platform payload as external
  metadata, and requires caller/platform-specific text extraction via
  the `text_fields` probe list.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from laclaugpt.collect import CollectRecord

ZEEF_WRAP_KEYS = ("data", "timestamp", "platform", "source", "search",
                  "complete", "item_index")


def _first(item: dict, *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def collect_minet_extract(csv_path: str, *, text_column: str | None = None,
                          url_column: str | None = None,
                          author_column: str | None = None,
                          timestamp_column: str | None = None) -> list[CollectRecord]:
    """minet extract CSV -> records (spec §12 via minet_adapter)."""
    from minet_adapter import import_minet_extract
    rows, _stats = import_minet_extract(
        csv_path, text_column=text_column, url_column=url_column,
        author_column=author_column, timestamp_column=timestamp_column)
    out: list[CollectRecord] = []
    for i, row in enumerate(rows):
        external = row.get("external_metadata", {}).get("minet", {})
        out.append(CollectRecord(
            source_type="minet",
            native_id=_first(row, "id") or None,
            url=_first(row, "url") or None,
            title=None,
            author=_first(row, "author") or None,
            published_at=_first(row, "created_at") or None,
            text=_first(row, "text") or None,
            platform="minet-extract",
            metadata={"minet": external} if external else {},
            collector="minet", imported_from=csv_path,
        ))
    return out


def collect_minet_collector(csv_path: str, *, platform: str,
                            text_column: str | None = None) -> list[CollectRecord]:
    """minet platform-collector CSV (twitter/youtube/...) -> records."""
    from minet_adapter import import_minet_collector
    rows, _stats = import_minet_collector(csv_path, platform,
                                          text_column=text_column)
    out: list[CollectRecord] = []
    for row in rows:
        out.append(CollectRecord(
            source_type="minet",
            native_id=_first(row, "id") or None,
            url=_first(row, "url") or None,
            author=_first(row, "author") or None,
            published_at=_first(row, "created_at") or None,
            text=_first(row, "text") or None,
            platform=f"minet-{platform}",
            metadata={"minet_platform": platform},
            collector="minet", imported_from=csv_path,
        ))
    return out


def iter_zeeschuimer(path: str) -> Iterator[dict]:
    """Yield items from a Zeeschuimer NDJSON export (or JSON list file)."""
    text = Path(path).read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):  # some exports are a JSON array
        for item in json.loads(text):
            yield item
        return
    for line in text.splitlines():
        if line.strip():
            yield json.loads(line)


def _zeeschuimer_text(data: dict, text_fields: tuple[str, ...]) -> str:
    for key in text_fields:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        # one level of nesting (e.g. data.desc / item.caption patterns)
        if isinstance(value, dict):
            for sub in ("text", "desc", "caption", "content", "title"):
                inner = value.get(sub)
                if isinstance(inner, str) and inner.strip():
                    return inner.strip()
    return ""


def collect_zeeschuimer(ndjson_path: str, *,
                        text_fields: tuple[str, ...] = (
                            "desc", "caption", "text", "content",
                            "title", "body", "full_text"),
                        platform_hint: str | None = None) -> list[CollectRecord]:
    """Zeeschuimer NDJSON export -> records.

    The wrapper's `data` payload is platform-specific and preserved
    verbatim under metadata; text extraction probes common field names
    and can be overridden per platform. Items flagged incomplete
    (complete=false) are kept but marked — review decides.
    """
    records: list[CollectRecord] = []
    for i, item in enumerate(iter_zeeschuimer(ndjson_path)):
        if not isinstance(item, dict):
            continue
        data = item.get("data") or {}
        native_id = _first(item, "id") or _first(
            data, "id", "aweme_id", "pk", "code", "rest_id") or str(i)
        url = (_first(data, "url", "web_url", "share_url")
               or _first(item, "source"))
        author = ""
        for author_key in ("author", "user", "creator"):
            value = data.get(author_key)
            if isinstance(value, dict):
                author = _first(value, "unique_id", "username",
                                "handle", "nickname", "name")
                if author:
                    break
            elif isinstance(value, str) and value.strip():
                author = value.strip()
                break
        ts = _first(item, "timestamp") or _first(
            data, "create_time", "timestamp", "taken_at", "published_at")
        records.append(CollectRecord(
            source_type="zeeschuimer",
            native_id=native_id,
            url=url or None,
            author=author or None,
            published_at=ts or None,
            text=_zeeschuimer_text(data, text_fields) or None,
            platform=platform_hint or _first(item, "platform") or "zeeschuimer",
            metadata={
                "zeeschuimer": {"source": item.get("source"),
                                "search": item.get("search"),
                                "complete": item.get("complete"),
                                "item_index": item.get("item_index")},
                "platform_payload": data,
            },
            collector="zeeschuimer", imported_from=ndjson_path,
        ))
    return records