"""Small protocols are the boundary between research logic and storage."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol, runtime_checkable

from laclaugpt.model import SourceItem


@runtime_checkable
class SourceRepository(Protocol):
    def put_source(self, item: SourceItem) -> SourceItem: ...
    def get_source(self, source_id: str) -> SourceItem | None: ...
    def iter_sources(self) -> Iterable[SourceItem]: ...


@runtime_checkable
class AnalysisRepository(Protocol):
    def put(self, kind: str, item: Any) -> Any: ...
    def get(self, kind: str, item_id: str) -> Any | None: ...
    def iter_kind(self, kind: str) -> Iterable[Any]: ...


@runtime_checkable
class GraphRepository(Protocol):
    def add_node(self, node_id: str, **attributes: Any) -> None: ...
    def add_edge(self, source_id: str, target_id: str, **attributes: Any) -> None: ...
    def graph(self, **filters: Any) -> Any: ...


@runtime_checkable
class VectorRepository(Protocol):
    def add_text(self, item_id: str, text: str, metadata: dict[str, Any]) -> None: ...
    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]: ...


@runtime_checkable
class CacheRepository(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None: ...


@runtime_checkable
class AnalyticsRepository(Protocol):
    def execute(self, query: str, parameters: Iterable[Any] = ()) -> Any: ...


@runtime_checkable
class BlobRepository(Protocol):
    def put_bytes(self, key: str, content: bytes) -> str: ...
    def get_bytes(self, key: str) -> bytes: ...


@dataclass
class Repositories:
    source: SourceRepository
    analysis: AnalysisRepository
    graph: GraphRepository
    vector: VectorRepository
    cache: CacheRepository
    analytics: AnalyticsRepository
    blob: BlobRepository
    temporary_directory: Path

