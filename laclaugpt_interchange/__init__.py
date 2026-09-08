# -*- coding: utf-8 -*-
"""LaclauGPT interchange schema — the standard output format.

One schema consumed by 4CAT, DATS, the pipeline and future tools
(Tomi's architecture decision 2026-09-04). Everything LaclauGPT
produces is expressed as annotations over documents with stable IDs
from the persistent memory (laclaugpt_memory).

Design rules:
- document_id is the interchange key (4CAT post id / DATS doc id / video key)
- every reference points to a stable memory ID (E001/T001/S001/C001/A001/F001)
- raw surface forms ride along (Laclau: the exact wording is data)
- provenance is mandatory (stage, model, timestamps, evidence quote)
- JSONL: one line per document; Parquet export available via pandas
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.5"   # 1.5: PopulismElementAssessment.claim_status (INV_CONTEXT);
                         #       DocumentAnnotation.discourse_applicable /
                         #       discourse_applicability_reason (INV_ABSTAIN);
                         #       populist=true requires non-empty us AND frontier
                         # 1.4: DocumentAnnotation.sentiment_observations (descriptive)
                         # 1.3: MemoryRef.ner_type (spaCy NER classes)


class MemoryRef(BaseModel):
    """Reference to a canonical object in laclaugpt_memory."""
    obj_id: str = Field(..., description="stable ID: E001/T001/S001/C001/A001/F001")
    label: str = Field(..., description="canonical label")
    kind: str = Field(..., description="entity|topic|signifier|target|actor|formation")
    raw: str = Field("", description="raw surface form as found in the document")
    ner_type: str = Field("", description=(
        "spaCy NER entity class for kind='entity' (PERSON/ORG/GPE/DATE/...); "
        "closed vocabulary from laclaugpt_memory.NER_TYPES, '' when untyped"))


class Articulation(BaseModel):
    """One articulation: a raw signifier welded into a relation."""
    signifier: MemoryRef
    related_to: list[MemoryRef] = []
    relation: str = "articulates"   # articulates|equivalence|difference|frontier_of
    evidence: str = ""              # quote from the document
    evidence_source: str = ""       # source column/modal transformation
    evidence_verified: bool = False
    claim_status: str = "asserted"
    confidence: float = 0.0
    rationale: str = ""


class Affect(BaseModel):
    target: MemoryRef
    affect: str                     # hope|fear|anger|pride|resentment|...
    polarity: str = ""              # optional sentiment polarity; not inferred from side
    side: str = ""                  # us|frontier when used in Palonen's formula
    evidence: str = ""
    evidence_source: str = ""
    evidence_verified: bool = False
    confidence: float = 0.0


class UsFrontier(BaseModel):
    """Palonen's Formula of Populism, structured."""
    us: list[MemoryRef] = []        # elements of the "people" chain
    us_affects: list[str] = []
    frontier: list[MemoryRef] = []
    frontier_affects: list[str] = []
    formula: str = ""               # human-readable restatement
    populist: bool = False


class Discourse(BaseModel):
    label: str = ""                 # free label (candidate discourse)
    confidence: float = 0.0
    elements: list[MemoryRef] = []


class SignifierRole(BaseModel):
    signifier: MemoryRef
    role: str
    rationale: str = ""
    evidence: str = ""
    evidence_source: str = ""
    confidence: float = 0.0
    needs_corpus_validation: bool = False
    evidence_verified: bool = False


class SociotechnicalImaginary(BaseModel):
    label: str
    normative_future: str = ""
    present_diagnosis: str = ""
    technology_role: str = ""
    human_agency: str = ""
    evidence: str = ""
    evidence_source: str = ""
    confidence: float = 0.0
    claim_status: str = "asserted"
    evidence_verified: bool = False


class FormationAssessment(BaseModel):
    formation: MemoryRef
    supporting_features: list[str] = []
    counter_evidence: list[str] = []
    evidence: str = ""
    evidence_source: str = ""
    confidence: float = 0.0
    evidence_verified: bool = False


