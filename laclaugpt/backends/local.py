"""Dependency-light local backends used in tests and offline HPC jobs."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

import networkx as nx
from pydantic import BaseModel

from laclaugpt.identity import normalize_url
from laclaugpt.model import CANONICAL_TYPES, SourceItem

_TYPE_BY_NAME = {t.__name__: t for t in CANONICAL_TYPES}


def _id_of(item: Any) -> str:
    for name in type(item).model_fields:
        if name.endswith("_id") and getattr(item, name, None):
            return str(getattr(item, name))
    raise ValueError(f"{type(item).__name__} has no identifier")


class InMemoryRepository:
    """Implements source, analysis, vector, cache, graph and analytics ports."""
    def __init__(self):
        self.items: dict[str, dict[str, Any]] = {}
        self.urls: dict[str, str] = {}
        self.native_ids: dict[tuple[str, str], str] = {}
        self._graph = nx.MultiDiGraph()
        self._cache: dict[str, tuple[float | None, Any]] = {}
        self._texts: dict[str, tuple[str, dict[str, Any]]] = {}
        self._sql = sqlite3.connect(":memory:")

    def put_source(self, item: SourceItem) -> SourceItem:
        if item.source_url:
            normalized = item.normalized_source_url or normalize_url(item.source_url)
            existing = self.urls.get(normalized)
            if existing and existing != item.source_id:
                raise ValueError(f"duplicate normalized source URL: {normalized}")
            item = item.model_copy(update={"normalized_source_url": normalized})
            self.urls[normalized] = item.source_id
        if item.platform and item.native_id:
            key = (item.platform.casefold(), item.native_id)
            existing = self.native_ids.get(key)
            if existing and existing != item.source_id:
                raise ValueError(f"duplicate platform/native_id: {key}")
            self.native_ids[key] = item.source_id
        self.items.setdefault("SourceItem", {})[item.source_id] = item
        return item

    def get_source(self, source_id: str) -> SourceItem | None:
        return self.items.get("SourceItem", {}).get(source_id)

    def iter_sources(self) -> Iterable[SourceItem]:
        return self.items.get("SourceItem", {}).values()

    def put(self, kind: str, item: Any) -> Any:
        self.items.setdefault(kind, {})[_id_of(item)] = item
        return item

    def get(self, kind: str, item_id: str) -> Any | None:
        return self.items.get(kind, {}).get(item_id)

    def iter_kind(self, kind: str) -> Iterable[Any]:
        return self.items.get(kind, {}).values()

    def add_node(self, node_id: str, **attributes: Any) -> None:
        self._graph.add_node(node_id, **attributes)

    def add_edge(self, source_id: str, target_id: str, **attributes: Any) -> None:
        self._graph.add_edge(source_id, target_id, **attributes)

    def graph(self, **filters: Any):
        if not filters:
            return self._graph.copy()
        edge_type = filters.get("relation_type")
        graph = nx.MultiDiGraph()
        for source, target, attrs in self._graph.edges(data=True):
            if edge_type is None or attrs.get("relation_type") == edge_type:
                graph.add_edge(source, target, **attrs)
        for node in graph:
            graph.nodes[node].update(self._graph.nodes[node])
        return graph

    def add_text(self, item_id: str, text: str, metadata: dict[str, Any]) -> None:
        self._texts[item_id] = (text, metadata)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        terms = set(query.casefold().split())
        ranked = []
        for item_id, (body, metadata) in self._texts.items():
            score = len(terms & set(body.casefold().split()))
            if score:
                ranked.append({"id": item_id, "text": body,
                               "metadata": metadata, "score": float(score)})
        return sorted(ranked, key=lambda row: (-row["score"], row["id"]))[:limit]

    def get(self, key: str, item_id: str | None = None) -> Any | None:  # cache + analysis
        if item_id is not None:
            return self.items.get(key, {}).get(item_id)
        hit = self._cache.get(key)
        if not hit:
            return None
        expires, value = hit
        if expires is not None and expires <= time.time():
            self._cache.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires = None if ttl_seconds is None else time.time() + ttl_seconds
        self._cache[key] = (expires, value)

    def execute(self, query: str, parameters: Iterable[Any] = ()) -> Any:
        return self._sql.execute(query, tuple(parameters))


class FileSourceRepository(InMemoryRepository):
    """Append-only JSONL source repository with in-process unique indexes."""
    def __init__(self, path: str | Path):
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    super().put_source(SourceItem.model_validate_json(line))

    def put_source(self, item: SourceItem) -> SourceItem:
        existing = self.get_source(item.source_id)
        stored = super().put_source(item)
        if existing is None:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(stored.model_dump_json(by_alias=True) + "\n")
        return stored


class FileAnalysisRepository(InMemoryRepository):
    def __init__(self, directory: str | Path):
        super().__init__()
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        for path in self.directory.glob("*.jsonl"):
            model_type = _TYPE_BY_NAME.get(path.stem)
            if model_type:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        super().put(path.stem, model_type.model_validate_json(line))

    def put(self, kind: str, item: Any) -> Any:
        result = super().put(kind, item)
        with (self.directory / f"{kind}.jsonl").open("a", encoding="utf-8") as handle:
            payload = item.model_dump(mode="json", by_alias=True) if isinstance(item, BaseModel) else item
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return result


class FileGraphRepository(InMemoryRepository):
    """NetworkX graph persisted as a portable node-link JSON snapshot."""
    def __init__(self, path: str | Path):
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self._graph = nx.node_link_graph(json.loads(self.path.read_text(encoding="utf-8")),
                                             edges="edges")

    def _flush(self) -> None:
        self.path.write_text(json.dumps(nx.node_link_data(self._graph, edges="edges"),
                                        ensure_ascii=False, default=str), encoding="utf-8")

    def add_node(self, node_id: str, **attributes: Any) -> None:
        super().add_node(node_id, **attributes); self._flush()

    def add_edge(self, source_id: str, target_id: str, **attributes: Any) -> None:
        super().add_edge(source_id, target_id, **attributes); self._flush()


class FileBlobRepository:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError("blob key escapes repository root")
        return path

    def put_bytes(self, key: str, content: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()
