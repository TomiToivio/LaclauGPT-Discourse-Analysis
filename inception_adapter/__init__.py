# -*- coding: utf-8 -*-
"""INCEpTION adapter — importer/exporter over the LaclauGPT interchange schema.

INCEpTION (inception-project/inception, TU Darmstadt) is the annotation
platform layer (WebAnno's successor). Its native interchange is Apache UIMA
CAS — de-facto standard UIMA CAS XMI (XML 1.0) + a separate type-system XML.
Python support is official via DKPro Cassis (dkpro-cassis, same project).

Format mapping (LaclauGPT interchange 1.2 <-> UIMA CAS):

  LaclauGPT                          UIMA CAS (custom.LaclauGPT layer)
  ---------------------------------  ------------------------------------
  document text                      sofa_string (one CAS per document)
  populism_elements (us/frontier)    custom.LaclauSpan annotations anchored
                                     at the evidence-quote char offsets;
                                     features: side, affect, evidence,
                                     obj_id, label, confidence,
                                     nodal_candidate, empty_candidate
  nodal/empty candidates             features on the same span layer
  signifiers/articulations           custom.LaclauRelation (begin at the
                                     signifier span, EndFeature = related
                                     span; feature relation + evidence)
  document metadata                  custom.LaclauDocMeta (document_id,
                                     platform, country, language, model,
                                     run_id, review_status, populist)

Import (INCEpTION -> LaclauGPT):
  - ``import_inception_xmi`` reads CAS XMI (+ optional shared TypeSystem.xml)
    back into interchange DocumentAnnotations: every custom.LaclauSpan
    becomes a PopulismElementAssessment (side/affect/evidence), so human
    corrections made inside INCEpTION flow back into the pipeline.

Export (LaclauGPT -> INCEpTION):
  - ``export_for_inception`` writes one XMI per document plus ONE
    TypeSystem.xml (INCEpTION's "UIMA CAS XMI (XML 1.0)" import expects
    exactly this pair; the project ZIP's per-document XMI files use the
    same shape).
  - ``export_statements_csv`` keeps the tool-agnostic fallback row shape.

cassis is an optional dependency: installed on demand
(``pip install dkpro-cassis``); without it the adapter raises ImportError
with that instruction. The CSV fallback always works and needs nothing.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from laclaugpt_interchange import (DocumentAnnotation, MemoryRef,
                                   PopulismElementAssessment, from_jsonl)

# Custom UIMA types written/read by this adapter.
_TYPE_SPAN = "custom.LaclauSpan"
_TYPE_RELATION = "custom.LaclauRelation"
_TYPE_DOCMETA = "custom.LaclauDocMeta"


# ---------------------------------------------------------------------------
# cassis bootstrap (optional dependency)
# ---------------------------------------------------------------------------

def _cassis():
    try:
        from cassis import (Cas, TypeSystem, load_cas_from_xmi,
                            load_typesystem)
        return Cas, TypeSystem, load_cas_from_xmi, load_typesystem
    except ImportError as e:  # pragma: no cover - environment guard
        raise ImportError(
            "INCEpTION adapter needs the optional dependency dkpro-cassis: "
            "pip install --break-system-packages dkpro-cassis") from e


def _span_offsets(quote: str, text: str) -> tuple[int, int]:
    """Character offsets of the evidence quote in the document text.

    Falls back to the whole text when the quote is not found verbatim
    (paraphrase/translation), so the span still anchors to its document.
    """
    if quote and quote in text:
        start = text.index(quote)
        return start, start + len(quote)
    return 0, max(len(text), 1)


def _build_typesystem(TypeSystem, doc_text: str):
    """TypeSystem with the three custom types this adapter owns."""
    ts = TypeSystem()
    Span = ts.create_type(_TYPE_SPAN)
    for name in ("side", "affect", "evidence", "obj_id", "label"):
        ts.create_feature(Span, name=name, rangeType="String")
    ts.create_feature(Span, name="confidence", rangeType="Double")
    ts.create_feature(Span, name="nodal_candidate", rangeType="Boolean")
    ts.create_feature(Span, name="empty_candidate", rangeType="Boolean")
    Rel = ts.create_type(_TYPE_RELATION)
    ts.create_feature(Rel, name="Governor", rangeType=_TYPE_SPAN)
    ts.create_feature(Rel, name="Dependent", rangeType=_TYPE_SPAN)
    ts.create_feature(Rel, name="relation", rangeType="String")
    ts.create_feature(Rel, name="evidence", rangeType="String")
    Meta = ts.create_type(_TYPE_DOCMETA)
    for name in ("document_id", "platform", "country", "language",
                 "model", "run_id", "review_status", "schema_version"):
        ts.create_feature(Meta, name=name, rangeType="String")
    return ts


def _types_with_span(TypeSystem, _unused=None):
    """TypeSystem pre-seeded with this adapter's types; returns (ts, Span, Rel, Meta)."""
    ts = _build_typesystem(TypeSystem, "")
    return ts, ts.get_type(_TYPE_SPAN), ts.get_type(_TYPE_RELATION), ts.get_type(_TYPE_DOCMETA)


