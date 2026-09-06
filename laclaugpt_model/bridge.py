# -*- coding: utf-8 -*-
"""Bridge: interchange schema 1.x annotations -> canonical data model.

Interchange stays the pipeline's output format; this adapter lifts it
into the canonical model so DNA/SNA/signifier projections and Parquet
storage work on everything the pipeline produces. Non-destructive:
interchange files remain valid.
"""
from __future__ import annotations

from typing import Iterable

from laclaugpt_interchange import from_jsonl
from laclaugpt_model import (Actor, AnalysisRun, Concept, Document, Relation,
                             Statement, Stance)

# interchange MemoryRef.kind -> canonical actor/concept split
_ACTOR_KINDS = {"entity", "actor"}


def interchange_to_canonical(annotations_path: str,
                             run: AnalysisRun | None = None,
                             ) -> tuple[list[Document], list[Actor], list[Concept],
                                        list[Statement], list[Relation]]:
    docs: list[Document] = []
    actors: dict[str, Actor] = {}
    concepts: dict[str, Concept] = {}
    statements: list[Statement] = []
    relations: list[Relation] = []

    for ann in from_jsonl(annotations_path):
        docs.append(Document(id=ann.document_id,
                             text=ann.summary,
                             source=ann.source_platform,
                             published_at=ann.created_at,
                             metadata={"country": ann.source_country,
                                       "language": ann.language}))
        for ref in list(ann.entities) + list(getattr(ann, "actors", None) or []):
            if ref.obj_id in actors:
                continue
            kind = "account" if ref.kind == "entity" else ref.kind
            attributes = {"raw": ref.raw}
            if getattr(ref, "ner_type", ""):
                attributes["ner_type"] = ref.ner_type
            actors[ref.obj_id] = Actor(id=ref.obj_id, name=ref.label,
                                       type=kind, attributes=attributes)
        for ref in list(ann.topics) + list(ann.signifiers) + list(ann.discourses):
            if ref.obj_id in concepts:
                continue
            concepts[ref.obj_id] = Concept(id=ref.obj_id, label=ref.label,
                                           attributes={"kind": ref.kind,
                                                       "raw": ref.raw})

        # interchange: Us/frontier/affects are first-class lists; affects
        # reference Us/frontier elements by obj_id
        affects_by_ref: dict[str, str] = {}
        for af in ann.affects or []:
            tgt = af.target
            key = getattr(tgt, "obj_id", None) or tgt
            affects_by_ref[key] = af.affect
        for side, els, stance in (("us", ann.us, Stance.SUPPORT),
                                  ("frontier", ann.frontier, Stance.OPPOSE)):
            for el in els:
                cid = el.obj_id
                if not cid:
                    continue
                if cid not in concepts:
                    concepts[cid] = Concept(id=cid, label=el.label,
                                            attributes={"kind": "concept"})
                statements.append(Statement(
                    document_id=ann.document_id, actor_id=None,
                    concept_id=cid, stance=stance,
                    timestamp=ann.created_at,
                    qualifiers={"side": side,
                                "affect": affects_by_ref.get(cid)},
                    analysis_run_id=run.id if run else None))
        for np in ann.nodal_points or []:
            cid = np.obj_id
            if cid and cid not in concepts:
                concepts[cid] = Concept(id=cid, label=np.label,
                                        attributes={"kind": "concept"})

        for art in ann.articulations:
            sid = art.signifier.obj_id
            if sid not in concepts:
                concepts[sid] = Concept(id=sid, label=art.signifier.label,
                                        attributes={"raw": art.signifier.raw})
            relations.append(Relation(
                source_id=ann.document_id, target_id=sid,
                type="articulates", timestamp=ann.created_at,
                evidence_ids=[art.evidence] if art.evidence else [],
                analysis_run_id=run.id if run else None))

    return docs, list(actors.values()), list(concepts.values()), statements, relations
