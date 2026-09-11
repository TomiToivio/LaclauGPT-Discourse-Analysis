"""Pure helpers for near-real-time LaclauGPT corpus visualization.

The functions in this module derive descriptive dashboard views from canonical
``DocumentAnnotation`` objects. They never promote frequency, centrality or model
confidence into theoretical validity.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Sequence

import pandas as pd

from laclaugpt.visualization.data import flatten_annotations
from laclaugpt_interchange import DocumentAnnotation


TIME_WINDOWS = {
    "Last hour": pd.Timedelta(hours=1),
    "24 hours": pd.Timedelta(hours=24),
    "7 days": pd.Timedelta(days=7),
    "30 days": pd.Timedelta(days=30),
    "Full corpus": None,
}


def build_live_frame(annotations: Sequence[DocumentAnnotation]) -> pd.DataFrame:
    """Flatten annotations and add operational fields used by the live dashboard."""
    frame = flatten_annotations(annotations)
    if frame.empty:
        return frame

    statuses: list[str] = []
    collectors: list[str] = []
    source_kinds: list[str] = []
    analysis_methods: list[str] = []
    analysis_timestamps: list[Any] = []
    relation_counts: list[int] = []
    candidate_role_counts: list[int] = []

    for annotation in annotations:
        provenance = annotation.collection_provenance or {}
        transformations = annotation.transformations or {}
        collection_only = bool(transformations.get("collection_only"))
        stage = str(getattr(annotation, "analysis_stage", "") or "")
        statuses.append("collection-only" if collection_only else stage or "analyzed")
        collectors.append(str(provenance.get("collector") or ""))
        source_kinds.append(str(provenance.get("source_kind") or ""))
        analysis_methods.append(str(provenance.get("analysis_method") or ""))
        analysis_timestamps.append(getattr(annotation, "created_at", None))
        relation_counts.append(len(annotation.articulations or []))
        candidate_role_counts.append(len(annotation.signifier_roles or []))

    frame["analysis_status"] = statuses
    frame["collector"] = collectors
    frame["source_kind"] = source_kinds
    frame["analysis_method"] = analysis_methods
    frame["analysis_timestamp"] = pd.to_datetime(
        analysis_timestamps, errors="coerce", utc=True
    )
    frame["relation_count"] = relation_counts
    frame["candidate_role_count"] = candidate_role_counts
    return frame


def apply_time_window(
    frame: pd.DataFrame,
    label: str,
    *,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Filter by a human-friendly rolling source-time window."""
    if frame.empty or "source_timestamp" not in frame or label == "Full corpus":
        return frame.copy()
    delta = TIME_WINDOWS.get(label)
    if delta is None:
        return frame.copy()
    anchor = now or pd.Timestamp.now(tz="UTC")
    if anchor.tzinfo is None:
        anchor = anchor.tz_localize("UTC")
    cutoff = anchor - delta
    timestamps = pd.to_datetime(frame["source_timestamp"], errors="coerce", utc=True)
    return frame[timestamps >= cutoff].copy()


def filter_list_value(
    frame: pd.DataFrame,
    column: str,
    selected: Iterable[str],
) -> pd.DataFrame:
    """Filter a list-valued column while keeping the operation schema-agnostic."""
    wanted = {str(value) for value in selected if str(value).strip()}
    if not wanted or frame.empty or column not in frame:
        return frame.copy()
    return frame[
        frame[column].apply(
            lambda values: bool(
                wanted.intersection(str(value) for value in values)
                if isinstance(values, (list, tuple, set))
                else str(values) in wanted
            )
        )
    ].copy()


def explode_timeline(
    frame: pd.DataFrame,
    column: str,
    *,
    period: str = "D",
    value_name: str = "label",
) -> pd.DataFrame:
    """Count list-valued labels by source-time period."""
    if frame.empty or column not in frame or "source_timestamp" not in frame:
        return pd.DataFrame(columns=["period", value_name, "documents"])
    subset = frame[["source_timestamp", column]].copy()
    subset = subset.dropna(subset=["source_timestamp"])
    subset = subset.explode(column)
    subset[column] = subset[column].fillna("").astype(str).str.strip()
    subset = subset[subset[column] != ""]
    if subset.empty:
        return pd.DataFrame(columns=["period", value_name, "documents"])
    subset["period"] = pd.to_datetime(
        subset["source_timestamp"], errors="coerce", utc=True
    ).dt.floor(period)
    return (
        subset.groupby(["period", column], dropna=False)
        .size()
        .reset_index(name="documents")
        .rename(columns={column: value_name})
        .sort_values(["period", "documents", value_name])
    )


def _join_top(values: Iterable[str], limit: int = 5) -> str:
    counts = Counter(str(value) for value in values if str(value).strip())
    return ", ".join(label for label, _count in counts.most_common(limit))