# ---------------------------------------------------------------------------
# Export: LaclauGPT interchange -> INCEpTION (CAS XMI + TypeSystem.xml)
# ---------------------------------------------------------------------------

def export_for_inception(annotations_path: str, out_dir: str,
                         doc_texts: dict[str, str] | None = None) -> dict:
    """Write INCEpTION-importable CAS XMI files from interchange JSONL.

    Layout (what INCEpTION's "UIMA CAS XMI" import wants):
        <out_dir>/TypeSystem.xml            — shared type system
        <out_dir>/xmi/<document_id>.xmi     — one CAS per document

    doc_texts: optional {document_id: raw text}. When given, spans anchor
    in the RAW document text (best for human re-annotation); otherwise the
    annotation summary is used as the CAS text (self-contained, matching
    the DNA adapter's "summary" mode).
    """
    Cas, TypeSystem, _, _ = _cassis()
    annotations = from_jsonl(annotations_path)
    out = Path(out_dir)
    xmi_dir = out / "xmi"
    xmi_dir.mkdir(parents=True, exist_ok=True)

    ts, Span, Rel, Meta = _types_with_span(TypeSystem)
    ts.to_xml(str(out / "TypeSystem.xml"))

    n_docs = n_spans = n_rels = 0
    slug_seen: dict[str, int] = {}
    for ann in annotations:
        text = (doc_texts or {}).get(ann.document_id) or ann.summary or ann.document_id
        cas = Cas(sofa_string=text, typesystem=ts)

        meta = Meta(begin=0, end=len(text),
                    document_id=ann.document_id,
                    platform=ann.source_platform or "",
                    country=ann.source_country or "",
                    language=ann.language or "",
                    model=ann.model or "",
                    run_id=ann.run_id or "",
                    review_status=ann.review_status or "",
                    schema_version=ann.schema_version)
        cas.add(meta)

        span_added: list = []
        added_spans: dict[str, object] = {}
        for el in ann.populism_elements:
            if not (el.evidence or el.evidence_verified):
                continue
            label = el.element.label or el.element.raw or ""
            if not label:
                continue
            begin, end = _span_offsets(el.evidence, text)
            s = Span(begin=begin, end=end, side=el.side,
                     affect=el.affect or "", evidence=el.evidence or "",
                     obj_id=el.element.obj_id or "", label=label,
                     confidence=float(el.confidence or 0.0),
                     nodal_candidate=bool(el.nodal_candidate),
                     empty_candidate=bool(el.empty_candidate))
            cas.add(s)
            span_added.append((el, begin, end))
            if el.element.obj_id and el.element.obj_id not in added_spans:
                added_spans[el.element.obj_id] = s
            n_spans += 1

        # articulations as relation annotations between signifier spans.
        # The relation endpoints MUST be the exact FeatureStructure objects
        # already added to the CAS above — fresh stand-alone FS instances
        # serialize as sofa-less orphans that cassis's own importer rejects.
        for art in ann.articulations:
            sig = art.signifier
            if sig.obj_id not in added_spans:
                continue
            gov = added_spans[sig.obj_id]
            for dep in art.related_to:
                if dep.obj_id not in added_spans:
                    continue
                cas.add(Rel(begin=gov.begin, end=gov.end,
                            Governor=gov, Dependent=added_spans[dep.obj_id],
                            relation=art.relation, evidence=art.evidence or ""))
                n_rels += 1

        # INCEpTION filenames: filesystem-safe slug, unique
        slug = "".join(c if c.isalnum() or c in "-_" else "_"
                       for c in ann.document_id)[:180] or f"doc{n_docs + 1}"
        if slug in slug_seen:
            slug_seen[slug] += 1
            slug = f"{slug}_{slug_seen[slug]}"
        else:
            slug_seen[slug] = 0
        cas.to_xmi(str(xmi_dir / f"{slug}.xmi"), pretty_print=True)
        n_docs += 1

    return {"documents": n_docs, "spans": n_spans, "relations": n_rels,
            "typesystem": str(out / "TypeSystem.xml"), "xmi_dir": str(xmi_dir)}


