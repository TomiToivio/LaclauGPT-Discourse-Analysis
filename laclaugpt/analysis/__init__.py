"""Analysis-library interfaces: one abstraction per analytical role.

LaclauGPT never depends on spaCy/BERTopic/Gensim/Transformers/sklearn/
statsmodels APIs directly — it depends on these protocols. Every backend
degrades gracefully: importing this package never requires the heavy
libraries, and each backend reports availability honestly.

Methodological boundary (paper §3.4): these layers produce descriptive
features, candidate structures, retrieval support and validation evidence.
They never decide theoretical codes (articulation, equivalence, nodal
point, hegemony, affective investment) — those remain evidence-bearing,
provenance-tracked, human-reviewable Laclaudian/Palonen judgements.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol, runtime_checkable

from laclaugpt.model import (EntityMention, Provenance, Representation,
                             Statement, Topic, TopicAssignment)


class BackendUnavailable(RuntimeError):
    """Raised by a backend whose optional library is not installed."""


@dataclass
class NlpDocument:
    """Linguistic features extracted from one representation."""
    representation_id: str
    tokens: list[str] = field(default_factory=list)
    sentences: list[str] = field(default_factory=list)
    lemmas: list[str] = field(default_factory=list)
    pos: list[str] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    mentions: list[EntityMention] = field(default_factory=list)
    language: str | None = None
    backend: str = ""
    model: str = ""          # model name+version for provenance
    provenance_id: str = ""


@dataclass
class EmbeddingResult:
    """One embedding with full provenance identity."""
    item_id: str
    vector: list[float]
    model: str
    model_version: str = ""
    backend: str = ""
    dimensions: int = 0


@dataclass
class TopicModelResult:
    """Topics are CANDIDATES for the canonical Topic registry, never
    discourses. Topic != Discourse is enforced structurally."""
    topics: list[Topic] = field(default_factory=list)
    assignments: list[TopicAssignment] = field(default_factory=list)
    method: str = ""            # bertopic | gensim_lda | sklearn_nmf | ...
    model_info: dict[str, Any] = field(default_factory=dict)
    provenance_id: str = ""


@dataclass
class ClassificationResult:
    label: str
    confidence: float | None
    task: str = ""
    model: str = ""
    model_version: str = ""
    backend: str = ""
    provenance_id: str = ""


@runtime_checkable
class NLPBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def analyze(self, representation: Representation,
                model_name: str | None = None) -> NlpDocument: ...


@runtime_checkable
class EmbeddingBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def embed(self, texts: Iterable[str], *,
              model: str | None = None) -> list[EmbeddingResult]: ...
    def similarity(self, text_a: str, text_b: str, **kwargs) -> float: ...


@runtime_checkable
class TopicModelBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def discover(self, documents: Iterable[str], *,
                 model: str | None = None,
                 timestamps: list[str] | None = None
                 ) -> TopicModelResult: ...


@runtime_checkable
class ClassificationBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def classify(self, text: str, *, task: str, model: str | None = None
                 ) -> ClassificationResult: ...


@runtime_checkable
class StatisticsBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def fit(self, dataset: Any, *, formula: str | None = None,
            method: str = "ols", **options: Any) -> dict[str, Any]: ...