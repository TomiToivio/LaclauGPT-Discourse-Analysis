# -*- coding: utf-8 -*-
"""LaclauGPT Data Model v0 — the canonical social/text data model.

Philosophy (borrowed, not invented):
- DNA (Leifeld): the STATEMENT is the atomic unit; networks are projections.
- Wikidata: relations carry qualifiers + references (evidence).
- W3C Web Annotation: analytical claims point at exact text spans.
- PROV-O: every analytical object knows what generated it.
- ActivityStreams 2.0: social actors/objects/activities types.
- UIMA CAS: annotations are typed spans (begin/end/features).
- Neo4j property-graph: a PROJECTION, never the storage model.

Storage: observations and assertions in tables (SQLite now, Parquet for
bulk); graphs are generated views via projections.py. Theory stays OUT
of the ontology: nodal_point / empty_signifier are AnalysisResults,
not node types (protection against LLM theory-forcing, paper §3.4).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── enums ────────────────────────────────────────────────────────────

class DocumentType(str, Enum):
    POST = "post"                # social media post (AS2 Object)
    ARTICLE = "article"
    COMMENT = "comment"
    TRANSCRIPT = "transcript"
    VIDEO = "video"
    IMAGE = "image"
    MANIFESTO = "manifesto"
    SPEECH = "speech"
    OTHER = "other"


class ActorType(str, Enum):
    PERSON = "person"            # AS2 Person
    ORGANIZATION = "organization"  # AS2 Organization
    GROUP = "group"              # AS2 Group
    ACCOUNT = "account"          # platform account
    SOFTWARE = "software"        # AS2 Application (bots, LLM agents)
    MOVEMENT = "movement"


class AnnotationType(str, Enum):
    PERSON = "person"            # UIMA-style named-entity spans
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


# ── identity helpers ─────────────────────────────────────────────────

def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(*parts: str) -> str:
    """Stable content hash for dedup (same text + same span = same object)."""
    return hashlib.sha1("\x00".join(parts).encode()).hexdigest()[:16]


# ── 1. Document ──────────────────────────────────────────────────────

class Document(BaseModel):
    """Anything observed. ActivityStreams-flavoured; platform fields go
    into metadata so we never fork per-platform document types."""
    id: str = Field(default_factory=lambda: _id("doc"))
    type: DocumentType = DocumentType.POST
    text: str = ""
    author_id: str | None = None
    published_at: datetime | None = None
    source: str | None = None            # platform/corpus name
    url: str | None = None
    parent_id: str | None = None         # inReplyTo (thread structure)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── 2. Actor ─────────────────────────────────────────────────────────

class Actor(BaseModel):
    id: str = Field(default_factory=lambda: _id("act"))
    type: ActorType = ActorType.PERSON
    name: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


# ── 3. Concept ───────────────────────────────────────────────────────

class Concept(BaseModel):
    """Theory-LIGHT: a concept is a concept. Nodal point / empty
    signifier / topic hub are AnalysisResults, never subtypes."""
    id: str = Field(default_factory=lambda: _id("con"))
    label: str
    description: str = ""
    aliases: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


# ── 4. Annotation (UIMA-style typed span; W3C Web Annotation evidence) ─

class Annotation(BaseModel):
    id: str = Field(default_factory=lambda: _id("ann"))
    document_id: str
    start: int                      # TextPositionSelector
    end: int
    type: AnnotationType = AnnotationType.OTHER
    value: str = ""                 # surface form or coded value
    confidence: float = 1.0
    analysis_run_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


# ── 5. Statement (the DNA killer primitive) ──────────────────────────

class Statement(BaseModel):
    """Actor + concept + qualifier + time + evidence. Networks derive
    from these. Wikidata-style: qualifiers/references ride ON the
    statement, not on the entities."""
    id: str = Field(default_factory=lambda: _id("stm"))
    document_id: str
    actor_id: str | None = None     # who (may be unknown → None)
    concept_id: str                 # what
    stance: Stance = Stance.UNCLEAR
    stance_score: float | None = None   # continuous -1..1
    timestamp: datetime | None = None
    evidence_span: tuple[int, int] | None = None  # (start, end) in document
    confidence: float = 1.0
    qualifiers: dict[str, Any] = Field(default_factory=dict)  # modality, context...
    analysis_run_id: str | None = None


# ── 6. Relation (generic typed edge with evidence) ───────────────────

RelationType = Literal[
    "articulates", "co_occurs", "semantically_associated",
    "replies_to", "reposts", "mentions", "member_of",
    "supports", "opposes", "agrees_with", "associated_with",
    "uses_signifier", "equivalent_to", "opposite_of",
    "derived_from",  # provenance edges land here too
]


class Relation(BaseModel):
    id: str = Field(default_factory=lambda: _id("rel"))
    source_id: str
    target_id: str
    type: RelationType
    weight: float = 1.0
    polarity: float | None = None   # -1..1 where meaningful
    timestamp: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)  # annotation/statement ids
    analysis_run_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


# ── 7. AnalysisRun (provenance; PROV-O Activity) ─────────────────────

class AnalysisRun(BaseModel):
    """PROV-O: used (model, prompt), wasGeneratedBy (this run), 
    wasAttributedTo (software + researcher)."""
    id: str = Field(default_factory=lambda: _id("run"))
    method: str = "laclaugpt"
    model: str | None = None            # e.g. gemma4:e4b
    model_version: str | None = None
    prompt_id: str | None = None        # prompt version reference
    parameters: dict[str, Any] = Field(default_factory=dict)
    software_version: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    operator: str | None = None         # who ran it
    notes: str = ""


# ── AnalysisResult: interpretations as versioned layer ───────────────

ClassificationType = Literal[
    "nodal_point", "empty_signifier_candidate", "floating_signifier",
    "topic_hub", "high_betweenness_signifier", "discourse_coalition",
    "hegemonic_articulation", "other",
]


class AnalysisResult(BaseModel):
    """The Laclaudian reading lives HERE, versioned and falsifiable —
    not in the ontology. Another method may classify the same concept
    differently; both results coexist."""
    id: str = Field(default_factory=lambda: _id("res"))
    subject_id: str                    # concept/signifier/actor id
    classification: ClassificationType
    score: float | None = None
    method: str = "laclaugpt"
    analysis_run_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)  # statements/relations
    timestamp: datetime = Field(default_factory=datetime.now)
    notes: str = ""
