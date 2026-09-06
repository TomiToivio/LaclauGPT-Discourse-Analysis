"""LaclauGPT canonical models — the academic data model of the paper.

Every Laclaudian concept is a CANDIDATE interpretation carrying evidence,
provenance and review status. Nothing here is an unquestionable fact
produced by a model: model proposal != accepted interpretation.

Conceptual distinctions enforced structurally (paper §3):
    topic != discourse            sentiment != affective investment
    co-occurrence != articulation semantic similarity != equivalence
    negative sentiment != antagonism
    centrality != nodal point     frequency != hegemony
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def new_id(prefix: str) -> str:
    from uuid import uuid4
    return f"{prefix}_{uuid4().hex[:12]}"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


# ── provenance & review (non-negotiable traceability) ────────────────

class ReviewStatus(str, Enum):
    PROPOSED = "proposed"               # pipeline output, nobody has reviewed
    MODEL_PROPOSED = "model_proposed"
    HUMAN_REVIEWED = "human_reviewed"
    ACCEPTED = "accepted"
    MODIFIED = "modified"
    REJECTED = "rejected"


class Provenance(Model):
    """Where an interpretation came from. Every theoretical code carries
    provenance_id; every analysis result carries run_id."""
    provenance_id: str = Field(default_factory=lambda: new_id("prov"))
    method: str                          # "llm" | "human" | "rule" | ...
    model: str | None = None             # e.g. "gemma3:12b"
    model_version: str | None = None
    prompt_version: str | None = None
    pipeline_version: str | None = None
    run_id: str | None = None
    created_at: str = Field(default_factory=utcnow)


class SourceDocument(Model):
    """Input document. LaclauGPT accepts already-collected textual or
    textualized material (source_text, transcript, OCR, frame_description);
    data collection lives outside this core."""
    document_id: str = Field(default_factory=lambda: new_id("doc"))
    text: str
    source_type: str = "source_text"     # source_text|transcript|ocr|frame_description
    language: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSpan(Model):
    """Exact quote anchoring a proposed interpretation to the source."""
    evidence_id: str = Field(default_factory=lambda: new_id("ev"))
    document_id: str
    exact_text: str
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)


class EvidenceLink(Model):
    """The traceability spine: proposed code + exact evidence + provenance
    + review status. Shared by every interpretive output below."""
    document_id: str
    evidence: str                        # exact quote from the document
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    uncertainty: str | None = None       # what could make this wrong
    review_status: ReviewStatus = ReviewStatus.PROPOSED
    provenance_id: str
    run_id: str | None = None


# ── descriptive extraction (candidates, not interpretations) ─────────

class Entity(Model):
    """Named-entity CANDIDATE (LLM- or NLP-proposed). Mention type is
    never the canonical entity; deduplication is Context Memory's job."""
    entity_id: str = Field(default_factory=lambda: new_id("ent"))
    canonical_name: str
    entity_type: str = "other"           # person|organization|place|event|...
    aliases: list[str] = Field(default_factory=list)


class Topic(Model):
    """Descriptive topic CANDIDATE. Topic != Discourse: a topic cluster
    never becomes a discourse without separate theoretical analysis."""
    topic_id: str = Field(default_factory=lambda: new_id("topic"))
    canonical_label: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None


class SentimentAnnotation(Model):
    """Sentiment toward a target. Sentiment != affective investment:
    negativity toward an opponent is not an antagonistic frontier."""
    sentiment_id: str = Field(default_factory=lambda: new_id("sent"))
    target_text: str
    sentiment_type: Literal["positive", "negative", "neutral"]
    document_id: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class Concept(Model):
    """A signifier or issue that articulations connect."""
    concept_id: str = Field(default_factory=lambda: new_id("con"))
    canonical_label: str
    concept_type: str = "signifier"      # signifier|demand|issue|other
    aliases: list[str] = Field(default_factory=list)


# ── Laclau & Mouffe concepts (candidate interpretations) ─────────────

class ArticulationType(str, Enum):
    EQUIVALENCE = "equivalence"
    DIFFERENCE = "difference"
    ANTAGONISM = "antagonism"


class Articulation(EvidenceLink):
    """A relation proposed between two concepts in the document.
    Co-occurrence alone is insufficient: the relation, its direction and
    the attributed speaker must be evidenced in the text."""
    articulation_id: str = Field(default_factory=lambda: new_id("art"))
    source_concept: str                  # signifier label as used in text
    target_concept: str
    relation_type: ArticulationType


