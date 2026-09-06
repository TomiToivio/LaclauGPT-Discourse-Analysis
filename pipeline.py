# -*- coding: utf-8 -*-
"""Paper-aligned LaclauGPT pipeline.

Flow: source-grounded summary -> Laclaudian discourse coding -> descriptive
extraction -> optional Formula of Populism diagnosis -> provisional JSONL.
All model coding remains explicitly pending human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from laclaugpt_interchange import (
    SCHEMA_VERSION,
    Affect, Articulation, Discourse, DocumentAnnotation, FormationAssessment,
    MemoryRef, PopulismElementAssessment, SignifierRole,
    SociotechnicalImaginary, to_jsonl,
)
from laclaugpt_memory import Memory
from llm import chat_structured, model_digest, resolve_endpoint
from prompts import discourse as discourse_prompt
from prompts import populism as populism_prompt
from prompts import postprocess as postprocess_prompt
from prompts import source_metadata as sm
from prompts import summary as summary_prompt
from prompts import topic_background as tb
from run_config import RunConfig, get_run

logger = logging.getLogger("laclaugpt")
SUMMARY_PROMPT_VERSION = "summary-v2.1"
POSTPROCESS_PROMPT_VERSION = "postprocess-v2.1"   # v2.1: spaCy NER types
SOURCE_TEXT_FIELDS = (
    "text", "body", "content", "transcript", "caption", "description",
    "ocr", "ocr_text", "ethnography_notes", "researcher_notes",
)


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "pipeline.log", encoding="utf-8", maxBytes=1_000_000,
        backupCount=5,
    )
    logging.basicConfig(
        level=logging.INFO, handlers=[handler],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _row_dict(row: Any) -> dict[str, Any]:
    raw = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    return {
        str(k): (None if _is_missing(v) else v)
        for k, v in raw.items()
    }


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        import pandas as pd
        return bool(pd.isna(value))
    except Exception:
        return False


def document_key(row: Any) -> str:
    """Return a stable non-empty key for social, web, and ethnography rows."""
    data = _row_dict(row)
    for field in (
        "document_id", "id", "post_id", "video_id", "videoId", "url",
        "source_url", "filename",
    ):
        value = str(data.get(field) or "").strip()
        if value:
            platform = str(data.get("platform") or data.get("source_platform") or "document")
            return f"{platform}::{value}"
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return "document::" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


# Backward-compatible name used by older utilities.
video_key = document_key


def source_text(row: Any) -> str:
    """Collect only actual source fields; never analyse an empty cache context."""
    data = _row_dict(row)
    chunks = []
    for field in SOURCE_TEXT_FIELDS:
        value = str(data.get(field) or "").strip()
        if value:
            chunks.append(f"[{field}]\n{value}")
    return "\n\n".join(chunks)


def evidence_source(quote: str, row: Any) -> str:
    """Locate a verbatim model quote in the original source column."""
    needle = " ".join((quote or "").casefold().split()).strip(' "“”')
    if not needle:
        return ""
    data = _row_dict(row)
    for field in SOURCE_TEXT_FIELDS:
        value = " ".join(str(data.get(field) or "").casefold().split())
        if needle in value:
            return field
    frame = " ".join(str(data.get("frame_analysis") or "").casefold().split())
    return "frame_analysis" if needle in frame else ""


def source_provenance(row: Any) -> tuple[list[str], dict[str, Any]]:
    """Describe available modalities and declared source transformations."""
    data = _row_dict(row)
    modalities = []
    if any(data.get(field) for field in ("text", "body", "content", "caption", "description")):
        modalities.append("text")
    if data.get("transcript"):
        modalities.append("speech_transcript")
    if data.get("ocr") or data.get("ocr_text"):
        modalities.append("ocr")
    if data.get("frame_analysis"):
        modalities.append("image_description")
    if data.get("ethnography_notes") or data.get("researcher_notes"):
        modalities.append("researcher_fieldnote")
    transformation_fields = (
        "asr_engine", "asr_model", "transcription_model", "translator",
        "translation_model", "source_language", "translation_language",
        "ocr_engine", "ocr_model", "frame_model",
    )
    transformations = {
        field: data[field] for field in transformation_fields if data.get(field)
    }
    return modalities, transformations


def analytic_hints_text(run: RunConfig) -> str:
    if run.ablate_hints:
        return ("(seed hints ablated for priming control: no ideological "
                "seed labels are supplied; paper §3.6)")
    lines = []
    for kind, values in run.analytic_hints.items():
        if values:
            lines.append(f"- {kind}: {', '.join(values)}")
    return "\n".join(lines) or "(none)"


def evidence_is_in_source(quote: str, text: str) -> bool:
    """Mechanical hallucination gate for verbatim evidence spans."""
    def normalise(value: str) -> str:
        return " ".join((value or "").casefold().split()).strip(' "“”')

    needle = normalise(quote)
    return bool(needle) and needle in normalise(text)


def source_description(run: RunConfig, row: Any) -> sm.SourceMetadata:
    data = _row_dict(row)
    language = str(data.get("language") or "")
    platform = str(data.get("platform") or data.get("source_platform") or "")
    spec = run.source_for_row(language, platform)
    metadata_fields = (
        "author", "author_username", "speaker", "timestamp", "created_at",
        "date", "url", "source_url", "document_id", "id", "video_id",
    )
    return sm.SourceMetadata(
        platform=platform or spec.platform,
        country=str(data.get("country") or data.get("scrapedCountry") or spec.country),
        language=language or spec.language,
        collection=spec.query or "researcher-provided corpus row",
        has_metadata=any(data.get(field) for field in metadata_fields),
        notes=spec.notes,
    )


class Stage:
    """Versioned SQLite cache; prompt/model/config changes invalidate entries."""

    def __init__(self, run: RunConfig, memory: Memory, stage_name: str,
                 prompt_version: str):
        self.run = run
        self.memory = memory
        self.stage_name = stage_name
        self.prompt_version = prompt_version
        run.database_dir.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(run.database_dir / f"{stage_name}.db")
        self.table = f"{stage_name}_v2"
        self.conn.execute(f"""CREATE TABLE IF NOT EXISTS {self.table} (
            cache_key TEXT PRIMARY KEY,
            document_key TEXT NOT NULL,
            result TEXT NOT NULL,
            run_id TEXT NOT NULL,
            model TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        self.conn.commit()

    def fingerprint(self, key: str, system: str, user: str) -> str:
        payload = {
            "document_key": key,
            "run": self.run.fingerprint_payload(),
            "stage": self.stage_name,
            "prompt_version": self.prompt_version,
            # model name alone is insufficient (paper §3.3): the digest
            # invalidates caches when the same tag resolves to a new build,
            # and the schema version invalidates them on schema migration.
            "model_digest": model_digest(self.run.model_text),
            "schema_version": SCHEMA_VERSION,
            "system": system,
            "user": user,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def cached(self, cache_key: str) -> str | None:
        row = self.conn.execute(
            f"SELECT result FROM {self.table} WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        return row[0] if row else None

    def call(self, key: str, system: str, user: str, model_cls: type):
        cache_key = self.fingerprint(key, system, user)
        cached = self.cached(cache_key)
        if cached:
            return model_cls.model_validate_json(cached)
        result = chat_structured(
            self.run.model_text, system, user, model_cls,
            {
                "temperature": self.run.temperature,
                "num_ctx": self.run.num_ctx,
                "num_predict": self.run.num_predict,
            },
        )
        raw = result.model_dump_json()
        self.conn.execute(
            f"INSERT INTO {self.table} VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                cache_key, key, raw, self.run.run_id, self.run.model_text,
                self.prompt_version,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        self.conn.commit()
        return result

    def close(self) -> None:
        self.conn.close()


class SummaryStage(Stage):
    def __init__(self, run: RunConfig, memory: Memory):
        super().__init__(run, memory, "summary", SUMMARY_PROMPT_VERSION)

    def run_row(self, row: Any, text: str, metadata: sm.SourceMetadata):
        topic = tb.topic_background(self.run.topic_key)
        system = summary_prompt.build_system_prompt(
            topic, metadata.prompt_text(), self.memory.context_prompt_block(text),
        )
        data = _row_dict(row)
        user = summary_prompt.build_user_prompt(
            frame_analysis=str(data.get("frame_analysis") or ""),
            metadata=json.dumps(data, ensure_ascii=False, default=str),
            transcript=text,
            ocr_results=str(data.get("ocr") or data.get("ocr_text") or ""),
        )
        return self.call(document_key(row), system, user, summary_prompt.pydantic_models())


class DiscourseStage(Stage):
    def __init__(self, run: RunConfig, memory: Memory):
        super().__init__(run, memory, "discourse", discourse_prompt.PROMPT_VERSION)

    def run_row(self, row: Any, text: str, summary_json: str,
                metadata: sm.SourceMetadata) -> dict:
        key = document_key(row)
        system = discourse_prompt.build_system_prompt(
            tb.topic_background(self.run.topic_key), metadata.prompt_text(),
            analytic_hints_text(self.run), self.memory.context_prompt_block(text),
        )
        user = discourse_prompt.build_user_prompt(
            text, json.dumps(_row_dict(row), ensure_ascii=False, default=str), summary_json,
        )
        result = self.call(key, system, user, discourse_prompt.pydantic_models())

        signifiers = []
        by_raw: dict[str, dict] = {}
        for coding in result.signifiers:
            resolved = self.memory.resolve(
                coding.term, "signifier", stage="discourse", video_key=key,
                evidence=coding.evidence_quote, model=self.run.model_text,
            )
            item = {
                "obj_id": resolved.obj_id, "label": resolved.label,
                "kind": "signifier", "raw": coding.term, "role": coding.role,
                "rationale": coding.rationale, "evidence": coding.evidence_quote,
                "confidence": coding.confidence,
                "needs_corpus_validation": coding.needs_corpus_validation,
                "evidence_verified": bool(evidence_source(coding.evidence_quote, row)),
                "evidence_source": evidence_source(coding.evidence_quote, row),
            }
            signifiers.append(item)
            by_raw[coding.term.casefold()] = item

        articulations = []
        for coding in result.articulations:
            refs = []
            for raw in (coding.source, coding.target):
                existing = by_raw.get(raw.casefold())
                if existing is None:
                    resolved = self.memory.resolve(
                        raw, "signifier", stage="discourse", video_key=key,
                        evidence=coding.evidence_quote, model=self.run.model_text,
                    )
                    existing = {
                        "obj_id": resolved.obj_id, "label": resolved.label,
                        "kind": "signifier", "raw": raw,
                    }
                    by_raw[raw.casefold()] = existing
                refs.append(existing)
            self.memory.record_relation(
                refs[0]["obj_id"], refs[1]["obj_id"], coding.relation,
                source_ref=key,
            )
            articulations.append({
                "source": refs[0], "target": refs[1], "relation": coding.relation,
                "rationale": coding.rationale, "evidence": coding.evidence_quote,
                "confidence": coding.confidence,
                "claim_status": coding.claim_status,
                "evidence_verified": bool(evidence_source(coding.evidence_quote, row)),
                "evidence_source": evidence_source(coding.evidence_quote, row),
            })

        formations = []
        for coding in result.formation_candidates:
            resolved = self.memory.resolve(
                coding.label, "formation", stage="discourse", video_key=key,
                evidence=coding.evidence_quote, model=self.run.model_text,
            )
            formations.append({
                "obj_id": resolved.obj_id, "label": resolved.label,
                "kind": "formation", "raw": coding.label,
                "supporting_features": coding.supporting_features,
                "counter_evidence": coding.counter_evidence,
                "evidence": coding.evidence_quote, "confidence": coding.confidence,
                "evidence_verified": bool(evidence_source(coding.evidence_quote, row)),
                "evidence_source": evidence_source(coding.evidence_quote, row),
            })
        return {
            "applicable": result.applicable,
            "applicability_reason": result.applicability_reason,
            "signifiers": signifiers,
            "articulations": articulations,
            "imaginaries": [
                {**x.model_dump(),
                 "evidence_verified": bool(evidence_source(x.evidence_quote, row)),
                 "evidence_source": evidence_source(x.evidence_quote, row)}
                for x in result.imaginaries
            ],
            "formation_candidates": formations,
            "hegemonic_evidence": result.hegemonic_evidence,
            "uncertainties": result.uncertainties,
        }


class PostprocessStage(Stage):
    def __init__(self, run: RunConfig, memory: Memory):
        super().__init__(run, memory, "postprocess", POSTPROCESS_PROMPT_VERSION)

    def run_row(self, row: Any, text: str, summary_json: str) -> dict:
        key = document_key(row)
        system = postprocess_prompt.build_system_prompt(
            self.memory.context_prompt_block(text, kinds=("topic", "entity", "target"))
        )
        Extraction = postprocess_prompt.pydantic_models()
        result = self.call(
            key, system, f"Source material:\n{text}\n\nAnalysis:\n{summary_json}", Extraction,
        )
        out = {}
        groups = {
            "topics": (list(result.topics) + list(result.new_topics), "topic"),
            "entities": (list(result.entities) + list(result.new_entities), "entity"),
            "positive": (list(result.positive), "target"),
            "neutral": (list(result.neutral), "target"),
            "negative": (list(result.negative), "target"),
        }
        # entity_types[i] classifies result.entities[i]; new_entities have no
        # LLM-assigned type (empty kind_type until human review assigns one)
        ner_by_index = list(result.entity_types or [])
        n_matched = len(result.entities)
        for name, (values, kind) in groups.items():
            refs = []
            for raw in dict.fromkeys(v for v in values if v and v.strip()):
                type_ = ""
                if kind == "entity":
                    try:
                        idx = list(result.entities).index(raw)
                    except ValueError:
                        idx = -1
                    if 0 <= idx < n_matched and idx < len(ner_by_index):
                        type_ = ner_by_index[idx] or ""
                resolved = self.memory.resolve(
                    raw, kind, stage="postprocess", video_key=key,
                    evidence=text[:500], model=self.run.model_text,
                    type_=type_,
                )
                refs.append({
                    "obj_id": resolved.obj_id, "label": resolved.label,
                    "kind": kind, "raw": raw, "decision": resolved.decision,
                    "ner_type": type_,
                })
            out[name] = refs
        return out


class PopulismStage(Stage):
    def __init__(self, run: RunConfig, memory: Memory):
        super().__init__(run, memory, "populism", populism_prompt.PROMPT_VERSION)

    def run_row(self, row: Any, text: str, summary_json: str,
                discourse: dict, metadata: sm.SourceMetadata) -> dict:
        key = document_key(row)
        system = populism_prompt.build_system_prompt(
            tb.topic_background(self.run.topic_key), metadata.prompt_text(),
            self.memory.context_prompt_block(text, kinds=("signifier", "target")),
        )
        user = (
            f"SOURCE MATERIAL:\n{text}\n\nPRELIMINARY SUMMARY:\n{summary_json}"
            f"\n\nDISCOURSE CODING:\n{json.dumps(discourse, ensure_ascii=False)}"
        )
        _, Formula = populism_prompt.pydantic_models()
        result = self.call(key, system, user, Formula)
        if not result.populist:
            return {
                "populist": False, "non_populist_reason": result.non_populist_reason,
                "populism_analysis": result.populism_analysis,
                "populism_us": [], "populism_frontier": [],
                "counter_evidence": result.counter_evidence,
                "uncertainties": result.uncertainties,
            }

        def resolve_side(items):
            out = []
            for item in items:
                resolved = self.memory.resolve(
                    item.populism_element, "signifier", stage="populism",
                    video_key=key, evidence=item.evidence_quote,
                    model=self.run.model_text,
                )
                out.append({
                    "obj_id": resolved.obj_id, "label": resolved.label,
                    "kind": "signifier", "raw": item.populism_element,
                    "affect": item.populism_affect,
                    "evidence": item.evidence_quote,
                    "confidence": item.confidence,
                    "nodal": item.nodal_candidate,
                    "empty_candidate": item.empty_candidate,
                    "evidence_verified": bool(evidence_source(item.evidence_quote, row)),
                    "evidence_source": evidence_source(item.evidence_quote, row),
                })
            return out

        return {
            "populist": True, "non_populist_reason": "",
            "populism_analysis": result.populism_analysis,
            "populism_us": resolve_side(result.populism_us),
            "populism_frontier": resolve_side(result.populism_frontier),
            "counter_evidence": result.counter_evidence,
            "uncertainties": result.uncertainties,
        }


def _ref(item: dict) -> MemoryRef:
    return MemoryRef(
        obj_id=item["obj_id"], label=item["label"], kind=item["kind"],
        raw=item.get("raw", ""), ner_type=item.get("ner_type", ""),
    )


def build_annotation(run: RunConfig, row: Any, summary_json: str,
                     discourse: dict, extracted: dict, populism: dict) -> DocumentAnnotation:
    data = _row_dict(row)
    modalities, transformations = source_provenance(row)
    ann = DocumentAnnotation(
        document_id=document_key(row),
        source_platform=str(data.get("platform") or data.get("source_platform") or ""),
        source_country=str(data.get("country") or data.get("scrapedCountry") or ""),
        language=str(data.get("language") or ""),
        model=run.model_text,
        model_digest=model_digest(run.model_text),
        run_id=run.run_id,
        summary=summary_json,
        populist=populism.get("populist"),
        populism_analysis=populism.get("populism_analysis", ""),
        non_populist_reason=populism.get("non_populist_reason", ""),
        uncertainties=list(discourse.get("uncertainties", [])) + list(populism.get("uncertainties", [])),
        hegemonic_evidence=discourse.get("hegemonic_evidence", []),
        prompt_versions={
            "summary": SUMMARY_PROMPT_VERSION,
            "discourse": discourse_prompt.PROMPT_VERSION,
            "postprocess": POSTPROCESS_PROMPT_VERSION,
            "populism": populism_prompt.PROMPT_VERSION,
        },
        source_author=str(data.get("author") or data.get("author_username") or data.get("speaker") or ""),
        source_timestamp=str(data.get("timestamp") or data.get("created_at") or data.get("date") or ""),
        source_url=str(data.get("source_url") or data.get("url") or ""),
        parent_id=str(data.get("parent_id") or data.get("conversation_id") or ""),
        sequence_index=str(data.get("sequence_index") or data.get("segment_index") or ""),
        source_modalities=modalities,
        transformations=transformations,
        counter_evidence=list(populism.get("counter_evidence", [])),
        collection_provenance={
            "config": str(run.config_path or ""),
            "paper_section": run.paper_section,
            "collector": str(data.get("collector") or data.get("collection_method") or ""),
            "run_config": run.fingerprint_payload(),
            "source_spec": run.source_for_row(
                str(data.get("language") or ""),
                str(data.get("platform") or data.get("source_platform") or ""),
            ).__dict__,
        },
    )
    ann.entities = [_ref(x) for x in extracted.get("entities", [])]
    ann.topics = [_ref(x) for x in extracted.get("topics", [])]
    ann.signifiers = [_ref(x) for x in discourse.get("signifiers", [])]
    ann.signifier_roles = [
        SignifierRole(
            signifier=_ref(x), role=x["role"], rationale=x["rationale"],
            evidence=x["evidence"], confidence=x["confidence"],
            evidence_source=x.get("evidence_source", ""),
            needs_corpus_validation=x["needs_corpus_validation"],
            evidence_verified=x.get("evidence_verified", False),
        ) for x in discourse.get("signifiers", [])
    ]
    ann.nodal_points = [
        _ref(x) for x in discourse.get("signifiers", [])
        if x.get("role") == "nodal_candidate"
    ]
    ann.articulations = [
        Articulation(
            signifier=_ref(x["source"]), related_to=[_ref(x["target"])],
            relation=x["relation"], evidence=x["evidence"],
            evidence_source=x.get("evidence_source", ""),
            evidence_verified=x.get("evidence_verified", False),
            claim_status=x.get("claim_status", "asserted"),
            confidence=x.get("confidence", 0.0), rationale=x.get("rationale", ""),
        ) for x in discourse.get("articulations", [])
    ]
    ann.imaginaries = [
        SociotechnicalImaginary(
            label=x["label"], normative_future=x["normative_future"],
            present_diagnosis=x["present_diagnosis"], technology_role=x["technology_role"],
            human_agency=x["human_agency"], evidence=x["evidence_quote"],
            evidence_source=x.get("evidence_source", ""),
            confidence=x["confidence"], claim_status=x.get("claim_status", "asserted"),
            evidence_verified=x.get("evidence_verified", False),
        ) for x in discourse.get("imaginaries", [])
    ]
    ann.formation_candidates = [
        FormationAssessment(
            formation=_ref(x), supporting_features=x["supporting_features"],
            counter_evidence=x["counter_evidence"], evidence=x["evidence"],
            evidence_source=x.get("evidence_source", ""),
            confidence=x["confidence"],
            evidence_verified=x.get("evidence_verified", False),
        ) for x in discourse.get("formation_candidates", [])
    ]
    ann.counter_evidence = list(dict.fromkeys(
        ann.counter_evidence
        + [item for formation in ann.formation_candidates for item in formation.counter_evidence]
    ))
    ann.discourses = [
        Discourse(label=x["label"], confidence=x["confidence"], elements=ann.signifiers)
        for x in discourse.get("formation_candidates", [])
    ]
    us_items = populism.get("populism_us", [])
    frontier_items = populism.get("populism_frontier", [])
    ann.us = [_ref(x) for x in us_items]
    ann.frontier = [_ref(x) for x in frontier_items]
    ann.nodal_points.extend(_ref(x) for x in us_items + frontier_items if x.get("nodal"))
    ann.populism_elements = [
        PopulismElementAssessment(
            element=_ref(x), side=side, affect=x.get("affect", ""),
            evidence=x.get("evidence", ""),
            evidence_source=x.get("evidence_source", ""),
            evidence_verified=x.get("evidence_verified", False),
            confidence=x.get("confidence", 0.0),
            nodal_candidate=x.get("nodal", False),
            empty_candidate=x.get("empty_candidate", False),
        )
        for side, items in (("us", us_items), ("frontier", frontier_items))
        for x in items
    ]
    ann.affects = [
        Affect(
            target=_ref(x), affect=x["affect"], side=side,
            evidence=x.get("evidence", ""),
            evidence_source=x.get("evidence_source", ""),
            evidence_verified=x.get("evidence_verified", False),
            confidence=x.get("confidence", 0.0),
        )
        for side, items in (("us", us_items), ("frontier", frontier_items))
        for x in items if x.get("affect")
    ]
    ann.evidence_quotes = list(dict.fromkeys(
        [x.get("evidence", "") for x in discourse.get("signifiers", [])]
        + [x.get("evidence", "") for x in discourse.get("articulations", [])]
        + [x.get("evidence_quote", "") for x in discourse.get("imaginaries", [])]
        + [x.get("evidence", "") for x in discourse.get("formation_candidates", [])]
        + [x.get("evidence", "") for x in us_items + frontier_items]
    ))
    ann.evidence_quotes = [q for q in ann.evidence_quotes if q]
    invalid_count = sum(not x.evidence_verified for x in ann.signifier_roles)
    invalid_count += sum(not x.evidence_verified for x in ann.articulations)
    invalid_count += sum(not x.evidence_verified for x in ann.imaginaries)
    invalid_count += sum(not x.evidence_verified for x in ann.formation_candidates)
    invalid_count += sum(not x.evidence_verified for x in ann.populism_elements)
    if invalid_count:
        ann.uncertainties.append(
            f"{invalid_count} discourse evidence quote(s) were not found verbatim in the source"
        )
    return ann


def run_pipeline(run_id: str, csv_path: str, dry_run: bool = False,
                 output_path: str | None = None) -> list[DocumentAnnotation]:
    import pandas as pd

    run = get_run(run_id)
    setup_logging(run.log_dir)
    # machine-tier routing: YAML/env decides local vs cloud Ollama.
    # YAML values are applied as env defaults (explicit env still wins).
    if run.ollama_mode in ("local", "cloud", "external", "auto"):
        os.environ.setdefault("LLM_MODE", run.ollama_mode)
    if run.ollama_host:
        os.environ.setdefault("OLLAMA_HOST", run.ollama_host)
    _, run.model_text = resolve_endpoint(run.model_text)
    _, run.model_vision = resolve_endpoint(run.model_vision)
    from llm import describe_routing
    logger.info("LLM routing: %s", describe_routing(run.model_text))
    df = pd.read_csv(csv_path)
    if run.languages and "language" in df.columns:
        df = df[df["language"].isin(run.languages)]
    if df.empty:
        raise ValueError("no input rows remain after language filtering")
    empty = [document_key(row) for _, row in df.iterrows() if not source_text(row)]
    if empty:
        raise ValueError(f"{len(empty)} row(s) contain no analysable source text; first: {empty[0]}")
    if dry_run:
        print(json.dumps({
            "run_id": run.run_id, "rows": len(df), "stages": list(run.stages),
            "model": run.model_text, "temperature": run.temperature,
            "output": str(output_path or run.output_path),
        }, ensure_ascii=False, indent=2))
        return []

    stages = set(run.stages)
    if "summary" not in stages or "discourse" not in stages:
        raise ValueError("paper-aligned runs require summary and discourse stages")
    memory_dir = os.environ.get("LACLAUGPT_MEMORY_DIR")
    memory = Memory(
        memory_dir=memory_dir or (str(run.memory_dir) if run.memory_dir else str(run.database_dir / "memory")),
        fuzzy_topic=run.dedup_fuzzy_topic,
        fuzzy_entity=run.dedup_fuzzy_entity,
        promote_threshold=run.glossary_lock_threshold,
        max_context_items=run.glossary_max_lines,
    )
    summary_stage = SummaryStage(run, memory)
    discourse_stage = DiscourseStage(run, memory)
    post_stage = PostprocessStage(run, memory) if "postprocess" in stages else None
    pop_stage = PopulismStage(run, memory) if "populism" in stages else None
    annotations = []
    try:
        for _, row in df.iterrows():
            text = source_text(row)
            metadata = source_description(run, row)
            summary_result = summary_stage.run_row(row, text, metadata)
            summary_json = summary_result.model_dump_json()
            discourse = discourse_stage.run_row(row, text, summary_json, metadata)
            extracted = post_stage.run_row(row, text, summary_json) if post_stage else {}
            populism = (
                pop_stage.run_row(row, text, summary_json, discourse, metadata)
                if pop_stage else {"populist": None}
            )
            ann = build_annotation(run, row, summary_json, discourse, extracted, populism)
            annotations.append(ann)
            memory.record_analysis(
                ann.document_id, "pipeline", ann.model_dump(mode="json"),
                evidence=" | ".join(ann.evidence_quotes[:3]),
            )
    finally:
        summary_stage.close()
        discourse_stage.close()
        if post_stage:
            post_stage.close()
        if pop_stage:
            pop_stage.close()

    destination = Path(output_path) if output_path else run.output_path
    if destination is None:
        destination = run.log_dir / "annotations.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    to_jsonl(annotations, str(destination))
    synthesis = corpus_synthesis(annotations, Path(destination).with_suffix(".corpus.json"))
    run.log_dir.mkdir(parents=True, exist_ok=True)
    memory.export_review_csv(str(run.log_dir / "glossary_review.csv"))
    memory.record_analysis(
        "run", "pipeline-run",
        {"run_id": run.run_id, "rows": len(annotations), "output": str(destination),
         "corpus_synthesis": synthesis},
    )
    memory.close()
    print(f"wrote {len(annotations)} provisional annotations to {destination}")
    return annotations


def corpus_synthesis(annotations: list[DocumentAnnotation],
                     output_path: Path | None = None) -> dict:
    """Workflow stage 6 (paper §3.3): corpus-level descriptive synthesis.

    Produces ONLY descriptive counts and candidate flags — never corpus-level
    theoretical claims. Floating/empty signifier status and hegemony remain
    human judgements; this module only assembles the comparable evidence:
    - signifier frequency and arena spread (how many documents per arena
      nominate the signifier, and in which roles)
    - floating-signifier candidates with their per-arena role distribution
      (comparative evidence a human needs to adjudicate floating status)
    - nodal/empty candidates and their evidence counts
    - articulation relation frequencies (equivalence/difference/antagonism)
    """
    signifier_docs: dict[str, set] = {}
    signifier_roles: dict[str, dict[str, int]] = {}
    for ann in annotations:
        for role in ann.signifier_roles:
            if not role.evidence_verified:
                continue
            key = role.signifier.obj_id or role.signifier.label
            signifier_docs.setdefault(key, set()).add(ann.document_id)
            roles = signifier_roles.setdefault(key, {})
            roles[role.role] = roles.get(role.role, 0) + 1

    relation_counts: dict[str, int] = {}
    for ann in annotations:
        for art in ann.articulations:
            if not art.evidence_verified:
                continue
            relation_counts[art.relation] = relation_counts.get(art.relation, 0) + 1

    floating_candidates = []
    for ann in annotations:
        for role in ann.signifier_roles:
            if role.role == "floating_candidate" and role.evidence_verified:
                key = role.signifier.obj_id or role.signifier.label
                floating_candidates.append({
                    "obj_id": role.signifier.obj_id,
                    "label": role.signifier.label,
                    "document_id": ann.document_id,
                    "evidence": role.evidence,
                    "needs_corpus_validation": role.needs_corpus_validation,
                })

    empty_candidates = []
    nodal_candidates = []
    for key, roles in signifier_roles.items():
        if roles.get("empty_candidate"):
            empty_candidates.append(key)
        if roles.get("nodal_candidate"):
            nodal_candidates.append(key)

    synthesis = {
        "documents": len(annotations),
        "signifier_frequency": {
            key: len(docs) for key, docs in sorted(signifier_docs.items())
        },
        "signifier_roles": signifier_roles,
        "articulation_relations": relation_counts,
        "floating_candidates": floating_candidates,
        "empty_candidates": empty_candidates,
        "nodal_candidates": nodal_candidates,
        "note": ("Descriptive corpus synthesis only. Floating/empty status and "
                 "hegemony are human adjudications over this evidence, never "
                 "automated findings (paper §3.3 stage 6)."),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(synthesis, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return synthesis


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-config", help="YAML arena config")
    group.add_argument("--run", help="legacy registered run id")
    ap.add_argument("--csv", required=True)
    ap.add_argument("--output")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run_pipeline(args.run_config or args.run, args.csv, args.dry_run, args.output)
