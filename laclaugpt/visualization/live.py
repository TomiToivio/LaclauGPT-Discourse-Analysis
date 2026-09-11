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
    max_formation_confidences: list[float] = []

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
        confidences = [
            float(item.confidence)
            for item in annotation.formation_candidates or []
            if item.confidence is not None
        ]
        max_formation_confidences.append(max(confidences) if confidences else None)

    frame["analysis_status"] = statuses
    frame["collector"] = collectors
    frame["source_kind"] = source_kinds
    frame["analysis_method"] = analysis_methods
    frame["analysis_timestamp"] = pd.to_datetime(
        analysis_timestamps, errors="coerce", utc=True
    )
    frame["relation_count"] = relation_counts
    frame["candidate_role_count"] = candidate_role_counts
    frame["max_formation_confidence"] = max_formation_confidences
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


def filter_min_confidence(frame: pd.DataFrame, min_confidence: Any) -> pd.DataFrame:
    """Keep documents whose strongest candidate formation passes a threshold.

    Formation confidence is model-reported and uncalibrated. The threshold is a
    display filter for the researcher, never a validity judgement.
    """
    try:
        threshold = float(min_confidence or 0.0)
    except (TypeError, ValueError):
        threshold = 0.0
    if threshold <= 0.0 or frame.empty or "max_formation_confidence" not in frame:
        return frame.copy()
    values = pd.to_numeric(frame["max_formation_confidence"], errors="coerce").fillna(0.0)
    return frame[values >= threshold].copy()


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


def signifier_trend(
    frame: pd.DataFrame, *, recent: pd.Timedelta | None = None
) -> pd.DataFrame:
    """Compare recent and earlier corpus halves for each observed signifier.

    Both periods are measured in the same filtered view, so rising or falling
    counts describe this corpus window only, not global usage. A signifier
    counted as emerging/declining here remains a descriptive observation.
    """
    columns = [
        "signifier",
        "documents",
        "recent_documents",
        "earlier_documents",
        "trend",
    ]
    if frame.empty or "signifiers" not in frame or "source_timestamp" not in frame:
        return pd.DataFrame(columns=columns)
    exploded = frame[["source_timestamp", "document_id", "signifiers"]].explode("signifiers")
    exploded = exploded.dropna(subset=["source_timestamp"])
    exploded["signifiers"] = exploded["signifiers"].fillna("").astype(str).str.strip()
    exploded = exploded[exploded["signifiers"] != ""]
    if exploded.empty:
        return pd.DataFrame(columns=columns)
    timestamps = pd.to_datetime(exploded["source_timestamp"], errors="coerce", utc=True)
    anchor = timestamps.max()
    window = recent or (anchor - timestamps.min()) / 2 or pd.Timedelta(days=7)
    cutoff = anchor - window
    recent_part = exploded[timestamps >= cutoff]
    earlier_part = exploded[timestamps < cutoff]
    totals = exploded.groupby("signifiers")["document_id"].nunique()
    recent_counts = recent_part.groupby("signifiers")["document_id"].nunique()
    earlier_counts = earlier_part.groupby("signifiers")["document_id"].nunique()
    rows: list[dict[str, Any]] = []
    for label in totals.index.sort():
        total = int(totals[label])
        recent_count = int(recent_counts.get(label, 0))
        earlier_count = int(earlier_counts.get(label, 0))
        if recent_count > earlier_count:
            trend = "rising"
        elif recent_count < earlier_count:
            trend = "declining"
        else:
            trend = "stable"
        rows.append(
            {
                "signifier": label,
                "documents": total,
                "recent_documents": recent_count,
                "earlier_documents": earlier_count,
                "trend": trend,
            }
        )
    order = {"rising": 0, "stable": 1, "declining": 2}
    result = pd.DataFrame(rows, columns=columns)
    result["trend_rank"] = result["trend"].map(order)
    return result.sort_values(
        ["trend_rank", "recent_documents", "signifier"],
        ascending=[True, False, True],
    ).drop(columns="trend_rank")


