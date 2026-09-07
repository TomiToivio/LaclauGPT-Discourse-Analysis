"""Pure data preparation for the LaclauGPT visualization layer."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from laclaugpt_interchange import DocumentAnnotation, from_jsonl


def _labels(values: Iterable[Any]) -> list[str]:
    labels: list[str] = []
    for value in values or []:
        label = getattr(value, "label", None)
        if label is None and isinstance(value, dict):
            label = value.get("label")
        if label:
            labels.append(str(label))
    return labels


def _discourse_labels(annotation: DocumentAnnotation) -> list[str]:
    return [str(item.label) for item in annotation.discourses if item.label]


def _imaginary_labels(annotation: DocumentAnnotation) -> list[str]:
    return [str(item.label) for item in annotation.imaginaries if item.label]


def _formation_labels(annotation: DocumentAnnotation) -> list[str]:
    return [
        str(item.formation.label)
        for item in annotation.formation_candidates
        if item.formation and item.formation.label
    ]


def _affect_labels(annotation: DocumentAnnotation) -> list[str]:
    return [
        f"{item.target.label}: {item.affect}"
        for item in annotation.affects
        if item.target and item.target.label and item.affect
    ]


def annotation_to_row(annotation: DocumentAnnotation) -> dict[str, Any]:
    """Flatten one interchange annotation without discarding the raw record."""
    provenance = annotation.collection_provenance or {}
    timestamp = annotation.source_timestamp or annotation.created_at
    entities = _labels(annotation.entities)
    topics = _labels(annotation.topics)
    signifiers = _labels(annotation.signifiers)
    nodal_points = _labels(annotation.nodal_points)
    us = _labels(annotation.us)
    frontier = _labels(annotation.frontier)
    discourses = _discourse_labels(annotation)
    imaginaries = _imaginary_labels(annotation)
    formations = _formation_labels(annotation)
    affects = _affect_labels(annotation)
    evidence = list(annotation.evidence_quotes or []) + list(annotation.hegemonic_evidence or [])
    uncertainties = list(annotation.uncertainties or [])
    searchable = "\n".join(
        str(value)
        for value in (
            annotation.document_id,
            annotation.source_author,
            annotation.summary,
            *entities,
            *topics,
            *signifiers,
            *nodal_points,
            *us,
            *frontier,
            *discourses,
            *imaginaries,
            *formations,
            *affects,
            *evidence,
            *uncertainties,
        )
        if value
    )
    return {
        "document_id": annotation.document_id,
        "project": str(provenance.get("project", "")),
        "analysis_profile": str(provenance.get("analysis_profile", "")),
        "arena_id": str(provenance.get("arena_id", "")),
        "run_id": annotation.run_id,
        "source_platform": annotation.source_platform,
        "source_country": annotation.source_country,
        "language": annotation.language,
        "source_author": annotation.source_author,
        "source_timestamp": timestamp,
        "source_url": annotation.source_url,
        "model": annotation.model,
        "review_status": annotation.review_status,
        "requires_human_review": bool(annotation.requires_human_review),
        "populist": annotation.populist,
        "summary": annotation.summary,
        "entities": entities,
        "topics": topics,
        "signifiers": signifiers,
        "nodal_points": nodal_points,
        "discourses": discourses,
        "imaginaries": imaginaries,
        "formations": formations,
        "us": us,
        "frontier": frontier,
        "affects": affects,
        "uncertainties": uncertainties,
        "evidence_count": len(evidence),
        "searchable_text": searchable,
        "annotation": annotation,
    }


def flatten_annotations(annotations: Sequence[DocumentAnnotation]) -> pd.DataFrame:
    rows = [annotation_to_row(annotation) for annotation in annotations]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["source_timestamp"] = pd.to_datetime(
        frame["source_timestamp"], errors="coerce", utc=True
    )
    return frame


def load_annotations(path: str | Path) -> list[DocumentAnnotation]:
    """Load canonical schema-1.3 JSONL/NDJSON annotations."""
    suffix = Path(path).suffix.casefold()
    if suffix not in {".jsonl", ".ndjson"}:
        raise ValueError(
            "dashboard input must be canonical LaclauGPT .jsonl or .ndjson output"
        )
    return from_jsonl(str(path))


def _matches_list(value: Any, selected: set[str]) -> bool:
    if not selected:
        return True
    if isinstance(value, (list, tuple, set)):
        return bool(selected.intersection(str(item) for item in value))
    return str(value) in selected


def filter_frame(
    frame: pd.DataFrame,
    *,
    search: str = "",
    projects: Iterable[str] = (),
    profiles: Iterable[str] = (),
    arenas: Iterable[str] = (),
    platforms: Iterable[str] = (),
    countries: Iterable[str] = (),
    languages: Iterable[str] = (),
    review_statuses: Iterable[str] = (),
    authors: Iterable[str] = (),
    entities: Iterable[str] = (),
    topics: Iterable[str] = (),
    signifiers: Iterable[str] = (),
    start: Any = None,
    end: Any = None,
) -> pd.DataFrame:
    """Apply dashboard filters without project-specific assumptions."""
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    scalar_filters = {
        "project": set(projects),
        "analysis_profile": set(profiles),
        "arena_id": set(arenas),
        "source_platform": set(platforms),
        "source_country": set(countries),
        "language": set(languages),
        "review_status": set(review_statuses),
        "source_author": set(authors),
    }
    for column, selected in scalar_filters.items():
        if selected and column in out:
            out = out[out[column].fillna("").astype(str).isin(selected)]
    for column, selected in (
        ("entities", set(entities)),
        ("topics", set(topics)),
        ("signifiers", set(signifiers)),
    ):
        if selected and column in out:
            out = out[out[column].apply(lambda value: _matches_list(value, selected))]
    if search.strip():
        needle = search.casefold()
        out = out[
            out["searchable_text"].fillna("").astype(str).str.casefold().str.contains(
                needle, regex=False
            )
        ]
    if "source_timestamp" in out:
        timestamps = out["source_timestamp"]
        if start is not None:
            start_ts = pd.Timestamp(start)
            if start_ts.tzinfo is None:
                start_ts = start_ts.tz_localize("UTC")
            out = out[timestamps >= start_ts]
        if end is not None:
            end_ts = pd.Timestamp(end)
            if end_ts.tzinfo is None:
                end_ts = end_ts.tz_localize("UTC")
            if end_ts == end_ts.normalize():
                end_ts = end_ts + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            out = out[timestamps <= end_ts]
    return out


def top_values(frame: pd.DataFrame, column: str, limit: int = 20) -> pd.DataFrame:
    """Return top labels from a list-valued dashboard column."""
    if frame.empty or column not in frame:
        return pd.DataFrame(columns=["label", "count"])
    counts: Counter[str] = Counter()
    for values in frame[column]:
        if isinstance(values, (list, tuple, set)):
            counts.update(str(value) for value in values if str(value).strip())
        elif values is not None and str(values).strip():
            counts[str(values)] += 1
    return pd.DataFrame(counts.most_common(limit), columns=["label", "count"])


def articulation_edges(
    annotations: Iterable[DocumentAnnotation], limit: int | None = 100
) -> pd.DataFrame:
    """Aggregate evidence-bearing articulation edges for graph visualization."""
    aggregated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for annotation in annotations:
        for articulation in annotation.articulations:
            source = articulation.signifier.label
            if not source:
                continue
            for target in articulation.related_to:
                if not target.label:
                    continue
                key = (source, target.label, articulation.relation or "articulates")
                row = aggregated.setdefault(
                    key,
                    {
                        "source": source,
                        "target": target.label,
                        "relation": articulation.relation or "articulates",
                        "count": 0,
                        "mean_confidence": 0.0,
                        "verified_count": 0,
                    },
                )
                old_count = row["count"]
                row["count"] = old_count + 1
                row["mean_confidence"] = (
                    row["mean_confidence"] * old_count + float(articulation.confidence or 0.0)
                ) / row["count"]
                row["verified_count"] += int(bool(articulation.evidence_verified))
    rows = sorted(aggregated.values(), key=lambda row: (-row["count"], row["source"], row["target"]))
    if limit is not None:
        rows = rows[:limit]
    return pd.DataFrame(rows)