class PopulismElementAssessment(BaseModel):
    """Evidence-bearing element on one side of Palonen's formula."""
    element: MemoryRef
    side: str                         # us | frontier
    affect: str = ""
    evidence: str = ""
    evidence_source: str = ""
    evidence_verified: bool = False
    confidence: float = 0.0
    claim_status: str = "asserted"    # asserted|quoted|reported|rejected|parodied|uncertain
    nodal_candidate: bool = False
    empty_candidate: bool = False


class HegemonicEvidenceSpan(BaseModel):
    """One verified-or-flagged hegemonic evidence quote (schema 1.4).

    Hegemony is the most theory-sensitive claim family (INV_HEGEMONY_CORPUS):
    its evidence quotes now pass through the same mechanical verbatim gate and
    carry the same evidence_source provenance as every other coding family.
    Legacy bare-string entries (schema ≤1.3) are upgraded with verified=False,
    so an unverified legacy quote can never silently pass as verified.
    """
    quote: str = Field(min_length=1)
    evidence_source: str = ""         # source column/modal transformation
    evidence_verified: bool = False


class SentimentObservation(BaseModel):
    """Descriptive sentiment observation (schema 1.4).

    Deliberately distinct from Laclaudian affective investment (Affect):
    this is the coarse positive/neutral/negative polarity assigned by the
    descriptive post-processing stage, with the target resolved to a
    stable codebook ID. Affect MUST NOT be reduced to this polarity
    (paper §3.1, INTEROPERABILITY_SPEC §8); the two record families
    coexist on one annotation but never substitute for each other.
    """
    target: MemoryRef                 # stable ID from laclaugpt_memory (C-kind)
    polarity: str                     # positive | neutral | negative
    evidence_source: str = ""         # stage/source field the reading came from
    uncertainty: float = 0.0          # 0..1; 0 = no uncertainty recorded
    model: str = ""                   # actual model that produced the reading
    prompt_version: str = ""          # postprocess prompt version
    review_status: str = "PROVISIONAL"


