"""Adapters for optional persistent services.

Clients may be injected for tests. Imports happen in constructors, keeping the
offline Roihu profile free of database dependencies.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

import networkx as nx

from laclaugpt.identity import normalize_url
from laclaugpt.model import SourceItem


class MongoSourceRepository:
    def __init__(self, uri: str, database: str = "laclaugpt",
                 collection: str = "source_items", client=None):
        if client is None:
            from pymongo import MongoClient
            client = MongoClient(uri)
        self.collection = client[database][collection]
        self.collection.create_index("normalized_source_url", unique=True,
                                     sparse=True, name="unique_source_url")
        self.collection.create_index([("platform", 1), ("native_id", 1)],
                                     unique=True, sparse=True, name="unique_native_source")

    def put_source(self, item: SourceItem) -> SourceItem:
        if item.source_url and not item.normalized_source_url:
            item = item.model_copy(update={"normalized_source_url": normalize_url(item.source_url)})
        self.collection.replace_one({"source_id": item.source_id},
                                    item.model_dump(mode="json"), upsert=True)
        return item

    def get_source(self, source_id: str) -> SourceItem | None:
        row = self.collection.find_one({"source_id": source_id}, {"_id": 0})
        return SourceItem.model_validate(row) if row else None

    def iter_sources(self) -> Iterable[SourceItem]:
        for row in self.collection.find({}, {"_id": 0}):
            yield SourceItem.model_validate(row)


class ArangoDocumentRepository:
    def __init__(self, database, collection: str = "analysis_objects"):
        self.database = database
        if not database.has_collection(collection):
            database.create_collection(collection)
        self.collection = database.collection(collection)

    def put(self, kind: str, item: Any) -> Any:
        payload = item.model_dump(mode="json", by_alias=True)
        item_id = next(str(v) for k, v in payload.items() if k.endswith("_id") and v)
        self.collection.insert({"_key": item_id.replace("/", "_"), "kind": kind,
                                "payload": payload}, overwrite=True)
        return item

    def get(self, kind: str, item_id: str) -> Any | None:
        row = self.collection.get(item_id.replace("/", "_"))
        return row.get("payload") if row and row.get("kind") == kind else None

    def iter_kind(self, kind: str):
        cursor = self.database.aql.execute(
            "FOR x IN @@collection FILTER x.kind == @kind RETURN x.payload",
            bind_vars={"@collection": self.collection.name, "kind": kind})
        yield from cursor


class ArangoGraphRepository:
    def __init__(self, database, nodes: str = "graph_nodes", edges: str = "graph_edges"):
        self.database = database
        for name, edge in ((nodes, False), (edges, True)):
            if not database.has_collection(name):
                database.create_collection(name, edge=edge)
        self.nodes = database.collection(nodes)
        self.edges = database.collection(edges)

    @staticmethod
    def _key(value: str) -> str:
        return value.replace("/", "_")

    def add_node(self, node_id: str, **attributes: Any) -> None:
        self.nodes.insert({"_key": self._key(node_id), "node_id": node_id, **attributes}, overwrite=True)

    def add_edge(self, source_id: str, target_id: str, **attributes: Any) -> None:
        key = f"{self._key(source_id)}_{self._key(target_id)}_{self.edges.count()}"
        self.edges.insert({"_key": key, "_from": f"{self.nodes.name}/{self._key(source_id)}",
                           "_to": f"{self.nodes.name}/{self._key(target_id)}", **attributes})

    def graph(self, **filters: Any):
        graph = nx.MultiDiGraph()
        for node in self.nodes.all():
            graph.add_node(node["node_id"], **{k: v for k, v in node.items() if not k.startswith("_") and k != "node_id"})
        for edge in self.edges.all():
            attrs = {k: v for k, v in edge.items() if not k.startswith("_")}
            if filters.get("relation_type") in (None, attrs.get("relation_type")):
                source = self.nodes.get(edge["_from"].split("/", 1)[1])["node_id"]
                target = self.nodes.get(edge["_to"].split("/", 1)[1])["node_id"]
                graph.add_edge(source, target, **attrs)
        return graph


class ChromaVectorRepository:
    def __init__(self, collection):
        self.collection = collection

    def add_text(self, item_id: str, text: str, metadata: dict[str, Any]) -> None:
        self.collection.upsert(ids=[item_id], documents=[text], metadatas=[metadata])

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        result = self.collection.query(query_texts=[query], n_results=limit)
        return [{"id": item_id, "text": text, "metadata": meta, "distance": distance}
                for item_id, text, meta, distance in zip(
                    result["ids"][0], result["documents"][0], result["metadatas"][0],
                    result.get("distances", [[None] * len(result["ids"][0])])[0])]


class RedisCacheRepository:
    def __init__(self, client):
        self.client = client

    def get(self, key: str) -> Any | None:
        value = self.client.get(key)
        return json.loads(value) if value is not None else None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self.client.set(key, json.dumps(value, ensure_ascii=False), ex=ttl_seconds)


class DuckDBAnalyticsRepository:
    def __init__(self, database: str = ":memory:", connection=None):
        if connection is None:
            import duckdb
            connection = duckdb.connect(database)
        self.connection = connection

    def execute(self, query: str, parameters: Iterable[Any] = ()) -> Any:
        return self.connection.execute(query, list(parameters))

