"""Pure data preparation for the LaclauGPT visualization layer."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from laclaugpt_interchange import DocumentAnnotation, from_jsonl


def _get(value: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a Pydantic object or a plain mapping."""
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _labels(values: Iterable[Any] | None) -> list[str]:
    labels: list[str] = []
    for value in values or []:
        label = _get(value, "label")
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


def _hegemonic_evidence_quotes(annotation: DocumentAnnotation) -> list[str]:
    """Normalize schema >=1.4 typed hegemonic evidence and legacy strings."""
    quotes: list[str] = []
    for item in annotation.hegemonic_evidence or []:
        quote = _get(item, "quote", item if isinstance(item, str) else "")
        if quote and str(quote).strip():
            quotes.append(str(quote))
    return quotes


def _sentiment_rows(annotation: DocumentAnnotation) -> list[dict[str, Any]]:
    """Flatten descriptive sentiment without conflating it with affect."""
    rows: list[dict[str, Any]] = []
    for item in annotation.sentiment_observations or []:
        target = _get(item, "target")
        label = _get(target, "label", "")
        obj_id = _get(target, "obj_id", "")
        polarity = str(_get(item, "polarity", "") or "")
        if not (label or obj_id or polarity):
            continue
        rows.append(
            {
                "target": str(label or obj_id),
                "target_id": str(obj_id or ""),
                "polarity": polarity,
                "uncertainty": float(_get(item, "uncertainty", 0.0) or 0.0),
                "model": str(_get(item, "model", "") or ""),
                "prompt_version": str(_get(item, "prompt_version", "") or ""),
                "review_status": str(_get(item, "review_status", "") or ""),
                "evidence_source": str(_get(item, "evidence_source", "") or ""),
            }
        )
    return rows


def annotation_to_row(annotation: DocumentAnnotation) -> dict[str, Any]:
    """Flatten one current interchange annotation without discarding the raw record."""
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
    hegemonic_evidence = _hegemonic_evidence_quotes(annotation)
    evidence = list(annotation.evidence_quotes or []) + hegemonic_evidence
    uncertainties = list(annotation.uncertainties or [])
    sentiments = _sentiment_rows(annotation)
    sentiment_labels = [
        f"{item['target']}: {item['polarity']}" for item in sentiments if item["polarity"]
    ]
    sentiment_polarities = sorted(
        {item["polarity"] for item in sentiments if item["polarity"]}
    )
    sentiment_targets = sorted(
        {item["target"] for item in sentiments if item["target"]}
    )
    relevance_state = annotation.relevance or "unreviewed"
    applicability_state = (
        "unreviewed"
        if annotation.discourse_applicable is None
        else "applicable" if annotation.discourse_applicable else "not_applicable"
    )
    searchable = "\n".join(
        str(value)
        for value in (
            annotation.document_id,
            annotation.source_author,
            annotation.summary,
            annotation.relevance_reason,
            annotation.discourse_applicability_reason,
            annotation.non_populist_reason,
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
            *sentiment_labels,
            *evidence,
            *uncertainties,
        )
        if value
    )
    return {
        "schema_version": annotation.schema_version,
        "document_id": annotation.document_id,
        "project": str(provenance.get("project", "")),
        "analysis_profile": str(provenance.get("analysis_profile", "")),
        "arena_id": str(provenance.get("arena_id", provenance.get("arena", ""))),
        "run_id": annotation.run_id,
        "source_platform": annotation.source_platform,
        "source_country": annotation.source_country,
        "language": annotation.language,
        "source_author": annotation.source_author,
        "source_timestamp": timestamp,
        "source_url": annotation.source_url,
        "source_modalities": list(annotation.source_modalities or []),
        "sequence_index": annotation.sequence_index,
        "model": annotation.model,
        "review_status": annotation.review_status,
        "requires_human_review": bool(annotation.requires_human_review),
        "relevance": annotation.relevance,
        "relevance_state": relevance_state,
        "relevance_reason": annotation.relevance_reason,
        "discourse_applicable": annotation.discourse_applicable,
        "discourse_applicability": applicability_state,
        "discourse_applicability_reason": annotation.discourse_applicability_reason,
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
        "sentiments": sentiments,
        "sentiment_labels": sentiment_labels,
        "sentiment_polarities": sentiment_polarities,
        "sentiment_targets": sentiment_targets,
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
    """Load canonical current-schema JSONL/NDJSON annotations."""
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
    models: Iterable[str] = (),
    review_statuses: Iterable[str] = (),
    relevance_states: Iterable[str] = (),
    discourse_applicabilities: Iterable[str] = (),
    authors: Iterable[str] = (),
    entities: Iterable[str] = (),
    topics: Iterable[str] = (),
    signifiers: Iterable[str] = (),
    sentiment_polarities: Iterable[str] = (),
    sentiment_targets: Iterable[str] = (),
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
        "model": set(models),
        "review_status": set(review_statuses),
        "relevance_state": set(relevance_states),
        "discourse_applicability": set(discourse_applicabilities),
        "source_author": set(authors),
    }
    for column, selected in scalar_filters.items():
        if selected and column in out:
            out = out[out[column].fillna("").astype(str).isin(selected)]
    for column, selected in (
        ("entities", set(entities)),
        ("topics", set(topics)),
        ("signifiers", set(signifiers)),
        ("sentiment_polarities", set(sentiment_polarities)),
        ("sentiment_targets", set(sentiment_targets)),
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
                    row["mean_confidence"] * old_count
                    + float(articulation.confidence or 0.0)
                ) / row["count"]
                row["verified_count"] += int(bool(articulation.evidence_verified))
    rows = sorted(
        aggregated.values(),
        key=lambda row: (-row["count"], row["source"], row["target"]),
    )
    if limit is not None:
        rows = rows[:limit]
    return pd.DataFrame(rows)