class DocumentAnnotation(BaseModel):
    """One annotated document — the interchange unit."""
    schema_version: str = SCHEMA_VERSION
    document_id: str
    source_platform: str = ""       # tiktok|x|instagram|...
    source_country: str = ""
    language: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    analysis_stage: str = "laclaugpt-analysis"
    model: str = ""
    model_digest: str = ""   # model build digest (paper §3.3); "" when unavailable
    run_id: str = ""

    entities: list[MemoryRef] = []
    signifiers: list[MemoryRef] = []
    articulations: list[Articulation] = []
    topics: list[MemoryRef] = []
    discourses: list[Discourse] = []
    affects: list[Affect] = []
    us: list[MemoryRef] = []
    frontier: list[MemoryRef] = []
    nodal_points: list[MemoryRef] = []
    signifier_roles: list[SignifierRole] = []
    imaginaries: list[SociotechnicalImaginary] = []
    formation_candidates: list[FormationAssessment] = []

    populist: bool | None = None
    populism_analysis: str = ""
    non_populist_reason: str = ""
    uncertainties: list[str] = []
    hegemonic_evidence: list[HegemonicEvidenceSpan] = []
    requires_human_review: bool = True
    review_status: str = "PROVISIONAL"
    prompt_versions: dict[str, str] = {}
    source_author: str = ""
    source_timestamp: str = ""
    source_url: str = ""
    parent_id: str = ""
    sequence_index: str = ""
    source_modalities: list[str] = []
    transformations: dict[str, Any] = {}
    collection_provenance: dict[str, Any] = {}
    populism_elements: list[PopulismElementAssessment] = []
    counter_evidence: list[str] = []
    sentiment_observations: list[SentimentObservation] = []

    # Discourse-stage applicability (INV_ABSTAIN): the model may judge the
    # Laclaudian analysis non-applicable to a document. That signal is
    # published instead of being discarded, so an "not applicable" document is
    # distinguishable from one with legitimately empty codings.
    discourse_applicable: bool | None = None
    discourse_applicability_reason: str = ""

    summary: str = ""
    evidence_quotes: list[str] = []

    @model_validator(mode="after")
    def populist_requires_both_sides(self):
        # INV_POPULISM (THEORY.md §15): populist=true requires an evidenced
        # Us and Frontier construction. Enforcement lives at the prompt stage
        # and here, at the schema every downstream consumer reads. Since
        # issue #59, populist=false may carry evidenced sides (one side from
        # the model's partial abstention; both sides after human review that
        # rejects the formula while retaining the codings), so only the
        # populist=true direction is schema-enforced here.
        if self.populist and not (self.us and self.frontier):
            raise ValueError(
                "populist=true requires non-empty us and frontier lists "
                "(INV_POPULISM: evidenced Us + Frontier construction)")
        return self

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_hegemonic_evidence(cls, data):
        # Schema-1.3 compatibility (INV_EVIDENCE / INV_HEGEMONY_CORPUS): the
        # hegemonic evidence family used to be bare strings. Upgrade them to
        # verified=False spans so an unverified legacy quote can never pass
        # as verified, and older JSONL files stay readable.
        if not isinstance(data, dict):
            return data
        legacy = data.get("hegemonic_evidence")
        if isinstance(legacy, list):
            data["hegemonic_evidence"] = [
                item if isinstance(item, (dict, HegemonicEvidenceSpan))
                else {"quote": str(item), "evidence_source": "",
                      "evidence_verified": False}
                for item in legacy if str(item).strip()
            ]
        return data

    @model_validator(mode="after")
    def substantive_codings_require_evidence(self):
        # INV_EVIDENCE at schema level (issue #60): substantive theoretical
        # codings must carry evidence. Older JSONL (schema ≤1.3) legitimately
        # lacks verified fields, so legacy rows degrade to an explicit
        # uncertainty instead of failing the whole file. New pipeline output
        # fills these fields; a coding with no evidence text at all is a
        # contract violation.
        missing = []
        for art in self.articulations:
            if not (art.evidence or "").strip():
                missing.append(f"articulation {art.signifier.obj_id}")
        for role in self.signifier_roles:
            if not (role.evidence or "").strip():
                missing.append(f"signifier_role {role.signifier.obj_id}")
        for element in self.populism_elements:
            if not (element.evidence or "").strip():
                missing.append(f"populism_element {element.element.obj_id}")
        for span in self.hegemonic_evidence:
            if not (span.quote or "").strip():
                missing.append("hegemonic_evidence span")
        if missing:
            self.uncertainties.append(
                "evidence-optional legacy coding(s) without evidence text: "
                + "; ".join(missing[:5]))
        return self


def _as_iref(ref) -> MemoryRef:
    """Accept either interchange MemoryRef or laclaugpt_memory.MemoryRef."""
    if ref is None:
        return MemoryRef(obj_id="", label="", kind="topic")
    if isinstance(ref, MemoryRef):
        return ref
    return MemoryRef(obj_id=getattr(ref, "obj_id", ""), label=getattr(ref, "label", ""),
                     kind=getattr(ref, "kind", "topic"), raw=getattr(ref, "raw", ""))


