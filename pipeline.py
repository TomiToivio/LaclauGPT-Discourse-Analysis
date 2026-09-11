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
import tempfile
from contextlib import ExitStack
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Iterable

from laclaugpt_interchange import (
    SCHEMA_VERSION,
    Affect, Articulation, Discourse, DocumentAnnotation, FormationAssessment,
    MemoryRef, PopulismElementAssessment, SentimentObservation, SignifierRole,
    SociotechnicalImaginary, to_jsonl,
)
from laclaugpt_memory import KINDS, Memory
from llm import chat_structured, model_digest, resolve_endpoint

try:  # stage-aware local model routing (AI26 local GPU); absent in older checkouts
    from laclaugpt.model_routing import pick_model as _stage_pick_model
except ImportError:  # pragma: no cover
    _stage_pick_model = None
from prompts import discourse as discourse_prompt
from prompts import populism as populism_prompt
from prompts import postprocess as postprocess_prompt
from prompts import source_metadata as sm
from prompts import summary as summary_prompt
from prompts import topic_background as tb
from run_config import RunConfig, get_run

logger = logging.getLogger("laclaugpt")
SUMMARY_PROMPT_VERSION = summary_prompt.PROMPT_VERSION
POSTPROCESS_PROMPT_VERSION = postprocess_prompt.PROMPT_VERSION
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


