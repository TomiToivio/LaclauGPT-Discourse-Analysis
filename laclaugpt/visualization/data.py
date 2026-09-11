"""Pure data preparation for the LaclauGPT visualization layer."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from laclaugpt_interchange import (
    Articulation,
    DocumentAnnotation,
    FormationAssessment,
    MemoryRef,
    SignifierRole,
)


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
    transformations = annotation.transformations or {}
    source_title = str(transformations.get("source_title", ""))
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
            source_title,
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
        "source_title": source_title,
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


def _collection_bundle_annotation(
    payload: dict[str, Any], *, project: str = "", arena: str = ""
) -> DocumentAnnotation:
    """Expose a canonical collection bundle without inventing analysis."""
    source = payload.get("source") or {}
    ingestion = payload.get("ingestion") or {}
    metadata = source.get("metadata") or {}
    document_id = str(
        source.get("native_id")
        or source.get("source_id")
        or ingestion.get("source_id")
        or ingestion.get("ingestion_id")
        or ""
    )
    if not document_id:
        raise ValueError("collection bundle has no stable source or ingestion identifier")
    platform = str(source.get("platform") or source.get("source_type") or "")
    collected_at = source.get("collected_at") or ingestion.get("collected_at")
    return DocumentAnnotation(
        document_id=document_id,
        source_platform=platform,
        language=str(source.get("language") or ""),
        source_author=str(source.get("author_text") or ""),
        source_timestamp=str(source.get("published_at") or collected_at or ""),
        source_url=str(source.get("source_url") or ""),
        source_modalities=["text"] if source.get("raw_text") else [],
        run_id=str(ingestion.get("ingestion_id") or ""),
        analysis_stage="collection-only",
        summary="",
        relevance=None,
        discourse_applicable=None,
        collection_provenance={
            "project": str(ingestion.get("dataset_id") or metadata.get("project") or project),
            "arena_id": str(metadata.get("arena") or arena),
            "collector": str(ingestion.get("collector") or ""),
        },
        transformations={
            "collection_only": True,
            "source_title": str(source.get("title") or ""),
            "source_text": str(source.get("raw_text") or ""),
        },
    )


def _export_ref(label: Any, kind: str) -> MemoryRef:
    text = str(label or "").strip()
    digest = hashlib.sha256(f"{kind}:{text.casefold()}".encode("utf-8")).hexdigest()[:16]
    return MemoryRef(obj_id=f"export-{kind}-{digest}", label=text, kind=kind, raw=text)


def _flat_source_annotation(
    payload: dict[str, Any], *, project: str = "", arena: str = ""
) -> DocumentAnnotation:
    """Map an AI26 document export to an explicitly collection-only view."""
    document_id = str(payload.get("event_id") or payload.get("url") or "")
    if not document_id:
        raise ValueError("AI26 document export has no event_id or URL")
    return DocumentAnnotation(
        document_id=document_id,
        source_platform=str(payload.get("source") or payload.get("source_kind") or ""),
        source_author=str(payload.get("actor_label") or ""),
        source_timestamp=str(payload.get("published_at") or ""),
        source_url=str(payload.get("url") or ""),
        source_modalities=["text"] if payload.get("text") else [],
        analysis_stage="collection-only",
        collection_provenance={
            "project": project,
            "arena_id": arena,
            "source_kind": str(payload.get("source_kind") or ""),
            "adapter": "ai26-export-documents-v1",
        },
        transformations={
            "collection_only": True,
            "source_title": str(payload.get("title") or ""),
            "source_text": str(payload.get("text") or ""),
            "source_export_event_id": str(payload.get("event_id") or ""),
        },
    )


def _ai26_export_annotation(
    payload: dict[str, Any], *, project: str = "", arena: str = ""
) -> DocumentAnnotation:
    """Adapt the evidence-bearing AI26 export without inventing missing claims."""
    signifiers: list[MemoryRef] = []
    roles: list[SignifierRole] = []
    refs: dict[str, MemoryRef] = {}
    for item in payload.get("signifiers") or []:
        if not isinstance(item, dict) or not str(item.get("label") or "").strip():
            continue
        ref = _export_ref(item["label"], "signifier")
        refs[ref.label.casefold()] = ref
        signifiers.append(ref)
        roles.append(
            SignifierRole(
                signifier=ref,
                role=str(item.get("role") or "candidate"),
                evidence=str(item.get("evidence") or ""),
                evidence_verified=bool(item.get("evidence_verified", False)),
                needs_corpus_validation=str(item.get("role") or "").casefold()
                in {"empty", "floating", "empty_signifier", "floating_signifier"},
            )
        )

    articulations: list[Articulation] = []
    for item in payload.get("articulations") or []:
        if not isinstance(item, dict):
            continue
        source_label = str(item.get("source") or "").strip()
        target_label = str(item.get("target") or "").strip()
        evidence = str(item.get("evidence") or "").strip()
        if not (source_label and target_label and evidence):
            continue
        source_ref = refs.get(source_label.casefold()) or _export_ref(source_label, "signifier")
        target_ref = refs.get(target_label.casefold()) or _export_ref(target_label, "signifier")
        articulations.append(
            Articulation(
                signifier=source_ref,
                related_to=[target_ref],
                relation=str(item.get("relation") or "articulates"),
                evidence=evidence,
                evidence_verified=bool(item.get("evidence_verified", False)),
                claim_status="uncertain",
            )
        )

    formations: list[FormationAssessment] = []
    for item in payload.get("formation_candidates") or []:
        if not isinstance(item, dict) or not str(item.get("formation") or "").strip():
            continue
        supporting = []
        if item.get("subflavor"):
            supporting.append(str(item["subflavor"]))
        formations.append(
            FormationAssessment(
                formation=_export_ref(item["formation"], "formation"),
                supporting_features=supporting,
                evidence=str(item.get("evidence") or ""),
                confidence=float(item.get("confidence") or 0.0),
                evidence_verified=False,
            )
        )

    missing_affect_targets = bool(payload.get("affects"))
    uncertainties = []
    if missing_affect_targets:
        uncertainties.append(
            "AI26 export affects retained in transformations only because the export "
            "does not identify their canonical target."
        )
    run = payload.get("analysis_run") or {}
    return DocumentAnnotation(
        document_id=str(payload.get("document_id") or payload.get("event_id") or ""),
        source_platform=str(payload.get("source") or ""),
        source_author=str(payload.get("actor_label") or ""),
        source_timestamp=str(payload.get("published_at") or ""),
        source_url=str(payload.get("url") or ""),
        source_modalities=["text"],
        run_id=str(run.get("at") or payload.get("event_id") or ""),
        model=str(payload.get("model") or run.get("model") or ""),
        review_status=str(payload.get("review_status") or "PROVISIONAL"),
        requires_human_review=True,
        signifiers=signifiers,
        signifier_roles=roles,
        articulations=articulations,
        formation_candidates=formations,
        affects=[],
        populist=payload.get("populist"),
        non_populist_reason=str(payload.get("non_populist_reason") or ""),
        prompt_versions=dict(payload.get("prompt_versions") or {}),
        uncertainties=uncertainties,
        collection_provenance={
            "project": project,
            "arena_id": arena,
            "adapter": "ai26-export-annotations-v1",
            "analysis_method": str(run.get("method") or ""),
        },
        transformations={
            "source_title": str(payload.get("title") or ""),
            "source_export_event_id": str(payload.get("event_id") or ""),
            "unmapped_affects": payload.get("affects") or [],
        },
    )

def load_annotations(
    path: str | Path, *, project: str = "", arena: str = ""
) -> list[DocumentAnnotation]:
    """Load annotations or canonical collection bundles for honest preview."""
    suffix = Path(path).suffix.casefold()
    if suffix not in {".jsonl", ".ndjson"}:
        raise ValueError(
            "dashboard input must be canonical LaclauGPT .jsonl or .ndjson output"
        )
    records: list[DocumentAnnotation] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if isinstance(payload, dict) and "source" in payload and "ingestion" in payload:
                    records.append(
                        _collection_bundle_annotation(payload, project=project, arena=arena)
                    )
                elif isinstance(payload, dict) and {"event_id", "text", "source_kind"} <= payload.keys():
                    records.append(
                        _flat_source_annotation(payload, project=project, arena=arena)
                    )
                elif isinstance(payload, dict) and "event_id" in payload and "analysis_run" in payload:
                    records.append(
                        _ai26_export_annotation(payload, project=project, arena=arena)
                    )
                else:
                    records.append(DocumentAnnotation.model_validate(payload))
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                raise ValueError(f"invalid dashboard record at line {line_number}: {exc}") from exc
    return records
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
