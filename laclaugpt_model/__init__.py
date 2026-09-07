# -*- coding: utf-8 -*-
"""Frozen compatibility model for pre-2.0 LaclauGPT code.

This package is NOT the canonical model for new code. Use::

    from laclaugpt.model import ...

The classes below are retained so old SQLite/Parquet/projection workflows can be
read and migrated without a flag day. New adapters and integrations must target
``laclaugpt.model``. The compatibility package is frozen: no new domain concepts
should be added here, and it may be removed after all retained projection/store
helpers have canonical replacements.

Theory remains OUT of the ontology here as in the current model: nodal-point,
floating-signifier and empty-signifier readings are analysis results, not node
types.
"""
from __future__ import annotations

import hashlib
import json
import uuid
import warnings
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

__deprecated_since__ = "2.0"
__replacement__ = "laclaugpt.model"
__compatibility_status__ = "frozen"

warnings.warn(
    "laclaugpt_model is a frozen compatibility API; use laclaugpt.model for new code",
    FutureWarning,
    stacklevel=2,
)


class DocumentType(str, Enum):
    POST = "post"
    ARTICLE = "article"
    COMMENT = "comment"
    TRANSCRIPT = "transcript"
    VIDEO = "video"
    IMAGE = "image"
    MANIFESTO = "manifesto"
    SPEECH = "speech"
    OTHER = "other"


class ActorType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    GROUP = "group"
    ACCOUNT = "account"
    SOFTWARE = "software"
    MOVEMENT = "movement"


class AnnotationType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    SENTIMENT = "sentiment"
    FRAME = "frame"
    SIGNIFIER = "signifier"
    OTHER = "other"


class Stance(str, Enum):
    """DNA-style qualifier, coarse buckets plus continuous score."""
    SUPPORT = "support"
    OPPOSE = "oppose"
    NEUTRAL = "neutral"
    UNCLEAR = "unclear"


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(*parts: str) -> str:
    """Stable content hash for dedup (same text + same span = same object)."""
    return hashlib.sha1("\x00".join(parts).encode()).hexdigest()[:16]


class Document(BaseModel):
    """Anything observed. Platform fields stay in metadata."""
    id: str = Field(default_factory=lambda: _id("doc"))
    type: DocumentType = DocumentType.POST
    text: str = ""
    author_id: str | None = None
    published_at: datetime | None = None
    source: str | None = None
    url: str | None = None
    parent_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Actor(BaseModel):
    id: str = Field(default_factory=lambda: _id("act"))
    type: ActorType = ActorType.PERSON
    name: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class Concept(BaseModel):
    """Theory-light concept. Laclaudian roles belong in AnalysisResult."""
    id: str = Field(default_factory=lambda: _id("con"))
    label: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Annotation(BaseModel):
    id: str = Field(default_factory=lambda: _id("ann"))
    document_id: str
    start: int
    end: int
    type: AnnotationType = AnnotationType.OTHER
    value: str = ""
    confidence: float = 1.0
    analysis_run_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class Statement(BaseModel):
    """Actor + concept + qualifier + time + evidence."""
    id: str = Field(default_factory=lambda: _id("stm"))
    document_id: str
    actor_id: str | None = None
    concept_id: str
    stance: Stance = Stance.UNCLEAR
    stance_score: float | None = None
    timestamp: datetime | None = None
    evidence_span: tuple[int, int] | None = None
    confidence: float = 1.0
    qualifiers: dict[str, Any] = Field(default_factory=dict)
    analysis_run_id: str | None = None


RelationType = Literal[
    "articulates", "co_occurs", "semantically_associated",
    "replies_to", "reposts", "mentions", "member_of",
    "supports", "opposes", "agrees_with", "associated_with",
    "uses_signifier", "equivalent_to", "opposite_of", "derived_from",
]


class Relation(BaseModel):
    id: str = Field(default_factory=lambda: _id("rel"))
    source_id: str
    target_id: str
    type: RelationType
    weight: float = 1.0
    polarity: float | None = None
    timestamp: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    analysis_run_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class AnalysisRun(BaseModel):
    id: str = Field(default_factory=lambda: _id("run"))
    method: str = "laclaugpt"
    model: str | None = None
    model_version: str | None = None
    prompt_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    software_version: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    operator: str | None = None
    notes: str = ""


ClassificationType = Literal[
    "nodal_point", "empty_signifier_candidate", "floating_signifier",
    "topic_hub", "high_betweenness_signifier", "discourse_coalition",
    "hegemonic_articulation", "other",
]


class AnalysisResult(BaseModel):
    """Versioned/falsifiable interpretation over an ordinary subject object."""
    id: str = Field(default_factory=lambda: _id("res"))
    subject_id: str
    classification: ClassificationType
    score: float | None = None
    method: str = "laclaugpt"
    analysis_run_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    notes: str = ""