class SignifierRole(str, Enum):
    NODAL_POINT_CANDIDATE = "nodal_point_candidate"
    FLOATING_SIGNIFIER_CANDIDATE = "floating_signifier_candidate"
    EMPTY_SIGNIFIER_CANDIDATE = "empty_signifier_candidate"


class SignifierRoleAssignment(EvidenceLink):
    """CANDIDATE role of a signifier in THIS document. Corpus-level roles
    (nodal/floating/empty) require comparative analysis and human review;
    a single document can only propose a candidate."""
    assignment_id: str = Field(default_factory=lambda: new_id("role"))
    signifier: str
    role: SignifierRole
    rationale: str
    needs_corpus_validation: bool = True


class CollectiveSubject(EvidenceLink):
    """'We', 'the people', 'workers' — constructed through articulation,
    not merely mentioned. Membership and common demands need evidence."""
    subject_id: str = Field(default_factory=lambda: new_id("subject"))
    label: str
    constructed_in_text: str | None = None


class AntagonisticFrontier(EvidenceLink):
    """A constitutive limit organising 'us' against an obstructing other.
    Policy disagreement or negative sentiment does not establish this."""
    frontier_id: str = Field(default_factory=lambda: new_id("frontier"))
    us_label: str
    them_label: str
    rationale: str


class AffectiveInvestment(EvidenceLink):
    """The attachment giving a signifier/demand/identity political force.
    Affects are NOT constrained to fixed positive/negative polarities."""
    investment_id: str = Field(default_factory=lambda: new_id("inv"))
    affect_label: str                    # hope, anger, fear, pride, ambivalence...
    target_label: str
    intensity: float | None = Field(default=None, ge=0, le=1)


class DiscourseCandidate(EvidenceLink):
    """A proposed structured totality of articulations — an interpretive
    claim, never a bag of co-occurring topics."""
    discourse_id: str = Field(default_factory=lambda: new_id("disc"))
    label: str
    description: str | None = None


class DiscursiveRoleAssignment(EvidenceLink):
    role_assignment_id: str = Field(default_factory=lambda: new_id("drole"))
    concept_label: str
    discourse_label: str
    role: Literal["element", "moment", "nodal_point"]


# ── Palonen's Formula of Populism (interpretive, not numerical) ──────

class PopulistConfiguration(EvidenceLink):
    """Populism = Us^Affects1 + Frontier^Affects2 — recorded as an
    interpretive structure: the proposed collective subject, frontier
    and affective investments, each with evidence. Absent components
    mean the configuration is not (yet) evidenced in the document."""
    configuration_id: str = Field(default_factory=lambda: new_id("pop"))
    populist: bool | None = None
    non_populist_reason: str | None = None
    us_label: str | None = None
    frontier_label: str | None = None
    us_affects: list[str] = Field(default_factory=list)
    frontier_affects: list[str] = Field(default_factory=list)


# ── corpus-level candidates (frequency != hegemony) ──────────────────

class HegemonyAssessment(Model):
    """Frequency, prominence and repetition GUIDE inquiry but do not
    establish hegemony; uptake and stabilisation need cross-corpus
    evidence. Always starts as model_proposed, human-adjudicated."""
    assessment_id: str = Field(default_factory=lambda: new_id("heg"))
    label: str
    interpretation: str | None = None
    review_status: ReviewStatus = ReviewStatus.MODEL_PROPOSED
    evidence_document_ids: list[str] = Field(default_factory=list)
    provenance_id: str


class AnalysisResult(Model):
    """Structured output of one LaclauGPT analysis. Theoretical codes
    are candidates with evidence/uncertainty/review status; abstention
    is a first-class outcome."""
    document_id: str = Field(default_factory=lambda: new_id("doc"))
    run_id: str = Field(default_factory=lambda: new_id("run"))
    summary: str | None = None
    entities: list[Entity] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    sentiment_targets: list[SentimentAnnotation] = Field(default_factory=list)
    concepts: list[Concept] = Field(default_factory=list)
    articulations: list[Articulation] = Field(default_factory=list)
    signifier_roles: list[SignifierRoleAssignment] = Field(default_factory=list)
    collective_subjects: list[CollectiveSubject] = Field(default_factory=list)
    antagonistic_frontiers: list[AntagonisticFrontier] = Field(default_factory=list)
    affective_investments: list[AffectiveInvestment] = Field(default_factory=list)
    populist_configuration: PopulistConfiguration | None = None
    discourses: list[DiscourseCandidate] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    not_detected: list[str] = Field(default_factory=list)   # explicit abstention
    provenance: Provenance | None = None