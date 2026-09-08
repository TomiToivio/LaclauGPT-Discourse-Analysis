"""Lift the existing pipeline interchange format into the 2.0 model."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from laclaugpt_interchange import from_jsonl
from laclaugpt.model import (Articulation, AttributionType, Concept, Discourse,
                             Entity, EvidenceSpan, Provenance, Representation,
                             ReviewStatus, SourceItem, Statement)

# INV_CONTEXT (THEORY.md §15): the interchange claim_status vocabulary maps
# onto the canonical model's attribution types so quoted/reported/parodied
# codings are never lifted into author-asserted statements. "rejected" maps to
# AttributionType.REJECTED (issue #63): the document explicitly distances
# itself from the claim, which is stronger information than mere UNCLEAR.
_CLAIM_STATUS_TO_ATTRIBUTION = {
    "asserted": AttributionType.AUTHOR,
    "quoted": AttributionType.QUOTED,
    "reported": AttributionType.REPORTED,
    "parodied": AttributionType.IRONIC,
    "rejected": AttributionType.REJECTED,
    "uncertain": AttributionType.UNCLEAR,
}


@dataclass
class CanonicalCorpus:
    sources: list[SourceItem] = field(default_factory=list)
    representations: list[Representation] = field(default_factory=list)
    statements: list[Statement] = field(default_factory=list)
    evidence: list[EvidenceSpan] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    concepts: list[Concept] = field(default_factory=list)
    discourses: list[Discourse] = field(default_factory=list)
    articulations: list[Articulation] = field(default_factory=list)
    provenance: list[Provenance] = field(default_factory=list)
    # Issue #60: the lift preserves the families it previously dropped so a
    # human reviewer sees the same evidence surface in the canonical model.
    # Canonical model classes for populism configurations, signifier roles
    # and hegemony assessments exist but require IDs/discourses that the
    # interchange does not carry; their raw evidence is preserved as
    # statements + evidence spans and the remaining narrative as annotations.
    review_annotations: list[dict] = field(default_factory=list)


def interchange_to_v2(path: str) -> CanonicalCorpus:
    corpus = CanonicalCorpus()
    seen_entities: set[str] = set()
    seen_concepts: set[str] = set()
    for annotation in from_jsonl(path):
        provenance = Provenance(method="import", model=annotation.model or None,
                                prompt_version=json.dumps(annotation.prompt_versions, sort_keys=True) if annotation.prompt_versions else None,
                                imported_from=f"laclaugpt_interchange_{annotation.schema_version}")
        corpus.provenance.append(provenance)
        source = SourceItem(source_id=annotation.document_id,
                            source_type="post", platform=annotation.source_platform or None,
                            language=annotation.language or None,
                            raw_text=annotation.summary,
                            metadata={"country": annotation.source_country})
        representation = Representation(
            source_id=source.source_id, representation_type="summary",
            text=annotation.summary, language=annotation.language or None,
            model=annotation.model or None, provenance_id=provenance.provenance_id)
        corpus.sources.append(source); corpus.representations.append(representation)

        # Issue #60: preserve the review state instead of hardcoding it.
        # The interchange review status is the pipeline's honest "model
        # proposed" state until a human reviews; PROVISIONAL maps onto
        # ReviewStatus.MODEL_PROPOSED, human review statuses map forward.
        _REVIEW_STATUS_LIFT = {
            "PROVISIONAL": ReviewStatus.MODEL_PROPOSED,
            "ACCEPTED": ReviewStatus.ACCEPTED,
            "REJECTED": ReviewStatus.REJECTED,
        }
        review_status = _REVIEW_STATUS_LIFT.get(
            str(annotation.review_status).upper(), ReviewStatus.MODEL_PROPOSED)

        # Hegemonic evidence (INV_HEGEMONY_CORPUS): lift spans with their
        # verification state so the canonical model keeps the gate signal.
        for span in annotation.hegemonic_evidence:
            heg_statement = Statement(source_id=source.source_id,
                representation_id=representation.representation_id,
                text=span.quote,
                confidence=None,
                run_id=annotation.run_id or None)
            corpus.statements.append(heg_statement)
            corpus.evidence.append(EvidenceSpan(
                source_id=source.source_id,
                representation_id=representation.representation_id,
                statement_id=heg_statement.statement_id,
                exact_text=span.quote))
            corpus.review_annotations.append({
                "document_id": annotation.document_id,
                "kind": "hegemonic_evidence",
                "statement_id": heg_statement.statement_id,
                "evidence_source": span.evidence_source,
                "evidence_verified": span.evidence_verified,
            })

        # Populism assessment: populist verdict, reason and uncertainties are
        # theory-facing state a reviewer needs; preserve them per document.
        if annotation.populist is not None or annotation.populism_elements:
            corpus.review_annotations.append({
                "document_id": annotation.document_id,
                "kind": "populism_assessment",
                "populist": annotation.populist,
                "non_populist_reason": annotation.non_populist_reason,
                "populism_elements": [
                    {"element": e.element.obj_id, "side": e.side,
                     "affect": e.affect, "evidence": e.evidence,
                     "claim_status": e.claim_status,
                     "nodal_candidate": e.nodal_candidate,
                     "empty_candidate": e.empty_candidate}
                    for e in annotation.populism_elements
                ],
                "affects": [
                    {"target": a.target.obj_id, "affect": a.affect,
                     "side": a.side, "evidence": a.evidence}
                    for a in annotation.affects
                ],
                "review_status": str(annotation.review_status),
            })

        # Signifier roles and uncertainties ride along as review annotations.
        if annotation.signifier_roles or annotation.uncertainties:
            corpus.review_annotations.append({
                "document_id": annotation.document_id,
                "kind": "signifier_roles_and_uncertainties",
                "signifier_roles": [
                    {"obj_id": r.signifier.obj_id, "label": r.signifier.label,
                     "role": r.role, "evidence": r.evidence,
                     "confidence": r.confidence,
                     "needs_corpus_validation": r.needs_corpus_validation}
                    for r in annotation.signifier_roles
                ],
                "uncertainties": list(annotation.uncertainties),
                "requires_human_review": annotation.requires_human_review,
            })
        for ref in annotation.entities:
            if ref.obj_id not in seen_entities:
                corpus.entities.append(Entity(entity_id=ref.obj_id,
                    canonical_name=ref.label, entity_type=ref.ner_type or "Other",
                    aliases=[ref.raw] if ref.raw and ref.raw != ref.label else []))
                seen_entities.add(ref.obj_id)
        for ref in [*annotation.topics, *annotation.signifiers]:
            if ref.obj_id not in seen_concepts:
                corpus.concepts.append(Concept(concept_id=ref.obj_id,
                    canonical_label=ref.label,
                    concept_type="signifier" if ref.kind == "signifier" else "issue",
                    aliases=[ref.raw] if ref.raw and ref.raw != ref.label else []))
                seen_concepts.add(ref.obj_id)
        for ref in annotation.discourses:
            discourse_id = "disc_" + hashlib.sha1(ref.label.encode("utf-8")).hexdigest()[:16]
            corpus.discourses.append(Discourse(discourse_id=discourse_id,
                                                label=ref.label,
                                                review_status=review_status))
        for relation in annotation.articulations:
            statement = Statement(source_id=source.source_id,
                representation_id=representation.representation_id,
                text=relation.evidence or annotation.summary,
                attribution_type=_CLAIM_STATUS_TO_ATTRIBUTION.get(
                    relation.claim_status, AttributionType.UNCLEAR))
            quote = relation.evidence or None
            start = annotation.summary.find(quote) if quote else None
            evidence = EvidenceSpan(source_id=source.source_id,
                representation_id=representation.representation_id,
                statement_id=statement.statement_id, exact_text=quote,
                start_offset=start if start is not None and start >= 0 else None,
                end_offset=start + len(quote) if quote and start is not None and start >= 0 else None)
            target_id = relation.signifier.obj_id
            if target_id not in seen_concepts:
                corpus.concepts.append(Concept(concept_id=target_id,
                    canonical_label=relation.signifier.label, concept_type="signifier"))
                seen_concepts.add(target_id)
            related = list(relation.related_to)
            # A legacy articulation without an explicit second concept is
            # retained as evidence/statement but is not upgraded into a
            # theoretically stronger binary relation.
            corpus.statements.append(statement); corpus.evidence.append(evidence)
            for ref in related:
                if ref.obj_id not in seen_concepts:
                    corpus.concepts.append(Concept(concept_id=ref.obj_id,
                        canonical_label=ref.label, concept_type="other"))
                    seen_concepts.add(ref.obj_id)
                mapping = {"equivalence": "EQUIVALENT_TO", "difference": "DIFFERENTIATED_FROM",
                           "frontier_of": "ANTAGONISTIC_TO", "articulates": "ARTICULATES"}
                corpus.articulations.append(Articulation(
                    source_id=source.source_id, statement_id=statement.statement_id,
                    source_concept_id=target_id, target_concept_id=ref.obj_id,
                    relation_type=mapping.get(relation.relation, "ARTICULATES"),
                    confidence=relation.confidence,
                    evidence_ids=[evidence.evidence_id], provenance_id=provenance.provenance_id,
                    review_status=review_status))
    return corpus