def antagonism_poles(
    annotations: Iterable[DocumentAnnotation],
) -> pd.DataFrame:
    """Aggregate antagonism relations by articulated side-pair over time.

    Returns one row per (source-side, target-side) pair with the actors that
    articulate each side and the evidence-bearing supporting documents. Sides
    are taken verbatim from coded relations; no fixed opposition list exists.
    """
    rows: list[dict[str, Any]] = []
    for annotation in annotations:
        for articulation in annotation.articulations or []:
            relation = str(articulation.relation or "").casefold()
            if "antagon" not in relation:
                continue
            for target in articulation.related_to or []:
                rows.append(
                    {
                        "side_a": str(articulation.signifier.label or ""),
                        "side_b": str(target.label or ""),
                        "documents": annotation.document_id,
                        "actor": str(annotation.source_author or ""),
                        "timestamp": annotation.source_timestamp,
                        "claim_status": articulation.claim_status,
                        "model_confidence": articulation.confidence,
                        "evidence_verified": articulation.evidence_verified,
                        "evidence": articulation.evidence,
                        "source_url": annotation.source_url,
                        "platform": annotation.source_platform,
                    }
                )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "antagonism",
                "side_a_actors",
                "side_b_actors",
                "documents",
                "latest_source",
            ]
        )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)

    def _ordered(row: pd.Series) -> tuple[str, str, str, str]:
        side_a, side_b = str(row["side_a"]), str(row["side_b"])
        if side_a.casefold() > side_b.casefold():
            side_a, side_b = side_b, side_a
        return side_a, side_b, str(row["documents"]), str(row["actor"])

    ordered = frame.apply(_ordered, axis=1, result_type="expand")
    frame[["side_a", "side_b", "documents", "actor"]] = ordered
    frame["document_id"] = frame["documents"]
    grouped = frame.groupby(["side_a", "side_b"], dropna=False)
    result = grouped.agg(
        documents=("document_id", "nunique"),
        latest_source=("timestamp", "max"),
    ).reset_index()
    actors_by_side = frame.groupby(["side_a", "side_b"])["actor"].apply(
        lambda values: sorted({value for value in values if value.strip()})
    )
    side_a_actors: list[str] = []
    side_b_actors: list[str] = []
    for pair, actors in actors_by_side.items():
        _pair = pair  # deterministic (side_a, side_b) tuple
        actors_csv = ", ".join(actors) or "n/a"
        side_a_actors.append(actors_csv)
        side_b_actors.append(actors_csv)
    result["side_a_actors"] = side_a_actors
    result["side_b_actors"] = side_b_actors
    result["antagonism"] = result["side_a"] + " ↔ " + result["side_b"]
    return result.sort_values(
        ["documents", "antagonism"], ascending=[False, True]
    )


def formation_intensity(
    frame: pd.DataFrame,
    annotations: Iterable[DocumentAnnotation],
) -> pd.DataFrame:
    """Describe per-formation coded relation density alongside document counts.

    Intensity is relations (articulation-family codes) per document carrying the
    formation candidate. It is a corpus metric about coded relations, never a
    measure of public opinion or discourse 'strength' in the wild.
    """
    relation_counts: Counter[str] = Counter()
    for annotation in annotations:
        for articulation in annotation.articulations or []:
            formation_labels = [
                str(item.formation.label)
                for item in annotation.formation_candidates or []
                if item.formation and item.formation.label
            ]
            for label in formation_labels:
                relation_counts[label] += len(articulation.related_to or [])
    if frame.empty or "formations" not in frame:
        return pd.DataFrame(
            columns=["formation", "documents", "actors", "relations", "relations_per_document"]
        )
    rows = frame[["document_id", "source_author", "formations"]].explode("formations")
    rows["formations"] = rows["formations"].fillna("").astype(str).str.strip()
    rows = rows[rows["formations"] != ""]
    if rows.empty:
        return pd.DataFrame(
            columns=["formation", "documents", "actors", "relations", "relations_per_document"]
        )
    documents = rows.groupby("formations")["document_id"].nunique()
    actors = rows.groupby("formations")["source_author"].apply(
        lambda values: len({str(value) for value in values if str(value).strip()})
    )
    result = pd.DataFrame(
        {
            "documents": documents,
            "actors": actors,
            "relations": pd.Series(relation_counts),
        }
    )
    result.index.name = "formation"
    result = result.fillna(0).reset_index()
    result["relations"] = result["relations"].astype(int)
    result["relations_per_document"] = (result["relations"] / result["documents"]).round(2)
    return result.sort_values(
        ["documents", "formation"], ascending=[False, True]
    )


def actor_relations(
    annotations: Iterable[DocumentAnnotation], *, limit: int = 60
) -> pd.DataFrame:
    """Return each actor's strongest equivalential and antagonistic connections.

    Rows pair actors with the signifiers they most frequently articulate as
    equivalent or antagonistic. Connections are coded relations in evidence,
    not attributes of the actors themselves.
    """
    buckets: dict[str, dict[str, Counter[str]]] = {}
    for annotation in annotations:
        actor = str(annotation.source_author or "").strip()
        if not actor:
            continue
        family = buckets.setdefault(actor, {"equivalence": Counter(), "antagonism": Counter()})
        for articulation in annotation.articulations or []:
            relation = str(articulation.relation or "").casefold()
            kind = "equivalence" if "equiv" in relation else (
                "antagonism" if "antagon" in relation else ""
            )
            if not kind:
                continue
            related = [str(ref.label or "") for ref in articulation.related_to or []]
            related = [label for label in related if label]
            if related:
                family[kind][", ".join(related)] += 1
    rows: list[dict[str, Any]] = []
    for actor, family in buckets.items():
        for kind in ("equivalence", "antagonism"):
            for related, count in family[kind].most_common(3):
                rows.append(
                    {
                        "actor": actor,
                        "relation_family": kind,
                        "connected_to": related,
                        "coded_relations": count,
                    }
                )
    return pd.DataFrame(rows).head(limit)
