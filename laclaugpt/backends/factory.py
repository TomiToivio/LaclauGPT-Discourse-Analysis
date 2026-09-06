"""Create repository sets from portable runtime profiles."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import os

from .base import Repositories
from .local import (FileAnalysisRepository, FileBlobRepository,
                    FileGraphRepository, FileSourceRepository,
                    InMemoryRepository)
from .services import (ArangoDocumentRepository, ArangoGraphRepository,
                       ChromaVectorRepository, DuckDBAnalyticsRepository,
                       MongoSourceRepository, RedisCacheRepository)


class BackendConfigurationError(RuntimeError):
    pass


def create_repositories(config: dict[str, Any], root: str | Path = ".") -> Repositories:
    """Build available local adapters; reject unavailable services clearly.

    Remote adapters are optional deployment extras.  They are never imported
    merely by loading the canonical model or an offline profile.
    """
    root = Path(root)
    # Accept the composed 2.0 structure. Flat keys remain accepted for direct
    # adapter tests, not as a second configuration source.
    backend = config.get("backends", {})
    runtime = config.get("runtime", {})
    config = {**config,
              "source_backend": backend.get("source", config.get("source_backend")),
              "analysis_backend": backend.get("analysis", config.get("analysis_backend")),
              "graph_backend": backend.get("graph", config.get("graph_backend")),
              "vector_backend": backend.get("vector", config.get("vector_backend")),
              "cache_backend": backend.get("cache", config.get("cache_backend")),
              "analytics_backend": backend.get("analytics", config.get("analytics_backend")),
              "temporary_directory": runtime.get("temporary_directory", config.get("temporary_directory"))}
    configured_temp = config.get("temporary_directory")
    temp = Path(configured_temp) if configured_temp else root / ".laclaugpt" / "tmp"
    temp.mkdir(parents=True, exist_ok=True)
    local = InMemoryRepository()
    source_name = config.get("source_backend", "memory")
    if source_name == "file":
        source = FileSourceRepository(root / "sources.jsonl")
    elif source_name == "memory":
        source = local
    elif source_name in {"mongodb", "mongodb_remote"}:
        source = MongoSourceRepository(_setting(config, "mongodb_uri", "LACLAUGPT_MONGODB_URI"))
    else:
        raise BackendConfigurationError(f"unknown source backend: {source_name}")

    analysis_name = config.get("analysis_backend", "file")
    graph_name = config.get("graph_backend", "memory")
    arango_db = None
    if analysis_name.startswith("arango") or graph_name.startswith("arango"):
        try:
            from arango import ArangoClient
            client = ArangoClient(hosts=_setting(config, "arangodb_url", "LACLAUGPT_ARANGODB_URL"))
            arango_db = client.db(config.get("arangodb_database", "laclaugpt"),
                                  username=_setting(config, "arangodb_user", "LACLAUGPT_ARANGODB_USER"),
                                  password=_setting(config, "arangodb_password", "LACLAUGPT_ARANGODB_PASSWORD"))
        except (ImportError, KeyError) as exc:
            raise BackendConfigurationError(f"cannot configure ArangoDB: {exc}") from exc
    analysis = (FileAnalysisRepository(root / "analysis") if analysis_name == "file"
                else ArangoDocumentRepository(arango_db) if analysis_name.startswith("arango")
                else local)
    graph = (ArangoGraphRepository(arango_db) if graph_name.startswith("arango")
             else FileGraphRepository(root / "graph.json") if graph_name == "snapshot"
             else local)

    vector_name = config.get("vector_backend", "memory")
    if vector_name.startswith("chroma"):
        try:
            import chromadb
            host = os.getenv("LACLAUGPT_CHROMA_HOST")
            client = chromadb.HttpClient(host=host) if host else chromadb.PersistentClient(path=str(root / "chroma"))
            vector = ChromaVectorRepository(client.get_or_create_collection("laclaugpt"))
        except ImportError as exc:
            raise BackendConfigurationError("Chroma backend requires the services extra") from exc
    else:
        vector = local
    cache_name = config.get("cache_backend", "memory")
    if cache_name.startswith("redis"):
        try:
            import redis
            cache = RedisCacheRepository(redis.from_url(_setting(config, "redis_url", "LACLAUGPT_REDIS_URL")))
        except ImportError as exc:
            raise BackendConfigurationError("Redis backend requires the services extra") from exc
    else:
        cache = local
    analytics_name = config.get("analytics_backend", "memory")
    analytics = (DuckDBAnalyticsRepository(str(temp / "analytics.duckdb"))
                 if analytics_name.startswith("duckdb") else local)
    return Repositories(source=source, analysis=analysis, graph=graph,
                        vector=vector, cache=cache, analytics=analytics,
                        blob=FileBlobRepository(root / "blobs"),
                        temporary_directory=temp)


def _setting(config: dict[str, Any], key: str, env: str) -> str:
    value = config.get(key) or os.getenv(env)
    if not value:
        raise BackendConfigurationError(f"missing {key} (or {env})")
    return str(value)