def export_statements_csv(annotations_path: str, out_path: str) -> int:
    """Flat statement CSV fallback (same shape as the DNA adapter's).

    One row per evidence-bearing Us/Frontier element; loadable through
    INCEpTION's "Import Survey/Data" tabular path or any spreadsheet.
    """
    annotations = from_jsonl(annotations_path)
    count = 0
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["document_id", "platform", "country", "language",
                         "model", "run_id", "created_at", "side", "affect",
                         "label", "confidence", "nodal", "empty",
                         "evidence"])
        for ann in annotations:
            for el in ann.populism_elements:
                if not (el.evidence or el.evidence_verified):
                    continue
                label = el.element.label or el.element.raw or ""
                if not label:
                    continue
                writer.writerow([
                    ann.document_id, ann.source_platform,
                    ann.source_country, ann.language, ann.model,
                    ann.run_id, ann.source_timestamp or ann.created_at,
                    el.side, el.affect, label, el.confidence,
                    int(bool(el.nodal_candidate)),
                    int(bool(el.empty_candidate)), el.evidence,
                ])
                count += 1
    return count


# ---------------------------------------------------------------------------
# Import: INCEpTION (CAS XMI) -> LaclauGPT interchange
# ---------------------------------------------------------------------------

def import_inception_xmi(xmi_path: str, typesystem_path: str | None = None) -> list[dict]:
    """Read human-refined CAS XMI files back into LaclauGPT-ready rows.

    Returns one dict per custom.LaclauSpan with everything
    PopulismElementAssessment needs plus the source text, so the caller can
    merge human corrections into PROVISIONAL annotations (side/affect may
    have been fixed inside INCEpTION). Documents without the custom layer
    yield an empty span list but still carry text + docmeta.
    """
    _, _, load_cas_from_xmi, load_typesystem = _cassis()
    # load_typesystem treats str as XML content — pass a Path for file paths
    ts = load_typesystem(Path(typesystem_path)) if typesystem_path else None
    with open(xmi_path, "rb") as f:
        cas = load_cas_from_xmi(f, typesystem=ts)

    text = cas.sofa_string
    meta = next(iter(cas.select(_TYPE_DOCMETA)), None)
    doc_id = getattr(meta, "document_id", "") or Path(xmi_path).stem

    rows = []
    for s in cas.select(_TYPE_SPAN):
        evidence = s.get("evidence") or ""
        covered = s.get_covered_text()
        rows.append({
            "document_id": doc_id,
            "text": text,
            "platform": getattr(meta, "platform", ""),
            "country": getattr(meta, "country", ""),
            "language": getattr(meta, "language", ""),
            "model": getattr(meta, "model", ""),
            "run_id": getattr(meta, "run_id", ""),
            "review_status": getattr(meta, "review_status", ""),
            "span": {"begin": s.begin, "end": s.end,
                     "side": s.get("side") or "",
                     "affect": s.get("affect") or "",
                     "evidence": evidence or covered,
                     "obj_id": s.get("obj_id") or "",
                     "label": s.get("label") or covered,
                     "confidence": float(s.get("confidence") or 0.0),
                     "nodal_candidate": bool(s.get("nodal_candidate")),
                     "empty_candidate": bool(s.get("empty_candidate")),
                     "covered_text": covered},
        })
    if not rows:
        # still surface the document text + metadata for corpus import
        rows.append({
            "document_id": doc_id, "text": text,
            "platform": getattr(meta, "platform", "") if meta else "",
            "country": getattr(meta, "country", "") if meta else "",
            "language": getattr(meta, "language", "") if meta else "",
            "model": getattr(meta, "model", "") if meta else "",
            "run_id": getattr(meta, "run_id", "") if meta else "",
            "review_status": getattr(meta, "review_status", "") if meta else "",
            "span": None,
        })
    return rows


