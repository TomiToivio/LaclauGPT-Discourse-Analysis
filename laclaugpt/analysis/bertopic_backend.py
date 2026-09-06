"""BERTopic topic backend: embeddings → topic CANDIDATES.

Topics are descriptive clusters for the canonical Topic registry —
Topic != Discourse is structural: discover() returns Topic +
TopicAssignment only. Turning a topic cluster into a discourse, a
nodal point or a hegemony claim is separate theory-guided analysis
with evidence and human review.
"""
from __future__ import annotations

from typing import Any, Iterable

from laclaugpt.analysis import BackendUnavailable, TopicModelResult
from laclaugpt.model import Provenance, Topic, TopicAssignment

_BACKEND = "bertopic"


def is_available() -> bool:
    try:
        import bertopic  # noqa: F401
        return True
    except ImportError:
        return False


def _version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("bertopic")
    except Exception:
        return ""


def discover(documents: Iterable[str], *, model: str | None = None,
             language: str | None = None, timestamps: list[str] | None = None,
             provenance: Provenance | None = None) -> TopicModelResult:
    """One BERTopic pass: topics, per-document assignments, labels."""
    if not is_available():
        raise BackendUnavailable("bertopic is not installed")
    docs = [d for d in documents if d and d.strip()]
    if not docs:
        return TopicModelResult(method=_BACKEND, model_info={"documents": 0})
    from bertopic import BERTopic
    kwargs: dict[str, Any] = {"calculate_probabilities": False}
    if language:
        kwargs["language"] = language
    topic_model = BERTopic(**kwargs)
    topics, probs = topic_model.fit_transform(docs)
    provenance_id = provenance.provenance_id if provenance else ""
    result = TopicModelResult(
        method=_BACKEND,
        model_info={"library": "bertopic", "library_version": _version(),
                    "embedding": (topic_model.embedding_model.model_name_or_path
                                  if getattr(topic_model, "embedding_model", None) else None),
                    "n_documents": len(docs)},
        provenance_id=provenance_id,
    )
    for _, row in topic_model.get_topic_info().iterrows():
        tid = int(row["Topic"])
        label = str(row.get("Name") or f"topic_{tid}")
        # -1 = outlier cluster: never promoted into the registry
        if tid == -1:
            continue
        keywords = [word for word, _ in topic_model.get_topic(tid)[:8]]
        result.topics.append(Topic(
            topic_id=f"bertopic_{tid}",
            canonical_label=label.replace("_", " ").strip(),
            aliases=keywords,
            description=f"BERTopic cluster {tid}: {', '.join(keywords[:5])}",
            metadata={"method": _BACKEND, "library_version": _version(),
                      "provenance_id": provenance_id},
        ))
    # Assignments: topic membership per document (probability when available)
    for index, (doc_index, tid) in enumerate(zip(range(len(docs)), topics)):
        if tid == -1:
            continue
        probability = None
        if probs is not None:
            try:
                probability = float(probs[doc_index][tid]) if hasattr(probs[doc_index], "__len__") else float(probs[doc_index])
            except (TypeError, IndexError):
                probability = None
        result.assignments.append(TopicAssignment(
            target_id=f"document_{doc_index}", topic_id=f"bertopic_{tid}",
            score=probability, confidence=None,  # cluster score != theoretical confidence
            provenance_id=provenance_id, review_status="model_proposed"))
    if timestamps:
        result.model_info["topics_over_time_available"] = True
    return result