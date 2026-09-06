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

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.3"   # 1.3: MemoryRef.ner_type (spaCy NER classes)


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
    nodal_candidate: bool = False
    empty_candidate: bool = False


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
    hegemonic_evidence: list[str] = []
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

    summary: str = ""
    evidence_quotes: list[str] = []


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
            return [MemoryRef(obj_id=r["obj_id"], label=r["label"], kind="signifier",
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
