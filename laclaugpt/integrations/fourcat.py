"""4CAT and Zeeschuimer corpus interchange."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from laclaugpt.identity import normalize_url, source_identity
from laclaugpt.model import SourceItem


def _source(row: dict[str, Any], platform: str | None = None) -> SourceItem:
    url = row.get("url") or row.get("source_url") or row.get("link")
    native_id = str(row.get("id") or row.get("post_id") or row.get("videoId") or "") or None
    platform = platform or row.get("platform") or row.get("source_platform")
    return SourceItem(
        source_id=source_identity(url=url, platform=platform, native_id=native_id),
        source_url=url, normalized_source_url=normalize_url(url) if url else None,
        platform=platform, source_type=row.get("source_type") or "post",
        native_id=native_id, author_text=row.get("author") or row.get("username"),
        raw_text=row.get("text") or row.get("body") or row.get("caption") or row.get("description"),
        metadata={"external": {"4cat": row}},
    )


def import_fourcat(path: str | Path, platform: str | None = None) -> list[SourceItem]:
    path = Path(path)
    if path.suffix.casefold() in {".json", ".jsonl", ".ndjson"}:
        content = path.read_text(encoding="utf-8-sig")
        rows = json.loads(content) if path.suffix.casefold() == ".json" else [json.loads(x) for x in content.splitlines() if x.strip()]
    else:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    return [_source(row, platform) for row in rows]


def import_zeeschuimer_ndjson(path: str | Path) -> list[SourceItem]:
    return import_fourcat(path)


def import_zeeschuimer_csv(path: str | Path) -> list[SourceItem]:
    return import_fourcat(path)


def export_fourcat(items: Iterable[SourceItem], path: str | Path,
                   analysis: dict[str, dict[str, Any]] | None = None) -> int:
    analysis = analysis or {}
    fields = ["id", "url", "platform", "author", "text", "timestamp",
              "laclaugpt_topics", "laclaugpt_entities", "laclaugpt_sentiment",
              "laclaugpt_discourses", "laclaugpt_signifiers", "laclaugpt_us",
              "laclaugpt_frontier", "laclaugpt_affects"]
    rows = []
    for item in items:
        extra = analysis.get(item.source_id, {})
        row = {"id": item.native_id or item.source_id, "url": item.source_url,
               "platform": item.platform, "author": item.author_text,
               "text": item.raw_text,
               "timestamp": item.published_at.isoformat() if item.published_at else None}
        for field in fields[6:]:
            value = extra.get(field.removeprefix("laclaugpt_"), [])
            row[field] = json.dumps(value, ensure_ascii=False)
        rows.append(row)
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    return len(rows)