def actor_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize source authors without treating them as fixed ideological subjects."""
    columns = [
        "actor",
        "documents",
        "platforms",
        "candidate_formations",
        "signifiers",
        "latest_source",
    ]
    if frame.empty or "source_author" not in frame:
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, Any]] = []
    for actor, group in frame.groupby(frame["source_author"].fillna("").astype(str)):
        actor = actor.strip()
        if not actor:
            continue
        formations = [item for values in group["formations"] for item in values]
        signifiers = [item for values in group["signifiers"] for item in values]
        platforms = sorted(
            {str(value) for value in group["source_platform"] if str(value).strip()}
        )
        latest = pd.to_datetime(group["source_timestamp"], errors="coerce", utc=True).max()
        rows.append(
            {
                "actor": actor,
                "documents": len(group),
                "platforms": ", ".join(platforms),
                "candidate_formations": _join_top(formations),
                "signifiers": _join_top(signifiers),
                "latest_source": latest,
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["documents", "actor"], ascending=[False, True]
    )


def signifier_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize observed signifiers and their descriptive associations."""
    columns = [
        "signifier",
        "documents",
        "actors",
        "candidate_formations",
        "platforms",
        "latest_source",
    ]
    if frame.empty or "signifiers" not in frame:
        return pd.DataFrame(columns=columns)
    buckets: dict[str, dict[str, Any]] = {}
    for row in frame.itertuples(index=False):
        for raw in getattr(row, "signifiers", []) or []:
            label = str(raw).strip()
            if not label:
                continue
            bucket = buckets.setdefault(
                label,
                {
                    "documents": set(),
                    "actors": set(),
                    "formations": [],
                    "platforms": set(),
                    "latest_source": pd.NaT,
                },
            )
            bucket["documents"].add(str(row.document_id))
            if str(row.source_author or "").strip():
                bucket["actors"].add(str(row.source_author))
            bucket["formations"].extend(getattr(row, "formations", []) or [])
            if str(row.source_platform or "").strip():
                bucket["platforms"].add(str(row.source_platform))
            timestamp = pd.to_datetime(row.source_timestamp, errors="coerce", utc=True)
            if pd.notna(timestamp) and (
                pd.isna(bucket["latest_source"]) or timestamp > bucket["latest_source"]
            ):
                bucket["latest_source"] = timestamp

    rows = [
        {
            "signifier": label,
            "documents": len(bucket["documents"]),
            "actors": len(bucket["actors"]),
            "candidate_formations": _join_top(bucket["formations"]),
            "platforms": ", ".join(sorted(bucket["platforms"])),
            "latest_source": bucket["latest_source"],
        }
        for label, bucket in buckets.items()
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["documents", "signifier"], ascending=[False, True]
    )


def relation_rows(
    annotations: Iterable[DocumentAnnotation],
    *,
    relations: Iterable[str] = (),
) -> pd.DataFrame:
    """Return evidence-bearing articulation rows for chains/frontiers inspection."""
    wanted = {str(value).casefold() for value in relations if str(value).strip()}
    rows: list[dict[str, Any]] = []
    for annotation in annotations:
        for articulation in annotation.articulations or []:
            relation = str(articulation.relation or "articulates")
            if wanted and relation.casefold() not in wanted:
                continue
            for target in articulation.related_to or []:
                rows.append(
                    {
                        "document_id": annotation.document_id,
                        "timestamp": annotation.source_timestamp,
                        "actor": annotation.source_author,
                        "platform": annotation.source_platform,
                        "source_url": annotation.source_url,
                        "source": articulation.signifier.label,
                        "relation": relation,
                        "target": target.label,
                        "claim_status": articulation.claim_status,
                        "model_confidence": articulation.confidence,
                        "evidence_verified": articulation.evidence_verified,
                        "evidence": articulation.evidence,
                    }
                )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    return frame


def signifier_role_rows(annotations: Iterable[DocumentAnnotation]) -> pd.DataFrame:
    """Return provisional signifier-role claims with corpus-validation flags."""
    rows: list[dict[str, Any]] = []
    for annotation in annotations:
        for item in annotation.signifier_roles or []:
            rows.append(
                {
                    "document_id": annotation.document_id,
                    "timestamp": annotation.source_timestamp,
                    "actor": annotation.source_author,
                    "signifier": item.signifier.label,
                    "role": item.role,
                    "needs_corpus_validation": item.needs_corpus_validation,
                    "model_confidence": item.confidence,
                    "evidence_verified": item.evidence_verified,
                    "evidence": item.evidence,
                }
            )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    return frame


def first_seen(frame: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    """Return first observed source timestamp for list-valued labels."""
    if frame.empty or column not in frame:
        return pd.DataFrame(columns=[label, "first_seen", "documents"])
    exploded = frame[["source_timestamp", "document_id", column]].explode(column)
    exploded[column] = exploded[column].fillna("").astype(str).str.strip()
    exploded = exploded[exploded[column] != ""]
    if exploded.empty:
        return pd.DataFrame(columns=[label, "first_seen", "documents"])
    exploded["source_timestamp"] = pd.to_datetime(
        exploded["source_timestamp"], errors="coerce", utc=True
    )
    return (
        exploded.groupby(column)
        .agg(first_seen=("source_timestamp", "min"), documents=("document_id", "nunique"))
        .reset_index()
        .rename(columns={column: label})
        .sort_values(["first_seen", label], ascending=[False, True])
    )
