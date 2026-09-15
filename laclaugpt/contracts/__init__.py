"""Stable public contracts shared by LaclauGPT subsystems.

These interfaces are deliberately small and backend-neutral.  Core subsystems
should depend on contracts like these rather than importing each other's
implementation internals.  The concrete interchange schema remains versioned
in :mod:`laclaugpt_interchange`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence, runtime_checkable

CONTRACT_VERSION = "1.0"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class SourceItem:
    """Normalized collection boundary object before interpretation."""

    document_id: str
    source_platform: str
    source_url: str = ""
    text: str = ""
    media_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = CONTRACT_VERSION


@dataclass(frozen=True, slots=True)
class AnalysisJob:
    """Backend-neutral request for canonical analysis."""

    run_id: str
    document_ids: tuple[str, ...]
    project: str
    arena: str
    machine_profile: str
    execution_profile: str
    config_fingerprint: str = ""
    schema_version: str = CONTRACT_VERSION


@dataclass(frozen=True, slots=True)
class JobEvent:
    """Inspectable lifecycle event suitable for files, DBs, or queues."""

    run_id: str
    state: JobState
    document_id: str = ""
    message: str = ""
    attempt: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = CONTRACT_VERSION


@dataclass(frozen=True, slots=True)
class VisualizationAggregate:
    """Small storage-neutral aggregate consumed by visualization clients."""

    key: str
    label: str
    count: int
    dimensions: Mapping[str, str] = field(default_factory=dict)
    measures: Mapping[str, float] = field(default_factory=dict)
    schema_version: str = CONTRACT_VERSION


@runtime_checkable
class SourceSink(Protocol):
    """Storage-facing boundary used by Collection."""

    def put_source_items(self, items: Iterable[SourceItem]) -> int: ...


@runtime_checkable
class AnalysisRepository(Protocol):
    """Minimal storage boundary used by Analysis."""

    def iter_source_items(self, document_ids: Sequence[str]) -> Iterable[SourceItem]: ...
    def put_analysis_json(self, document_id: str, payload: Mapping[str, Any]) -> None: ...


@runtime_checkable
class AnalysisExecutor(Protocol):
    """Public execution boundary for canonical analysis workers."""

    def run(self, job: AnalysisJob) -> Iterable[JobEvent]: ...


@runtime_checkable
class VisualizationDataSource(Protocol):
    """Read-only boundary so dashboards never need collector/model internals."""

    def aggregates(self, *, project: str, arena: str) -> Iterable[VisualizationAggregate]: ...
    def document_json(self, document_id: str) -> Mapping[str, Any] | None: ...


@runtime_checkable
class ArtifactStore(Protocol):
    """Durable artifact boundary for local files, object stores, or HPC stages."""

    def write_bytes(self, key: str, data: bytes) -> str: ...
    def read_bytes(self, key: str) -> bytes: ...
    def local_path(self, key: str) -> Path | None: ...