def import_inception_dir(xmi_dir: str, typesystem_path: str | None = None) -> list[dict]:
    """Import every .xmi in a directory (e.g. an unzipped INCEpTION export's
    annotation/<doc>/<user>.xmi files, or this adapter's own xmi/ output)."""
    out = []
    for p in sorted(Path(xmi_dir).glob("*.xmi")):
        out.extend(import_inception_xmi(str(p), typesystem_path))
    return out


def merge_inception_corrections(annotations_path: str, imported_rows: list[dict],
                                out_path: str) -> dict:
    """Merge human INCEpTION corrections into an interchange JSONL.

    For each imported span, matching is done by (document_id, obj_id);
    side/affect/confidence/nodal/empty are updated on the existing element
    and review_status is upgraded to INCEpTION-REVIEWED. Spans whose obj_id
    is new for the document are appended as new elements (human-added).
    Returns counts for logging.
    """
    annotations = {a.document_id: a for a in from_jsonl(annotations_path)}
    updated = new = 0
    touched: set[str] = set()
    for row in imported_rows:
        span = row.get("span")
        if not span:
            continue
        ann = annotations.get(row["document_id"])
        if ann is None:
            continue
        match = None
        for el in ann.populism_elements:
            if el.element.obj_id == span["obj_id"]:
                match = el
                break
        if match is None:
            ref = MemoryRef(obj_id=span["obj_id"], label=span["label"],
                            kind="signifier", raw=span["covered_text"])
            ann.populism_elements.append(PopulismElementAssessment(
                element=ref, side=span["side"] or "us",
                affect=span["affect"], evidence=span["evidence"],
                evidence_verified=True, confidence=span["confidence"],
                nodal_candidate=span["nodal_candidate"],
                empty_candidate=span["empty_candidate"]))
            new += 1
        else:
            if span["side"]:
                match.side = span["side"]
            match.affect = span["affect"]
            match.confidence = span["confidence"]
            match.nodal_candidate = span["nodal_candidate"]
            match.empty_candidate = span["empty_candidate"]
            match.evidence_verified = True
            updated += 1
        ann.review_status = "INCEpTION-REVIEWED"
        ann.requires_human_review = False
        touched.add(row["document_id"])

    # Re-derive Formula-of-Populism coherence after human edits (issue #50):
    # human-added evidenced Us and Frontier spans can turn an earlier
    # abstention into a both-sides coding. Leaving populist=False with both
    # sides populated would export a contradictory annotation (INV_POPULISM).
    for doc_id in touched:
        ann = annotations[doc_id]
        us = [el for el in ann.populism_elements if el.side == "us"]
        frontier = [el for el in ann.populism_elements if el.side == "frontier"]
        if us and frontier:
            ann.populist = True
            ann.non_populist_reason = ""
            ann.us = [el.element for el in us]
            ann.frontier = [el.element for el in frontier]
        elif ann.populist:
            # Both sides can no longer be evidenced after human edits: demote
            # back to an explicit abstention instead of publishing an invalid
            # populist=true.
            ann.populist = False
            ann.non_populist_reason = (
                ann.non_populist_reason
                or "INCEpTION review removed the evidenced Us or Frontier side")
            ann.us = []
            ann.frontier = []

    from laclaugpt_interchange import to_jsonl as _to
    _to(list(annotations.values()), out_path)
    return {"updated": updated, "new_elements": new,
            "out": out_path}