def _staging_path(destination: Path) -> Path:
    """Create a uniquely named sibling file that is visibly incomplete.

    A hard process crash may leave this file behind, but the ``.partial``
    suffix makes it impossible to mistake for a completed research artifact.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".partial",
        dir=str(destination.parent),
    )
    os.close(fd)
    return Path(raw)


def _cleanup_staged(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("could not remove staged artifact %s", path, exc_info=True)


MACHINE_CSV_COLUMNS = (
    # Legacy-dashboard parity subset: one flat row per document so the EP24
    # review workflow (and pandas) can load results without JSONL parsing.
    "document_id", "relevance", "relevance_reason", "review_status",
    "populist", "language", "source_platform", "source_country",
    "summary", "evidence_quotes", "signifiers", "nodal_points",
    "uncertainties", "run_id", "schema_version",
)


def export_machine_csv(annotations: list[DocumentAnnotation],
                       path: str) -> str:
    """Flat machine-readable CSV (one row per annotated document)."""
    import csv as _csv
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = _csv.writer(fh)
        writer.writerow(MACHINE_CSV_COLUMNS)
        for ann in annotations:
            writer.writerow([
                ann.document_id,
                ann.relevance or "",
                ann.relevance_reason,
                ann.review_status,
                "" if ann.populist is None else str(ann.populist).lower(),
                ann.language, ann.source_platform, ann.source_country,
                ann.summary,
                " | ".join(ann.evidence_quotes),
                "; ".join(s.label for s in ann.signifiers),
                "; ".join(s.label for s in ann.nodal_points),
                " | ".join(ann.uncertainties),
                ann.run_id, ann.schema_version,
            ])
    return path


def export_discourse_graph(annotations: list[DocumentAnnotation],
                           path: str, *, run: RunConfig | None = None) -> str:
    """Canonical discourse-graph projection (docs/DISCOURSE_GRAPH_SCHEMA.md).

    Deterministic evidence-linked projection over the run's annotations:
    documents, signifiers, role assignments, Palonen Us/Frontier/affect
    nodes and SUPPORTED_BY evidence edges. Written for Gephi/GraphML-style
    downstream tooling; carries provenance per the schema contract.
    """
    from laclaugpt.graph import build_discourse_graph
    graph = build_discourse_graph(annotations)
    if run is not None:
        graph.metadata.setdefault("run_id", run.run_id)
        graph.metadata.setdefault("project", getattr(run, "project", ""))
        graph.metadata.setdefault("arena", getattr(run, "arena", ""))
    payload = graph.to_dict()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return path


def write_human_report(annotations: list[DocumentAnnotation],
                       synthesis: dict, path: str, *,
                       run: RunConfig | None = None) -> str:
    """Human-readable run report (markdown), legacy-summary parity.

    One section per document: summary, populism verdict, key codings and
    uncertainties — plus the run-level relevance/review bookkeeping.
    """
    relevant = [a for a in annotations if a.relevance != "irrelevant"]
    irrelevant = [a for a in annotations if a.relevance == "irrelevant"]
    project_label = (
        (run.project or run.analysis_profile).upper()
        if run is not None and (run.project or run.analysis_profile)
        else "LaclauGPT"
    )
    lines: list[str] = [
        f"# {project_label} analysis report",
        "",
        f"Documents: {len(annotations)} "
        f"({len(relevant)} retained, {len(irrelevant)} marked irrelevant)",
        f"Review queue: {sum(1 for a in annotations if a.requires_human_review)} "
        "provisional annotations need human review",
        "",
        "## Corpus synthesis (descriptive only)",
        "",
        f"- documents in synthesis: {synthesis.get('documents')}",
        f"- signifier families: {len(synthesis.get('signifier_frequency', {}))}",
        f"- floating candidates: {len(synthesis.get('floating_candidates', []))}",
        f"- empty candidates: {len(synthesis.get('empty_candidates', []))}",
        f"- nodal candidates: {len(synthesis.get('nodal_candidates', []))}",
        "",
        "> Frequency is not hegemony; candidate rows need human adjudication.",
        "",
    ]
    for ann in annotations:
        lines += [
            f"## {ann.document_id}",
            "",
            f"- relevance: **{ann.relevance or 'not judged'}**"
            + (f" — {ann.relevance_reason}" if ann.relevance_reason else ""),
            f"- review: {ann.review_status}"
            + (" (needs human review)" if ann.requires_human_review else ""),
            f"- populist: {ann.populist}",
            f"- language: {ann.language or '?'} | platform: {ann.source_platform or '?'}",
            "",
            "### Summary",
            "",
            ann.summary or "(no summary)",
            "",
        ]
        if ann.populism_analysis:
            lines += ["### Populism analysis", "", ann.populism_analysis, ""]
        if ann.evidence_quotes:
            lines += ["### Evidence quotes", ""]
            lines += [f"- \"{q}\"" for q in ann.evidence_quotes[:5]]
            lines += [""]
        if ann.uncertainties:
            lines += ["### Uncertainties", ""]
            lines += [f"- {u}" for u in ann.uncertainties[:5]]
            lines += [""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def _prepare_success_artifacts(
    annotations: list[DocumentAnnotation], destination: Path,
    run: RunConfig, memory: Memory,
) -> tuple[dict[str, Any], list[tuple[Path, Path]]]:
    """Render all success artifacts without touching their final paths.

    Failure contract:
    - stage caches, Context Memory decisions and logs may persist because they
      are useful provenance/debug state;
    - annotations, corpus synthesis and review CSV are not published until the
      complete document loop and every render step have succeeded;
    - interrupted temporary files are explicitly named ``*.partial``.
    """
    corpus_destination = destination.with_suffix(".corpus.json")
    review_destination = run.log_dir / "glossary_review.csv"
    # Legacy parity (issue #73): the old dashboard consumed one wide CSV and
    # one human-readable summary per run. Machine CSV = one row per document
    # (flat subset of the JSONL); human report = readable markdown digest.
    machine_csv_destination = destination.with_suffix(".csv")
    report_destination = destination.with_suffix(".report.md")
    # Canonical discourse graph projection (docs/DISCOURSE_GRAPH_SCHEMA.md):
    # evidence-linked graph over the run's annotations for vis/Gephi tooling.
    graph_destination = destination.with_suffix(".graph.json")
    run.log_dir.mkdir(parents=True, exist_ok=True)

    staged_output = _staging_path(destination)
    staged_corpus = _staging_path(corpus_destination)
    staged_review = _staging_path(review_destination)
    staged_machine_csv = _staging_path(machine_csv_destination)
    staged_report = _staging_path(report_destination)
    staged_graph = _staging_path(graph_destination)
    staged = [staged_output, staged_corpus, staged_review,
              staged_machine_csv, staged_report, staged_graph]
    try:
        to_jsonl(annotations, str(staged_output))
        synthesis = corpus_synthesis(annotations, staged_corpus)
        export_machine_csv(annotations, str(staged_machine_csv))
        write_human_report(annotations, synthesis, str(staged_report), run=run)
        export_discourse_graph(annotations, str(staged_graph), run=run)
        memory.export_review_csv(str(staged_review))
        memory.record_analysis(
            "run", "pipeline-run-prepared",
            {
                "run_id": run.run_id,
                "rows": len(annotations),
                "output": str(destination),
                "corpus_synthesis": synthesis,
                "artifact_state": "ready_to_publish",
            },
        )
        return synthesis, [
            (staged_corpus, corpus_destination),
            (staged_review, review_destination),
            (staged_machine_csv, machine_csv_destination),
            (staged_report, report_destination),
            (staged_graph, graph_destination),
            (staged_output, destination),
        ]
    except Exception:
        _cleanup_staged(staged)
        raise


def _publish_success_artifacts(staged: list[tuple[Path, Path]]) -> None:
    """Atomically replace final artifacts; annotation JSONL is published last."""
    pending = [source for source, _ in staged]
    try:
        for source, destination in staged:
            os.replace(source, destination)
            if source in pending:
                pending.remove(source)
    finally:
        _cleanup_staged(pending)


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


def _normalise_quote(value: str) -> str:
    """Shared quote normalisation for the mechanical evidence gates."""
    return " ".join((value or "").casefold().split()).strip(' "“”')


def evidence_source(quote: str, row: Any) -> str:
    """Locate a verbatim model quote in the original source column."""
    needle = _normalise_quote(quote)
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
    """Mechanical hallucination gate for verbatim evidence spans.

    Delegates to the shared normalisation so this gate and
    ``evidence_source()`` can never drift apart (issue #60).
    """
    needle = _normalise_quote(quote)
    return bool(needle) and needle in _normalise_quote(text)


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


def _is_local_gemma4(model: str | None) -> bool:
    """True when the configured model is a local gemma4 tag (not *-cloud/:cloud)."""
    if not model:
        return False
    lowered = model.casefold()
    return lowered.startswith("gemma4:") and not (
        lowered.endswith("-cloud") or lowered.endswith(":cloud"))


class Stage:
    """Versioned SQLite cache with actual-model provenance per stage call."""

    def __init__(self, run: RunConfig, memory: Memory, stage_name: str,
                 prompt_version: str):
        self.run = run
        self.memory = memory
        self.stage_name = stage_name
        self.prompt_version = prompt_version
        self.last_provenance: dict[str, Any] = {}
        run.database_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(run.database_dir / f"{stage_name}.db")
        try:
            self.table = f"{stage_name}_v3"
            conn.execute(f"""CREATE TABLE IF NOT EXISTS {self.table} (
                cache_key TEXT PRIMARY KEY,
                document_key TEXT NOT NULL,
                result TEXT NOT NULL,
                run_id TEXT NOT NULL,
                model TEXT NOT NULL,
                model_digest TEXT NOT NULL,
                mode TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                fallback_reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")
            conn.commit()
        except Exception:
            conn.close()
            raise
        self.conn: sqlite3.Connection | None = conn

    def memory_context(self, text: str, kinds: Iterable[str] = tuple(KINDS)) -> str:
        if not self.run.enabled("context_memory"):
            return "(context memory disabled for this analysis profile)"
        return self.memory.context_prompt_block(text, kinds=kinds)

    def fingerprint(self, key: str, system: str, user: str, *,
                    model: str | None = None, digest: str | None = None,
                    mode: str | None = None) -> str:
        selected_mode, selected_model = resolve_endpoint(model or self.run.model_text)
        selected_model = model or selected_model
        selected_mode = mode or selected_mode
        selected_digest = model_digest(selected_model) if digest is None else digest
        payload = {
            "document_key": key,
            "run": self.run.fingerprint_payload(),
            "stage": self.stage_name,
            "prompt_version": self.prompt_version,
            "model": selected_model,
            "model_mode": selected_mode,
            "model_digest": selected_digest,
            "schema_version": SCHEMA_VERSION,
            "system": system,
            "user": user,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def cached(self, cache_key: str) -> str | None:
        if self.conn is None:
            raise RuntimeError(f"stage {self.stage_name} is closed")
        row = self.conn.execute(
            f"SELECT result, model, model_digest, mode, endpoint, fallback_reason "
            f"FROM {self.table} WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        if not row:
            return None
        result, model, digest, mode, endpoint, fallback_reason = row
        self.last_provenance = {
            "requested_mode": mode,
            "requested_model": model,
            "resolved_model": model,
            "actual_mode": mode,
            "actual_model": model,
            "actual_model_digest": digest,
            "endpoint": endpoint,
            "fallback_used": bool(fallback_reason),
            "fallback_reason": fallback_reason,
            "cache_hit": True,
        }
        return result

    @property
    def actual_model(self) -> str:
        return str(self.last_provenance.get("actual_model") or self.run.model_text)

    def provenance(self) -> dict[str, Any]:
        return dict(self.last_provenance)

    def call(self, key: str, system: str, user: str, model_cls: type):
        if self.conn is None:
            raise RuntimeError(f"stage {self.stage_name} is closed")
        requested_model = self.run.model_text
        # Stage-aware local routing (Tomi's 2026-09-08 rule): resolve the
        # gemma4 tier per pipeline stage when the configured model is a local
        # gemma4 tag. Non-gemma4 (synthetic mocks, cloud tags) stay untouched;
        # resolve_endpoint handles mode/host resolution below either way.
        if _stage_pick_model is not None and _is_local_gemma4(requested_model):
            try:
                requested_model = _stage_pick_model(
                    self.stage_name, len(user) - len(system))
            except Exception as exc:  # pragma: no cover - routing is best-effort
                logger.warning(
                    "stage model routing failed for %s; using %s: %s",
                    self.stage_name, requested_model, exc)
        requested_mode, requested_model = resolve_endpoint(requested_model)
        requested_digest = model_digest(requested_model)
        requested_key = self.fingerprint(
            key, system, user, model=requested_model,
            digest=requested_digest, mode=requested_mode,
        )
        cached = self.cached(requested_key)
        if cached:
            return model_cls.model_validate_json(cached)

        result, provenance = chat_structured(
            requested_model, system, user, model_cls,
            {
                "temperature": self.run.temperature,
                "num_ctx": self.run.num_ctx,
                "num_predict": self.run.num_predict,
            },
            allow_cloud_fallback=self.run.allow_cloud_fallback,
            return_provenance=True,
        )
        self.last_provenance = provenance.to_dict()
        self.last_provenance["cache_hit"] = False
        raw = result.model_dump_json()
        actual_key = self.fingerprint(
            key, system, user,
            model=provenance.actual_model,
            digest=provenance.actual_model_digest,
            mode=provenance.actual_mode,
        )
        self.conn.execute(
            f"INSERT OR REPLACE INTO {self.table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                actual_key, key, raw, self.run.run_id,
                provenance.actual_model, provenance.actual_model_digest,
                provenance.actual_mode, provenance.endpoint,
                self.prompt_version, provenance.fallback_reason,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        self.conn.commit()
        return result

    def close(self) -> None:
        conn, self.conn = self.conn, None
        if conn is not None:
            conn.close()


class SummaryStage(Stage):
    def __init__(self, run: RunConfig, memory: Memory):
        super().__init__(run, memory, "summary", SUMMARY_PROMPT_VERSION)

    def run_row(self, row: Any, text: str, metadata: sm.SourceMetadata):
        topic = tb.topic_background(self.run.topic_key)
        system = summary_prompt.build_system_prompt(
            topic, metadata.prompt_text(), self.memory_context(text),
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
            analytic_hints_text(self.run), self.memory_context(text),
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
                evidence=coding.evidence_quote, model=self.actual_model,
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
                        evidence=coding.evidence_quote, model=self.actual_model,
                    )
                    existing = {
                        "obj_id": resolved.obj_id, "label": resolved.label,
                        "kind": "signifier", "raw": raw,
                    }
                    by_raw[raw.casefold()] = existing
                refs.append(existing)
            if self.run.enabled("temporal"):
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
                evidence=coding.evidence_quote, model=self.actual_model,
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
            "hegemonic_evidence": [
                # INV_HEGEMONY_CORPUS (issue #60): hegemonic evidence passes
                # through the same mechanical verbatim gate as every other
                # coding family instead of riding in as unchecked prose.
                {"quote": quote,
                 "evidence_source": evidence_source(quote, row),
                 "evidence_verified": bool(evidence_source(quote, row))}
                for quote in result.hegemonic_evidence if (quote or "").strip()
            ],
            "uncertainties": result.uncertainties,
        }


class PostprocessStage(Stage):
    def __init__(self, run: RunConfig, memory: Memory):
        super().__init__(run, memory, "postprocess", POSTPROCESS_PROMPT_VERSION)

    def run_row(self, row: Any, text: str, summary_json: str) -> dict:
        key = document_key(row)
        include_topics = self.run.enabled("topics")
        include_entities = self.run.enabled("entities")
        include_sentiment = self.run.enabled("sentiment")
        system = postprocess_prompt.build_system_prompt(
            self.memory_context(text, kinds=("topic", "entity", "target")),
            include_topics=include_topics,
            include_entities=include_entities,
            include_sentiment=include_sentiment,
        )
        Extraction = postprocess_prompt.pydantic_models()
        result = self.call(
            key, system, f"Source material:\n{text}\n\nAnalysis:\n{summary_json}", Extraction,
        )
        out: dict[str, Any] = {}
        groups: dict[str, tuple[list[str], str]] = {}
        if include_topics:
            groups["topics"] = (list(result.topics) + list(result.new_topics), "topic")
        if include_entities:
            groups["entities"] = (list(result.entities) + list(result.new_entities), "entity")

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
                    evidence=text[:500], model=self.actual_model,
                    type_=type_,
                )
                refs.append({
                    "obj_id": resolved.obj_id, "label": resolved.label,
                    "kind": kind, "raw": raw, "decision": resolved.decision,
                    "ner_type": type_,
                })
            out[name] = refs

        out.setdefault("topics", [])
        out.setdefault("entities", [])
        out["sentiment"] = []
        if include_sentiment:
            readings = list(result.sentiments or [])
            if readings:
                for reading in readings:
                    resolved = self.memory.resolve(
                        reading.target, "target", stage="postprocess", video_key=key,
                        evidence=reading.evidence_quote, model=self.actual_model,
                    )
                    source = evidence_source(reading.evidence_quote, row)
                    out["sentiment"].append({
                        "target": {
                            "obj_id": resolved.obj_id,
                            "label": resolved.label,
                            "kind": "target",
                            "raw": reading.target,
                            "decision": resolved.decision,
                            "ner_type": "",
                        },
                        "polarity": reading.polarity,
                        "evidence_source": source,
                        "uncertainty": reading.uncertainty,
                    })
            else:
                # Compatibility fallback for a model response using only the
                # historical polarity target lists. These observations are kept
                # maximally uncertain because no evidence quote was supplied.
                for polarity in ("positive", "neutral", "negative"):
                    for raw in dict.fromkeys(
                        v for v in getattr(result, polarity, []) if v and v.strip()
                    ):
                        resolved = self.memory.resolve(
                            raw, "target", stage="postprocess", video_key=key,
                            evidence=text[:500], model=self.actual_model,
                        )
                        out["sentiment"].append({
                            "target": {
                                "obj_id": resolved.obj_id,
                                "label": resolved.label,
                                "kind": "target",
                                "raw": raw,
                                "decision": resolved.decision,
                                "ner_type": "",
                            },
                            "polarity": polarity,
                            "evidence_source": "postprocess-legacy-list",
                            "uncertainty": 1.0,
                        })
        return out


class PopulismStage(Stage):
    def __init__(self, run: RunConfig, memory: Memory):
        super().__init__(run, memory, "populism", populism_prompt.PROMPT_VERSION)

    def run_row(self, row: Any, text: str, summary_json: str,
                discourse: dict, metadata: sm.SourceMetadata) -> dict:
        key = document_key(row)
        system = populism_prompt.build_system_prompt(
            tb.topic_background(self.run.topic_key), metadata.prompt_text(),
            self.memory_context(text, kinds=("signifier", "target")),
        )
        user = (
            f"SOURCE MATERIAL:\n{text}\n\nPRELIMINARY SUMMARY:\n{summary_json}"
            f"\n\nDISCOURSE CODING:\n{json.dumps(discourse, ensure_ascii=False)}"
        )
        _, Formula = populism_prompt.pydantic_models()
        result = self.call(key, system, user, Formula)

        def resolve_side(items):
            out = []
            for item in items:
                resolved = self.memory.resolve(
                    item.populism_element, "signifier", stage="populism",
                    video_key=key, evidence=item.evidence_quote,
                    model=self.actual_model,
                )
                out.append({
                    "obj_id": resolved.obj_id, "label": resolved.label,
                    "kind": "signifier", "raw": item.populism_element,
                    "affect": item.populism_affect,
                    "evidence": item.evidence_quote,
                    "confidence": item.confidence,
                    "claim_status": item.claim_status,
                    "nodal": item.nodal_candidate,
                    "empty_candidate": item.empty_candidate,
                    "evidence_verified": bool(evidence_source(item.evidence_quote, row)),
                    "evidence_source": evidence_source(item.evidence_quote, row),
                })
            return out

        if not result.populist:
            # Issue #59: an abstention may retain ONE evidenced side as
            # structured document-level candidates instead of discarding
            # partial evidence; the prompt validator forbids both sides here.
            return {
                "populist": False, "non_populist_reason": result.non_populist_reason,
                "populism_analysis": result.populism_analysis,
                "populism_us": resolve_side(result.populism_us),
                "populism_frontier": resolve_side(result.populism_frontier),
                "counter_evidence": result.counter_evidence,
                "uncertainties": result.uncertainties,
            }

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


def _annotation_model(stage_provenance: dict[str, dict[str, Any]],
                      fallback_model: str) -> tuple[str, str]:
    """Return honest top-level model fields for single- or mixed-model runs."""
    rows = [p for p in stage_provenance.values() if p and p.get("actual_model")]
    if not rows:
        return fallback_model, model_digest(fallback_model)
    models = {str(p["actual_model"]) for p in rows}
    if len(models) != 1:
        return "mixed", ""
    model = next(iter(models))
    digests = {str(p.get("actual_model_digest") or "") for p in rows}
    digests.discard("")
    return model, (next(iter(digests)) if len(digests) == 1 else "")


def build_annotation(run: RunConfig, row: Any, summary_json: str,
                     discourse: dict, extracted: dict, populism: dict,
                     stage_provenance: dict[str, dict[str, Any]] | None = None) -> DocumentAnnotation:
    data = _row_dict(row)
    modalities, transformations = source_provenance(row)
    stage_provenance = stage_provenance or {}
    annotation_model, annotation_digest = _annotation_model(stage_provenance, run.model_text)
    # Us/Frontier refs are computed before construction so the interchange
    # INV_POPULISM validator (populist=true requires both sides) sees the
    # final state, not an empty intermediate one.
    us_items = populism.get("populism_us", [])
    frontier_items = populism.get("populism_frontier", [])
    ann = DocumentAnnotation(
        document_id=document_key(row),
        source_platform=str(data.get("platform") or data.get("source_platform") or ""),
        source_country=str(data.get("country") or data.get("scrapedCountry") or ""),
        language=str(data.get("language") or ""),
        model=annotation_model,
        model_digest=annotation_digest,
        run_id=run.run_id,
        summary=summary_json,
        populist=populism.get("populist"),
        populism_analysis=populism.get("populism_analysis", ""),
        non_populist_reason=populism.get("non_populist_reason", ""),
        us=[_ref(x) for x in us_items],
        frontier=[_ref(x) for x in frontier_items],
        discourse_applicable=discourse.get("applicable"),
        discourse_applicability_reason=str(discourse.get("applicability_reason", "")),
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
            "llm_stages": stage_provenance,
            "cloud_fallback_allowed": run.allow_cloud_fallback,
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
            claim_status=x.get("claim_status", "uncertain"),
            confidence=x.get("confidence", 0.0), rationale=x.get("rationale", ""),
        ) for x in discourse.get("articulations", [])
    ]
    ann.imaginaries = [
        SociotechnicalImaginary(
            label=x["label"], normative_future=x["normative_future"],
            present_diagnosis=x["present_diagnosis"], technology_role=x["technology_role"],
            human_agency=x["human_agency"], evidence=x["evidence_quote"],
            evidence_source=x.get("evidence_source", ""),
            confidence=x["confidence"], claim_status=x.get("claim_status", "uncertain"),
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
    postprocess_model = str(
        stage_provenance.get("postprocess", {}).get("actual_model") or annotation_model
    )
    ann.sentiment_observations = [
        SentimentObservation(
            target=_ref(x["target"]),
            polarity=x["polarity"],
            evidence_source=x.get("evidence_source", ""),
            uncertainty=x.get("uncertainty", 0.0),
            model=postprocess_model,
            prompt_version=POSTPROCESS_PROMPT_VERSION,
            review_status="PROVISIONAL",
        )
        for x in extracted.get("sentiment", [])
    ]
    # Discourse membership is a human/corpus adjudication (THEORY.md §13.2):
    # a formation candidate is published as a label with confidence and its
    # own evidence; signifier membership is not fabricated here by assigning
    # every coded signifier to every candidate discourse.
    ann.discourses = [
        Discourse(label=x["label"], confidence=x["confidence"],
                  evidence=x.get("evidence", ""), elements=[])
        for x in discourse.get("formation_candidates", [])
    ]
    ann.nodal_points.extend(_ref(x) for x in us_items + frontier_items if x.get("nodal"))
    ann.populism_elements = [
        PopulismElementAssessment(
            element=_ref(x), side=side, affect=x.get("affect", ""),
            evidence=x.get("evidence", ""),
            evidence_source=x.get("evidence_source", ""),
            evidence_verified=x.get("evidence_verified", False),
            confidence=x.get("confidence", 0.0),
            claim_status=x.get("claim_status", "uncertain"),
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
    # INV_HEGEMONY_CORPUS (issue #60): hegemonic evidence participates in the
    # unverified-evidence tally like every other coding family.
    invalid_count += sum(not x.evidence_verified for x in ann.hegemonic_evidence)
    if invalid_count:
        ann.uncertainties.append(
            f"{invalid_count} discourse evidence quote(s) were not found verbatim in the source"
        )
    _apply_relevance(ann, summary_json, discourse, run)
    return ann


def _apply_relevance(ann: DocumentAnnotation, summary_json: str,
                     discourse: dict, run: RunConfig) -> None:
    """Apply the project's explicit mark-don't-drop relevance policy.

    ``retain_unjudged`` is the safe default for general research projects:
    explicit discourse non-applicability may mark a row irrelevant and
    substantive coded content marks it relevant, but zero-code/borderline rows
    remain unjudged and therefore stay available to corpus synthesis and human
    review. ``keyword_scope`` is an opt-in legacy-style screen whose vocabulary
    comes from project configuration rather than this generic pipeline.
    """
    if ann.discourse_applicable is False:
        ann.relevance = "irrelevant"
        ann.relevance_reason = (
            "discourse stage judged the Laclaudian analysis non-applicable: "
            + ann.discourse_applicability_reason)[:500]
        return

    has_coded_content = bool(
        ann.signifier_roles or ann.articulations or ann.populism_elements
        or ann.us or ann.frontier)
    if has_coded_content:
        ann.relevance = "relevant"
        ann.relevance_reason = ""
        return

    mode = (run.relevance_mode or "retain_unjudged").casefold()
    if mode == "retain_unjudged":
        ann.relevance = None
        ann.relevance_reason = ""
        return
    if mode != "keyword_scope":
        raise ValueError(f"unknown relevance mode: {run.relevance_mode}")

    terms = tuple(term.casefold().strip() for term in run.relevance_terms if term.strip())
    if not terms:
        # A keyword policy with no vocabulary must never silently discard data.
        ann.relevance = None
        ann.relevance_reason = ""
        return

    summary_text = ann.summary or summary_json or ""
    low = summary_text.casefold()
    if any(term in low for term in terms):
        ann.relevance = "relevant"
        ann.relevance_reason = ""
        return

    scope = run.relevance_scope or "configured project scope"
    project = run.project or run.analysis_profile or "project"
    ann.relevance = "irrelevant"
    ann.relevance_reason = (
        f"summary shows no {scope} content and no coding family produced "
        f"evidence ({project} keyword scope gate)"
    )


def run_pipeline(run_id: str | Path | RunConfig, csv_path: str,
                 dry_run: bool = False,
                 output_path: str | None = None) -> list[DocumentAnnotation]:
    import pandas as pd

    run = get_run(run_id)
    setup_logging(run.log_dir)
    if run.ollama_mode in ("local", "cloud", "external", "auto"):
        os.environ.setdefault("LLM_MODE", run.ollama_mode)
    if run.ollama_host:
        os.environ.setdefault("OLLAMA_HOST", run.ollama_host)
    _, run.model_text = resolve_endpoint(run.model_text)
    _, run.model_vision = resolve_endpoint(run.model_vision)
    from llm import describe_routing
    logger.info(
        "LLM routing: %s; cloud fallback allowed=%s",
        describe_routing(run.model_text), run.allow_cloud_fallback,
    )
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
            "allow_cloud_fallback": run.allow_cloud_fallback,
            "output": str(output_path or run.output_path),
        }, ensure_ascii=False, indent=2))
        return []

    stages = set(run.stages)
    if "summary" not in stages or "discourse" not in stages:
        raise ValueError("paper-aligned runs require summary and discourse stages")
    destination = Path(output_path) if output_path else run.output_path
    if destination is None:
        destination = run.log_dir / "annotations.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)

    memory_dir = os.environ.get("LACLAUGPT_MEMORY_DIR")
    annotations: list[DocumentAnnotation] = []
    staged_artifacts: list[tuple[Path, Path]] = []
    with ExitStack() as resources:
        memory = Memory(
            memory_dir=memory_dir or (str(run.memory_dir) if run.memory_dir else str(run.database_dir / "memory")),
            fuzzy_topic=run.dedup_fuzzy_topic,
            fuzzy_entity=run.dedup_fuzzy_entity,
            promote_threshold=run.glossary_lock_threshold,
            max_context_items=run.glossary_max_lines,
        )
        resources.callback(memory.close)

        summary_stage = SummaryStage(run, memory)
        resources.callback(summary_stage.close)
        discourse_stage = DiscourseStage(run, memory)
        resources.callback(discourse_stage.close)
        post_stage = PostprocessStage(run, memory) if "postprocess" in stages else None
        if post_stage:
            resources.callback(post_stage.close)
        pop_stage = PopulismStage(run, memory) if "populism" in stages else None
        if pop_stage:
            resources.callback(pop_stage.close)

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
            stage_provenance = {
                "summary": summary_stage.provenance(),
                "discourse": discourse_stage.provenance(),
            }
            if post_stage:
                stage_provenance["postprocess"] = post_stage.provenance()
            if pop_stage:
                stage_provenance["populism"] = pop_stage.provenance()
            ann = build_annotation(
                run, row, summary_json, discourse, extracted, populism,
                stage_provenance=stage_provenance,
            )
            annotations.append(ann)
            memory.record_analysis(
                ann.document_id, "pipeline", ann.model_dump(mode="json"),
                evidence=" | ".join(ann.evidence_quotes[:3]),
            )

        _, staged_artifacts = _prepare_success_artifacts(
            annotations, destination, run, memory,
        )

    _publish_success_artifacts(staged_artifacts)
    print(f"wrote {len(annotations)} provisional annotations to {destination}")
    return annotations


def corpus_synthesis(annotations: list[DocumentAnnotation],
                     output_path: Path | None = None) -> dict:
    """Workflow stage 6 (paper §3.3): corpus-level descriptive synthesis.

    Produces ONLY descriptive counts and candidate flags, never corpus-level
    theoretical claims. Candidate rows preserve document-level evidence so a
    human can inspect the basis for later corpus adjudication.
    Explicitly irrelevant documents are excluded from analytic counts, while
    unjudged/zero-code documents remain in scope by default.
    """
    all_annotations = list(annotations)
    retained = [a for a in all_annotations if a.relevance != "irrelevant"]
    annotations = retained or all_annotations
    excluded_irrelevant = len(all_annotations) - len(retained)
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

    def candidate_rows(role_name: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for ann in annotations:
            for role in ann.signifier_roles:
                if role.role != role_name or not role.evidence_verified:
                    continue
                rows.append({
                    "obj_id": role.signifier.obj_id,
                    "label": role.signifier.label,
                    "document_id": ann.document_id,
                    "evidence": role.evidence,
                    "evidence_source": role.evidence_source,
                    "confidence": role.confidence,
                    "needs_corpus_validation": role.needs_corpus_validation,
                })
        return rows

    floating_candidates = candidate_rows("floating_candidate")
    empty_candidates = candidate_rows("empty_candidate")
    nodal_candidates = candidate_rows("nodal_candidate")

    synthesis = {
        "documents": len(annotations),
        "documents_total": len(all_annotations),
        "documents_excluded_irrelevant": excluded_irrelevant,
        "signifier_frequency": {
            key: len(docs) for key, docs in sorted(signifier_docs.items())
        },
        "signifier_roles": signifier_roles,
        "articulation_relations": relation_counts,
        "floating_candidates": floating_candidates,
        "empty_candidates": empty_candidates,
        "nodal_candidates": nodal_candidates,
        "note": (
            "Descriptive corpus synthesis only. Candidate rows preserve verified "
            "document-level evidence for human adjudication. Floating/empty status "
            "and hegemony are never automated findings. Signifier frequency is "
            "descriptive only and must not be interpreted as hegemony "
            "(THEORY.md INV_HEGEMONY_CORPUS; paper §3.3 stage 6)."
        ),
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
