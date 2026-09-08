"""Lift the existing pipeline interchange format into the 2.0 model."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from laclaugpt_interchange import from_jsonl
from laclaugpt.model import (Articulation, AttributionType, Concept, Discourse,
                             Entity, EvidenceSpan, Provenance, Representation,
                             SourceItem, Statement)

# INV_CONTEXT (THEORY.md §15): the interchange claim_status vocabulary maps
# onto the canonical model's attribution types so quoted/reported/parodied
# codings are never lifted into author-asserted statements. "rejected" has no
# direct canonical equivalent yet, so it conservatively stays UNCLEAR rather
# than being attributed to the author (canonical model gap tracked in the
# issue-#50 follow-ups).
_CLAIM_STATUS_TO_ATTRIBUTION = {
    "asserted": AttributionType.AUTHOR,
    "quoted": AttributionType.QUOTED,
    "reported": AttributionType.REPORTED,
    "parodied": AttributionType.IRONIC,
    "rejected": AttributionType.UNCLEAR,
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
                                                review_status="model_proposed"))
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
                    review_status="model_proposed"))
    return corpus
