"""Canonical, storage-neutral LaclauGPT 2.0 domain model.

Computational observations and Laclaudian interpretations are intentionally
different object types.  Interpretive objects carry evidence, provenance and
review state; no storage backend is mentioned in this module.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class ReviewStatus(str, Enum):
    PROPOSED = "proposed"
    MODEL_PROPOSED = "model_proposed"
    HUMAN_REVIEWED = "human_reviewed"
    ACCEPTED = "accepted"
    MODIFIED = "modified"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class MemoryTrust(str, Enum):
    SOURCE_FACT = "SOURCE_FACT"
    EXTRACTED = "EXTRACTED"
    MODEL_PROPOSED = "MODEL_PROPOSED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class Reviewed(Model):
    run_id: str | None = None
    review_status: ReviewStatus = ReviewStatus.PROPOSED
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None


class Provenance(Model):
    provenance_id: str = Field(default_factory=lambda: new_id("prov"))
    method: str
    model: str | None = None
    model_version: str | None = None
    prompt_id: str | None = None
    prompt_version: str | None = None
    pipeline_version: str | None = None
    imported_from: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    confidence: float | None = Field(default=None, ge=0, le=1)


class SourceItem(Model):
    source_id: str = Field(default_factory=lambda: new_id("src"))
    source_url: str | None = None
    normalized_source_url: str | None = None
    platform: str | None = None
    source_type: str
    native_id: str | None = None
    title: str | None = None
    author_text: str | None = None
    published_at: datetime | None = None
    collected_at: datetime | None = None
    language: str | None = None
    raw_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    legacy_fields: dict[str, Any] = Field(default_factory=dict)
    parent_source_id: str | None = None


class IngestionRecord(Model):
    ingestion_id: str = Field(default_factory=lambda: new_id("ing"))
    source_id: str
    collector: str
    collector_version: str | None = None
    collected_at: datetime = Field(default_factory=utcnow)
    dataset_id: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    raw_payload_ref: str | None = None
    provenance_id: str


class MediaAsset(Model):
    media_id: str = Field(default_factory=lambda: new_id("media"))
    source_id: str
    media_type: str
    uri: str | None = None
    local_path: str | None = None
    mime_type: str | None = None
    duration: float | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Representation(Model):
    representation_id: str = Field(default_factory=lambda: new_id("rep"))
    source_id: str
    media_id: str | None = None
    representation_type: str
    text: str | None = None
    language: str | None = None
    model: str | None = None
    model_version: str | None = None
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance_id: str
    run_id: str | None = None


class AttributionType(str, Enum):
    AUTHOR = "author"
    SPEAKER = "speaker"
    QUOTED = "quoted"
    REPORTED = "reported"
    HYPOTHETICAL = "hypothetical"
    IRONIC = "ironic"
    UNCLEAR = "unclear"


class Statement(Model):
    statement_id: str = Field(default_factory=lambda: new_id("stm"))
    source_id: str
    representation_id: str
    speaker_actor_id: str | None = None
    text: str
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, ge=0)
    attribution_type: AttributionType = AttributionType.UNCLEAR
    confidence: float | None = Field(default=None, ge=0, le=1)
    run_id: str | None = None

    @model_validator(mode="after")
    def ordered_spans(self):
        for start, end in ((self.start_offset, self.end_offset),
                           (self.start_time, self.end_time)):
            if start is not None and end is not None and end < start:
                raise ValueError("span end must not precede span start")
        return self


class EvidenceSpan(Model):
    evidence_id: str = Field(default_factory=lambda: new_id("ev"))
    source_id: str
    representation_id: str
    statement_id: str | None = None
    exact_text: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, ge=0)
    frame_number: int | None = Field(default=None, ge=0)
    bounding_box: dict[str, float] | None = None


class Actor(Model):
    actor_id: str = Field(default_factory=lambda: new_id("act"))
    canonical_name: str
    actor_type: str
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Affiliation(Model):
    actor_id: str
    organization_id: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class EntityMention(Model):
    mention_id: str = Field(default_factory=lambda: new_id("mention"))
    representation_id: str
    statement_id: str | None = None
    surface_form: str
    spacy_label: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    candidate_entity_id: str | None = None
    # spaCy label → canonical CANDIDATE type (person/organization/place/
    # event/...). The mention type is never the canonical entity; Context
    # Memory resolution decides what the mention maps to.
    candidate_entity_type: str | None = None
    resolution_confidence: float | None = Field(default=None, ge=0, le=1)
    run_id: str | None = None


class Entity(Model):
    entity_id: str = Field(default_factory=lambda: new_id("ent"))
    canonical_name: str
    entity_type: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Place(Entity):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    geocoding_source: str | None = None
    geocoding_confidence: float | None = Field(default=None, ge=0, le=1)
    country: str | None = None
    region: str | None = None
    locality: str | None = None


class Event(Entity):
    start_date: datetime | None = None
    end_date: datetime | None = None
    date_precision: str | None = None
    place_ids: list[str] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Topic(Model):
    topic_id: str = Field(default_factory=lambda: new_id("topic"))
    canonical_label: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None


class TopicAssignment(Model):
    target_id: str
    topic_id: str
    score: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance_id: str
    run_id: str | None = None


class SentimentAnnotation(Model):
    sentiment_id: str = Field(default_factory=lambda: new_id("sent"))
    target_text: str
    target_entity_id: str | None = None
    target_concept_id: str | None = None
    sentiment_type: str
    statement_id: str | None = None
    source_id: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance_id: str
    run_id: str | None = None


class Concept(Model):
    concept_id: str = Field(default_factory=lambda: new_id("con"))
    canonical_label: str
    concept_type: str = "other"
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    entity_ref: str | None = None
    topic_ref: str | None = None


class DiscursiveRelationType(str, Enum):
    ARTICULATES = "ARTICULATES"
    EQUIVALENT_TO = "EQUIVALENT_TO"
    DIFFERENTIATED_FROM = "DIFFERENTIATED_FROM"
    ANTAGONISTIC_TO = "ANTAGONISTIC_TO"
    REPRESENTS = "REPRESENTS"
    IDENTIFIES_WITH = "IDENTIFIES_WITH"
    EXCLUDES = "EXCLUDES"
    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"


class ComputationalRelationType(str, Enum):
    CO_OCCURS_WITH = "CO_OCCURS_WITH"
    SEMANTICALLY_SIMILAR_TO = "SEMANTICALLY_SIMILAR_TO"
    SAME_TOPIC_AS = "SAME_TOPIC_AS"
    MENTIONS = "MENTIONS"


class Articulation(Reviewed):
    articulation_id: str = Field(default_factory=lambda: new_id("art"))
    source_id: str
    statement_id: str
    actor_id: str | None = None
    source_concept_id: str
    target_concept_id: str
    relation_type: DiscursiveRelationType = DiscursiveRelationType.ARTICULATES
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    provenance_id: str


class DiscursiveRelation(Reviewed):
    relation_id: str = Field(default_factory=lambda: new_id("drel"))
    source_concept_id: str
    target_concept_id: str
    relation_type: DiscursiveRelationType
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    provenance_id: str


class AnalyticRelation(Model):
    relation_id: str = Field(default_factory=lambda: new_id("arel"))
    source_id: str
    target_id: str
    relation_type: ComputationalRelationType
    score: float | None = None
    provenance_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None


class Discourse(Reviewed):
    discourse_id: str = Field(default_factory=lambda: new_id("disc"))
    label: str | None = None
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class DiscursiveRole(str, Enum):
    ELEMENT = "ELEMENT"
    MOMENT = "MOMENT"
    NODAL_POINT = "NODAL_POINT"
    FLOATING_SIGNIFIER = "FLOATING_SIGNIFIER"
    EMPTY_SIGNIFIER = "EMPTY_SIGNIFIER"


class DiscursiveRoleAssignment(Reviewed):
    role_assignment_id: str = Field(default_factory=lambda: new_id("role"))
    concept_id: str
    discourse_id: str
    role: DiscursiveRole
    start_time: datetime | None = None
    end_time: datetime | None = None
    score: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    provenance_id: str


class EquivalenceChain(Model):
    chain_id: str = Field(default_factory=lambda: new_id("chain"))
    discourse_id: str
    label: str | None = None
    collective_subject_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class ChainMembership(Model):
    chain_id: str
    concept_id: str
    strength: float | None = None
    evidence_ids: list[str] = Field(min_length=1)


class CollectiveSubject(Model):
    subject_id: str = Field(default_factory=lambda: new_id("subject"))
    label: str
    discourse_id: str
    aliases: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)


class AntagonisticFrontier(Model):
    frontier_id: str = Field(default_factory=lambda: new_id("frontier"))
    discourse_id: str
    us_subject_id: str | None = None
    us_chain_id: str | None = None
    other_subject_id: str | None = None
    other_chain_id: str | None = None
    strength: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    start_time: datetime | None = None
    end_time: datetime | None = None


class Affect(Model):
    affect_id: str = Field(default_factory=lambda: new_id("affect"))
    label: str
    valence: float | None = Field(default=None, ge=-1, le=1)
    arousal: float | None = Field(default=None, ge=0, le=1)


class AffectiveInvestment(Model):
    investment_id: str = Field(default_factory=lambda: new_id("investment"))
    affect_id: str
    target_type: str
    target_id: str
    discourse_id: str | None = None
    intensity: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    run_id: str | None = None


class PopulistConfiguration(Reviewed):
    configuration_id: str = Field(default_factory=lambda: new_id("pop"))
    discourse_id: str
    us_subject_id: str
    us_chain_id: str | None = None
    frontier_id: str
    us_affective_investment_ids: list[str] = Field(min_length=1)
    frontier_affective_investment_ids: list[str] = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    provenance_id: str


class HegemonyAssessment(Model):
    assessment_id: str = Field(default_factory=lambda: new_id("hegemony"))
    discourse_id: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: ReviewStatus = ReviewStatus.MODEL_PROPOSED
    frequency_metric: float | None = None
    actor_coverage_metric: float | None = None
    institutional_uptake_metric: float | None = None
    stability_metric: float | None = None
    contestation_metric: float | None = None
    interpretation: str | None = None
    evidence_ids: list[str] = Field(min_length=1)
    provenance_id: str
    run_id: str | None = None


class ImaginaryElementType(str, Enum):
    FUTURE_VISION = "future_vision"
    DESIRED_SOCIAL_ORDER = "desired_social_order"
    FEARED_FUTURE = "feared_future"
    PROBLEM_DEFINITION = "problem_definition"
    BENEFICIARY = "beneficiary"
    AFFECTED_GROUP = "affected_group"
    AUTHORISED_ACTOR = "authorised_actor"
    TECHNOLOGY = "technology"
    INSTITUTION = "institution"
    POLICY = "policy"
    ECONOMIC_MODEL = "economic_model"
    INFRASTRUCTURE = "infrastructure"
    VALUE = "value"


class SociotechnicalImaginary(Reviewed):
    """A collective technology-linked social vision, not a prediction/topic."""
    imaginary_id: str = Field(default_factory=lambda: new_id("imaginary"))
    label: str
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    provenance_id: str
    collective_articulation_supported: bool = False

    @model_validator(mode="after")
    def requires_collective_articulation(self):
        if not self.collective_articulation_supported:
            raise ValueError(
                "an imaginary requires collective articulation; a prediction or topic mention is insufficient")
        return self


class ImaginaryElement(Reviewed):
    element_id: str = Field(default_factory=lambda: new_id("imaginary_element"))
    imaginary_id: str
    element_type: ImaginaryElementType
    target_id: str | None = None
    text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    provenance_id: str

    @model_validator(mode="after")
    def has_target_or_text(self):
        if not self.target_id and not self.text:
            raise ValueError("imaginary element needs target_id or text")
        return self


class ImaginaryRelationType(str, Enum):
    ARTICULATES_IMAGINARY = "ARTICULATES_IMAGINARY"
    PROMOTES = "PROMOTES"
    PART_OF_IMAGINARY = "PART_OF_IMAGINARY"


class ImaginaryRelation(Reviewed):
    relation_id: str = Field(default_factory=lambda: new_id("imaginary_relation"))
    source_id: str
    source_type: str
    imaginary_id: str
    relation_type: ImaginaryRelationType
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1)
    provenance_id: str


class Annotation(Model):
    annotation_id: str = Field(default_factory=lambda: new_id("ann"))
    target_type: str
    target_id: str
    annotation_type: str
    value: dict[str, Any] | str | float | bool
    schema_name: str | None = Field(default=None, alias="schema")
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance_id: str
    run_id: str | None = None


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Run(Model):
    run_id: str = Field(default_factory=lambda: new_id("run"))
    project: str
    machine: str
    execution_mode: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: RunStatus = RunStatus.PENDING
    hostname: str | None = None
    slurm_job_id: str | None = None
    parent_run_id: str | None = None
    configuration_snapshot: dict[str, Any]
    pipeline_version: str


class ExternalRelation(Model):
    relation_id: str = Field(default_factory=lambda: new_id("external"))
    source_id: str
    target_id: str
    relation_type: str
    schema_name: str = Field(alias="schema")
    metadata: dict[str, Any] = Field(default_factory=dict)


CANONICAL_TYPES = (
    SourceItem, IngestionRecord, MediaAsset, Representation, Statement,
    EvidenceSpan, Actor, Affiliation, EntityMention, Entity, Place, Event,
    Topic, TopicAssignment, SentimentAnnotation, Concept, Articulation,
    DiscursiveRelation, AnalyticRelation, Discourse, DiscursiveRoleAssignment,
    EquivalenceChain, ChainMembership, CollectiveSubject,
    AntagonisticFrontier, Affect, AffectiveInvestment, PopulistConfiguration,
    HegemonyAssessment, SociotechnicalImaginary, ImaginaryElement,
    ImaginaryRelation, Provenance, Annotation, Run, ExternalRelation,
)
