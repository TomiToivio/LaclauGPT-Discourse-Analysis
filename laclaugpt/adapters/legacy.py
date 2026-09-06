"""Non-destructive adapters for historical LaclauGPT/TikTok records."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from laclaugpt.identity import normalize_url, source_identity
from laclaugpt.model import (Actor, Annotation, IngestionRecord, MediaAsset,
                             Provenance, Representation, SourceItem)


@dataclass
class LegacyBundle:
    source: SourceItem
    provenance: Provenance
    ingestion: IngestionRecord
    actors: list[Actor] = field(default_factory=list)
    media: list[MediaAsset] = field(default_factory=list)
    representations: list[Representation] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)


class LegacyTikTokAdapter:
    known = {
        "videoId", "videoDescription", "authorId", "authorUniqueId",
        "authorNickname", "authorSignature", "summary_analysis", "videoCreated",
        "videoUrl", "whisper_transcript", "videoPlayCount", "videoShareCount",
        "videoCommentCount", "videoDiggCount", "videoCollectCount", "evaluation",
        "populism", "social_contract", "grievance_politics", "us_and_them",
        "topics", "entities", "positive", "neutral", "negative", "sentiment_target",
    }

    def convert(self, row: dict[str, Any], *, dataset_id: str | None = None) -> LegacyBundle:
        url = _none(row.get("videoUrl") or row.get("url"))
        native = _none(row.get("videoId") or row.get("id"))
        sid = (source_identity(url=url, platform="tiktok", native_id=native)
               if url or native else "src_legacy_" + hashlib.sha256(
                   json.dumps(row, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24])
        provenance = Provenance(method="import", imported_from="legacy_tiktok")
        engagement = {
            key: _number(row.get(old)) for key, old in {
                "plays": "videoPlayCount", "shares": "videoShareCount",
                "comments": "videoCommentCount", "likes": "videoDiggCount",
                "collections": "videoCollectCount",
            }.items() if _none(row.get(old)) is not None
        }
        source = SourceItem(
            source_id=sid, source_url=url,
            normalized_source_url=normalize_url(url) if url else None,
            platform="tiktok", source_type="video", native_id=native,
            author_text=_none(row.get("authorUniqueId") or row.get("authorNickname")),
            published_at=_datetime(row.get("videoCreated")),
            raw_text=_none(row.get("videoDescription")),
            metadata={"engagement": engagement},
            legacy_fields={k: v for k, v in row.items() if k not in self.known},
        )
        ingestion = IngestionRecord(source_id=sid, collector="legacy_tiktok",
                                    dataset_id=dataset_id, raw_metadata=dict(row),
                                    provenance_id=provenance.provenance_id)
        bundle = LegacyBundle(source=source, provenance=provenance, ingestion=ingestion)
        if source.author_text:
            bundle.actors.append(Actor(
                actor_id=f"act_tiktok_{row.get('authorId') or source.author_text}",
                canonical_name=str(source.author_text), actor_type="social_account",
                metadata={k: row.get(k) for k in
                          ("authorId", "authorUniqueId", "authorNickname", "authorSignature")
                          if row.get(k) is not None}))
        video = MediaAsset(source_id=sid, media_type="video", uri=url)
        bundle.media.append(video)
        for representation_type, text, metadata in _representations(row):
            bundle.representations.append(Representation(
                source_id=sid, media_id=video.media_id,
                representation_type=representation_type, text=text,
                metadata=metadata, provenance_id=provenance.provenance_id))
        for key in ("populism", "social_contract", "grievance_politics", "us_and_them"):
            value = row.get(key)
            if _none(value) is not None:
                bundle.annotations.append(Annotation(
                    target_type="SourceItem", target_id=sid,
                    annotation_type=f"legacy_{key}", value=_jsonish(value),
                    schema="legacy_laclaugpt", provenance_id=provenance.provenance_id))
        return bundle


class LegacyCSVAdapter:
    def __init__(self, record_adapter: LegacyTikTokAdapter | None = None):
        self.record_adapter = record_adapter or LegacyTikTokAdapter()

    def import_documents(self, path: str | Path) -> list[LegacyBundle]:
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            return [self.record_adapter.convert(row, dataset_id=Path(path).stem)
                    for row in csv.DictReader(handle)]


class LegacyMongoAdapter:
    """Converts mappings/cursors; pymongo remains outside the canonical layer."""
    def __init__(self, record_adapter: LegacyTikTokAdapter | None = None):
        self.record_adapter = record_adapter or LegacyTikTokAdapter()

    def import_documents(self, records: Iterable[dict[str, Any]],
                         dataset_id: str | None = None) -> Iterable[LegacyBundle]:
        for record in records:
            row = dict(record)
            row.pop("_id", None)
            yield self.record_adapter.convert(row, dataset_id=dataset_id)


def _representations(row: dict[str, Any]):
    for typ, key in (("source_text", "videoDescription"),
                     ("transcript", "whisper_transcript"),
                     ("summary", "summary_analysis")):
        if text := _none(row.get(key)):
            yield typ, str(text), {"legacy_field": key}
    frames = sorted((k, v) for k, v in row.items()
                    if k.startswith("frame_analysis_") and _none(v) is not None)
    for key, value in frames:
        yield "frame_description", str(value), {"legacy_field": key}


def _none(value: Any):
    return None if value is None or (isinstance(value, str) and not value.strip()) else value


def _number(value: Any):
    value = _none(value)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value


def _datetime(value: Any) -> datetime | None:
    value = _none(value)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)) or str(value).isdigit():
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _jsonish(value: Any):
    if isinstance(value, (dict, list, bool, int, float)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return str(value)