def from_memory_results(document_id: str, *, platform: str = "", country: str = "",
                        language: str = "", model: str = "", run_id: str = "",
                        summary: str = "",
                        entity_refs: list | None = None,
                        signifier_refs: list | None = None,
                        topic_refs: list | None = None,
                        target_resolutions: list[dict] | None = None,
                        populism: dict | None = None) -> DocumentAnnotation:
    """Build an annotation from the pipeline's stage outputs.

    populism: the PopulismStage dict (populism_us/populism_frontier with
    MemoryRefs already resolved); target_resolutions: memory resolution
    results for sentiment targets.
    """
    from laclaugpt_memory import MemoryRef as _MemRef  # convert, don't shadow
    ann = DocumentAnnotation(
        document_id=document_id, source_platform=platform,
        source_country=country, language=language, model=model, run_id=run_id,
        summary=summary)
    ann.entities = [_as_iref(r) for r in (entity_refs or [])]
    ann.signifiers = [_as_iref(r) for r in (signifier_refs or [])]
    ann.topics = [_as_iref(r) for r in (topic_refs or [])]
    if populism:
        def refs(items):
            return [MemoryRef(obj_id=r["obj_id"], label=r["label"],
                              kind=r.get("kind", "signifier"),
                              raw=r.get("raw", ""))
                    for r in items if isinstance(r, dict) and r.get("obj_id")]
        ann.us = refs(populism.get("populism_us", []))
        ann.frontier = refs(populism.get("populism_frontier", []))
        ann.populism_elements = [
            PopulismElementAssessment(
                element=_as_iref(MemoryRef(
                    obj_id=r["obj_id"], label=r["label"], kind="signifier",
                    raw=r.get("raw", ""),
                )),
                side=side,
                affect=r.get("affect", ""),
                evidence=r.get("evidence", ""),
                evidence_source=r.get("evidence_source", ""),
                evidence_verified=r.get("evidence_verified", False),
                confidence=r.get("confidence", 0.0),
                claim_status=r.get("claim_status", "asserted"),
                nodal_candidate=r.get("nodal", False),
                empty_candidate=r.get("empty_candidate", False),
            )
            for side, items in (
                ("us", populism.get("populism_us", [])),
                ("frontier", populism.get("populism_frontier", [])),
            )
            for r in items if isinstance(r, dict) and r.get("obj_id")
        ]
        ann.nodal_points = [_as_iref(MemoryRef(obj_id=r["obj_id"], label=r["label"],
                                               kind="signifier", raw=r.get("raw", "")))
                            for r in populism.get("populism_us", [])
                            + populism.get("populism_frontier", [])
                            if isinstance(r, dict) and r.get("nodal", False)]
        # Affect polarity is never inferred from the Us/Frontier side:
        # anger can invest an Us element and admiration an opponent
        # (paper §3.1; populism prompt v3).  The side is recorded as data.
        ann.affects = [
            Affect(target=_as_iref(MemoryRef(obj_id=r["obj_id"],
                                             label=r["label"], kind="signifier",
                                             raw=r.get("raw", ""))),
                   affect=r.get("affect", ""), polarity="",
                   side="us", evidence=r.get("evidence", ""),
                   evidence_source=r.get("evidence_source", ""),
                   evidence_verified=r.get("evidence_verified", False),
                   confidence=r.get("confidence", 0.0))
            for r in populism.get("populism_us", [])
            if isinstance(r, dict) and r.get("affect")
        ] + [
            Affect(target=_as_iref(MemoryRef(obj_id=r["obj_id"],
                                             label=r["label"], kind="signifier",
                                             raw=r.get("raw", ""))),
                   affect=r.get("affect", ""), polarity="",
                   side="frontier", evidence=r.get("evidence", ""),
                   evidence_source=r.get("evidence_source", ""),
                   evidence_verified=r.get("evidence_verified", False),
                   confidence=r.get("confidence", 0.0))
            for r in populism.get("populism_frontier", [])
            if isinstance(r, dict) and r.get("affect")
        ]
    return ann


def to_jsonl(annotations: list[DocumentAnnotation], path: str) -> str:
    import json
    with open(path, "w", encoding="utf-8") as fh:
        for ann in annotations:
            fh.write(json.dumps(ann.model_dump(), ensure_ascii=False) + "\n")
    return path


def from_jsonl(path: str) -> list[DocumentAnnotation]:
    import json
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(DocumentAnnotation.model_validate_json(line))
    return out
