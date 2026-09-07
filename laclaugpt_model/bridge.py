# -*- coding: utf-8 -*-
"""Legacy interchange bridge for the frozen ``laclaugpt_model`` API.

New code should use ``laclaugpt.adapters.interchange.interchange_to_v2`` and
``laclaugpt.model``. This bridge is retained only so older projection/storage
workflows can still read schema-1.x/1.3 pipeline outputs during migration.
"""
from __future__ import annotations

import hashlib
import warnings

from laclaugpt_interchange import from_jsonl
from laclaugpt_model import (Actor, AnalysisRun, Concept, Document, Relation,
                             Statement, Stance)

warnings.warn(
    "laclaugpt_model.bridge is legacy; use laclaugpt.adapters.interchange.interchange_to_v2",
    FutureWarning,
    stacklevel=2,
)


def _discourse_concept_id(label: str) -> str:
    return "legacy_discourse_" + hashlib.sha1(label.encode("utf-8")).hexdigest()[:16]


def interchange_to_canonical(
    annotations_path: str,
    run: AnalysisRun | None = None,
) -> tuple[list[Document], list[Actor], list[Concept], list[Statement], list[Relation]]:
    """Read interchange into the frozen pre-2.0 compatibility model.

    The return shape is preserved for old callers. In particular, discourse
    candidates are converted into synthetic compatibility ``Concept`` objects
    instead of being treated as ``MemoryRef`` instances. That keeps schema-1.3
    outputs readable without pretending that the old model is canonical.
    """
    docs: list[Document] = []
    actors: dict[str, Actor] = {}
    concepts: dict[str, Concept] = {}
    statements: list[Statement] = []
    relations: list[Relation] = []

    for ann in from_jsonl(annotations_path):
        docs.append(Document(
            id=ann.document_id,
            text=ann.summary,
            source=ann.source_platform,
            published_at=ann.created_at,
            metadata={"country": ann.source_country, "language": ann.language},
        ))

        for ref in list(ann.entities) + list(getattr(ann, "actors", None) or []):
            if not ref.obj_id or ref.obj_id in actors:
                continue
            # The old ActorType vocabulary has no generic "actor" value. Use
            # account as the least-committal compatibility representation.
            actor_type = "account" if ref.kind in {"entity", "actor"} else "person"
            attributes = {"raw": ref.raw, "legacy_kind": ref.kind}
            if getattr(ref, "ner_type", ""):
                attributes["ner_type"] = ref.ner_type
            actors[ref.obj_id] = Actor(
                id=ref.obj_id,
                name=ref.label,
                type=actor_type,
                attributes=attributes,
            )

        for ref in list(ann.topics) + list(ann.signifiers):
            if not ref.obj_id or ref.obj_id in concepts:
                continue
            concepts[ref.obj_id] = Concept(
                id=ref.obj_id,
                label=ref.label,
                attributes={"kind": ref.kind, "raw": ref.raw},
            )

        # Interchange discourse candidates are Discourse objects, not
        # MemoryRefs. Preserve them as compatibility concepts with deterministic
        # IDs so old graph workflows can still inspect them.
        for discourse in ann.discourses:
            cid = _discourse_concept_id(discourse.label)
            if cid in concepts:
                continue
            concepts[cid] = Concept(
                id=cid,
                label=discourse.label,
                attributes={
                    "kind": "discourse",
                    "confidence": discourse.confidence,
                    "element_ids": [
                        element.obj_id for element in discourse.elements if element.obj_id
                    ],
                },
            )

        affects_by_ref: dict[str, str] = {}
        for affect in ann.affects or []:
            target = affect.target
            key = getattr(target, "obj_id", None) or target
            affects_by_ref[key] = affect.affect

        for side, elements, stance in (
            ("us", ann.us, Stance.SUPPORT),
            ("frontier", ann.frontier, Stance.OPPOSE),
        ):
            for element in elements:
                cid = element.obj_id
                if not cid:
                    continue
                if cid not in concepts:
                    concepts[cid] = Concept(
                        id=cid,
                        label=element.label,
                        attributes={"kind": "concept"},
                    )
                statements.append(Statement(
                    document_id=ann.document_id,
                    actor_id=None,
                    concept_id=cid,
                    stance=stance,
                    timestamp=ann.created_at,
                    qualifiers={"side": side, "affect": affects_by_ref.get(cid)},
                    analysis_run_id=run.id if run else None,
                ))

        for nodal in ann.nodal_points or []:
            cid = nodal.obj_id
            if cid and cid not in concepts:
                concepts[cid] = Concept(
                    id=cid,
                    label=nodal.label,
                    attributes={"kind": "concept"},
                )

        for articulation in ann.articulations:
            sid = articulation.signifier.obj_id
            if not sid:
                continue
            if sid not in concepts:
                concepts[sid] = Concept(
                    id=sid,
                    label=articulation.signifier.label,
                    attributes={"raw": articulation.signifier.raw},
                )
            relations.append(Relation(
                source_id=ann.document_id,
                target_id=sid,
                type="articulates",
                timestamp=ann.created_at,
                evidence_ids=[articulation.evidence] if articulation.evidence else [],
                analysis_run_id=run.id if run else None,
            ))

    return docs, list(actors.values()), list(concepts.values()), statements, relations
