"""Hybrid context memory orchestration and reversible entity resolution."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from laclaugpt.model import MemoryTrust, SourceItem, Statement


def normalized_label(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", value)


@dataclass(frozen=True)
class Resolution:
    canonical_id: str | None
    decision: str
    confidence: float
    candidates: tuple[str, ...] = ()


class CanonicalRegistry:
    """Authoritative codebook with explicit negative merge history."""
    def __init__(self):
        self.records: dict[str, dict[str, Any]] = {}
        self.lookup: dict[tuple[str, str], str] = {}
        self.rejected_merges: set[frozenset[str]] = set()
        self.superseded_ids: dict[str, str] = {}

    def add(self, canonical_id: str, label: str, kind: str,
            aliases: Iterable[str] = (), trust: MemoryTrust = MemoryTrust.EXTRACTED,
            project_id: str | None = None, module: str | None = None,
            **metadata: Any) -> None:
        values = {label, *aliases}
        self.records[canonical_id] = {"id": canonical_id, "label": label,
                                      "kind": kind, "aliases": sorted(values - {label}),
                                      "trust": trust, "project_id": project_id,
                                      "module": module, **metadata}
        for value in values:
            self.lookup[(kind, normalized_label(value))] = canonical_id

    def reject_merge(self, left_id: str, right_id: str) -> None:
        self.rejected_merges.add(frozenset((left_id, right_id)))

    def resolve(self, mention: str, kind: str,
                candidate_provider: Callable[[str, str], Iterable[tuple[str, float]]] | None = None,
                auto_merge_threshold: float = 0.98) -> Resolution:
        exact = self.lookup.get((kind, normalized_label(mention)))
        if exact:
            return Resolution(exact, "reuse", 1.0)
        candidates = tuple(candidate_provider(mention, kind)) if candidate_provider else ()
        allowed = [(cid, score) for cid, score in candidates if cid in self.records]
        if allowed and allowed[0][1] >= auto_merge_threshold:
            # Similarity proposes reuse only when it is extremely high. Any
            # ambiguous/rejected case remains a candidate for human review.
            cid, score = allowed[0]
            return Resolution(cid, "candidate_reuse", score, tuple(c for c, _ in allowed))
        return Resolution(None, "create_candidate", allowed[0][1] if allowed else 0.0,
                          tuple(c for c, _ in allowed))


class EntityResolver:
    def __init__(self, registry: CanonicalRegistry, candidate_provider=None):
        self.registry, self.candidate_provider = registry, candidate_provider

    def resolve(self, mention: str) -> Resolution:
        return self.registry.resolve(mention, "entity", self.candidate_provider)


class TopicResolver(EntityResolver):
    def resolve(self, mention: str) -> Resolution:
        return self.registry.resolve(mention, "topic", self.candidate_provider)


class ConceptResolver(EntityResolver):
    def resolve(self, mention: str) -> Resolution:
        return self.registry.resolve(mention, "concept", self.candidate_provider)


class MemoryTrustModel:
    """Controls how remembered claims may be presented to a model."""
    authoritative = {MemoryTrust.SOURCE_FACT, MemoryTrust.HUMAN_REVIEWED,
                     MemoryTrust.ACCEPTED}

    @classmethod
    def is_authoritative(cls, trust: MemoryTrust | str) -> bool:
        return MemoryTrust(trust) in cls.authoritative

    @classmethod
    def presentation(cls, record: dict[str, Any]) -> dict[str, Any]:
        trust = MemoryTrust(record.get("trust", MemoryTrust.MODEL_PROPOSED))
        return {**record, "authoritative": cls.is_authoritative(trust),
                "warning": None if cls.is_authoritative(trust)
                else "Prior proposal; not an accepted interpretation."}


@dataclass
class ContextBundle:
    source_context: list[Any] = field(default_factory=list)
    entity_context: list[Any] = field(default_factory=list)
    topic_context: list[Any] = field(default_factory=list)
    graph_context: list[Any] = field(default_factory=list)
    vector_context: list[Any] = field(default_factory=list)
    temporal_context: list[Any] = field(default_factory=list)
    reviewed_context: list[Any] = field(default_factory=list)
    rejected_context: list[Any] = field(default_factory=list)


class ContextBuilder:
    """Single bounded gateway for context supplied to an analysis model."""
    def __init__(self, repositories, registry: CanonicalRegistry, max_items: int = 20,
                 project_id: str | None = None,
                 enabled_modules: Iterable[str] | None = None):
        self.repositories = repositories
        self.registry = registry
        self.max_items = max_items
        self.project_id = project_id
        self.enabled_modules = set(enabled_modules or ())

    def _allowed(self, record: dict[str, Any]) -> bool:
        same_project = record.get("project_id") in {None, self.project_id}
        module = record.get("module")
        module_enabled = module is None or module in self.enabled_modules
        return same_project and module_enabled

    def build(self, source: SourceItem, statement: Statement | None,
              task: str) -> ContextBundle:
        sources = [item for item in self.repositories.source.iter_sources()
                   if item.source_id == source.parent_source_id or
                   (source.parent_source_id and item.parent_source_id == source.parent_source_id)]
        entities = [r for r in self.registry.records.values()
                    if r["kind"] == "entity" and self._allowed(r)]
        topics = [r for r in self.registry.records.values()
                  if r["kind"] == "topic" and self._allowed(r)]
        query = " ".join(filter(None, (task, statement.text if statement else source.raw_text)))
        vector = self.repositories.vector.search(query, limit=self.max_items)
        reviewed = [MemoryTrustModel.presentation(r) for r in self.registry.records.values()
                    if self._allowed(r) and
                    r.get("trust") in {MemoryTrust.HUMAN_REVIEWED, MemoryTrust.ACCEPTED}]
        rejected = [sorted(pair) for pair in self.registry.rejected_merges]
        return ContextBundle(
            source_context=sources[:self.max_items],
            entity_context=entities[:self.max_items],
            topic_context=topics[:self.max_items],
            vector_context=vector[:self.max_items],
            reviewed_context=reviewed[:self.max_items],
            rejected_context=rejected[:self.max_items],
        )
