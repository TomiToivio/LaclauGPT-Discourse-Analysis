"""Minimal reference implementation of the LaclauGPT method.

    input text
        ↓  structured LLM pre-analysis (abstention allowed)
        ↓  evidence-verified candidate interpretations
        ↓  AnalysisResult with provenance + review status

This demonstrates the methodology; it is not the production pipeline
(no memory infrastructure, databases, collection, scheduling — those
live elsewhere). Model provider is an injected callable so the core
stays dependency-light: pass any function(system, user) -> str (Ollama,
OpenAI-compatible endpoint, or a stub in tests).
"""
from __future__ import annotations

import json
import re
from typing import Callable

from laclaugpt import prompts
from laclaugpt.models import (AnalysisResult, AntagonisticFrontier,
                              Articulation, ArticulationType,
                              AffectiveInvestment, CollectiveSubject, Concept,
                              DiscourseCandidate, Entity, EvidenceLink,
                              PopulistConfiguration, Provenance,
                              ReviewStatus, SentimentAnnotation,
                              SignifierRole, SignifierRoleAssignment,
                              SourceDocument, Topic)
from laclaugpt.provenance import PIPELINE_VERSION, make_provenance

ModelCall = Callable[[str, str], str]   # (system, user) -> raw text


class LaclauGPTAnalyzer:
    """Theory-guided LLM pre-analysis with evidence-verified candidates."""

    def __init__(self, model_call: ModelCall, *, model: str | None = None,
                 model_version: str | None = None):
        """model_call: (system_prompt, user_prompt) -> raw completion text.
        Dependency-light by design: any provider callable works."""
        if not callable(model_call):
            raise TypeError("model_call must be callable(system, user) -> str")
        self.model_call = model_call
        self.model = model
        self.model_version = model_version

    # ── public API ───────────────────────────────────────────────────
    def analyze(self, text: str, *, source_type: str = "source_text",
                language: str | None = None) -> AnalysisResult:
        document = SourceDocument(text=text, source_type=source_type,
                                  language=language)
        provenance = make_provenance(
            "llm", model=self.model, model_version=self.model_version,
            prompt_version=prompts.PROMPT_VERSION,
            run_id=document.document_id)
        raw = self._call(document)
        payload = self._parse_json(raw)
        return self._build_result(document, payload, provenance)

    # ── internals ────────────────────────────────────────────────────
    def _call(self, document: SourceDocument) -> str:
        return self.model_call(
            prompts.system_prompt(),
            prompts.user_prompt(document.text, document.source_type)
            + prompts.SCHEMA_HINT)

    @staticmethod
    def _parse_json(raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):     # tolerate fenced JSON
            text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text).strip()
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("model returned no JSON object")
        return json.loads(match.group(0))

    def _link(self, document: SourceDocument, evidence: str,
              confidence: float | None, uncertainty: str | None) -> EvidenceLink:
        return EvidenceLink(
            document_id=document.document_id, evidence=evidence or "",
            confidence=confidence, uncertainty=uncertainty,
            review_status=ReviewStatus.PROPOSED,
            provenance_id="", run_id=document.document_id)

    def _build_result(self, document: SourceDocument, payload: dict,
                      provenance: Provenance) -> AnalysisResult:
        p_id = provenance.provenance_id
        result = AnalysisResult(
            document_id=document.document_id,
            run_id=provenance.run_id or document.document_id,
            summary=payload.get("summary") or None,
            entities=[Entity(canonical_name=e.get("canonical_name", ""),
                             entity_type=e.get("entity_type", "other"))
                      for e in payload.get("entities", []) if e.get("canonical_name")],
            topics=[Topic(canonical_label=t.get("canonical_label", ""))
                    for t in payload.get("topics", []) if t.get("canonical_label")],
            sentiment_targets=[
                SentimentAnnotation(target_text=s.get("target_text", ""),
                                    sentiment_type=s.get("sentiment_type", "neutral"),
                                    document_id=document.document_id,
                                    confidence=s.get("confidence"))
                for s in payload.get("sentiment_targets", [])
                if s.get("target_text")
                and s.get("sentiment_type") in ("positive", "negative", "neutral")],
            concepts=[Concept(canonical_label=c.get("canonical_label", ""))
                      for c in payload.get("concepts", []) if c.get("canonical_label")],
            uncertainties=list(payload.get("uncertainties", [])),
            not_detected=list(payload.get("not_detected", [])),
            provenance=provenance,
        )
        for a in payload.get("articulations", []):
            relation = str(a.get("relation_type", "")).casefold()
            if relation not in {m.value for m in ArticulationType}:
                continue  # unknown relation names are dropped, never guessed
            result.articulations.append(Articulation(
                **self._link(document, a.get("evidence", ""),
                             a.get("confidence"), a.get("uncertainty")).__dict__,
                articulation_id="art_" + result.document_id[-12:] + str(len(result.articulations)),
                source_concept=a.get("source_concept", ""),
                target_concept=a.get("target_concept", ""),
                relation_type=ArticulationType(relation)))
        for r in payload.get("signifier_roles", []):
            role = str(r.get("role", "")).casefold()
            if role not in {m.value for m in SignifierRole}:
                continue
            link = self._link(document, r.get("evidence", ""),
                              r.get("confidence"), None)
            result.signifier_roles.append(SignifierRoleAssignment(
                **link.__dict__,
                assignment_id="role_" + result.document_id[-12:] + str(len(result.signifier_roles)),
                signifier=r.get("signifier", ""), role=SignifierRole(role),
                rationale=r.get("rationale", ""),
                needs_corpus_validation=True))
        for s in payload.get("collective_subjects", []):
            result.collective_subjects.append(CollectiveSubject(
                **self._link(document, s.get("evidence", ""), None, None).__dict__,
                subject_id="subject_" + result.document_id[-12:] + str(len(result.collective_subjects)),
                label=s.get("label", "")))
        for f in payload.get("antagonistic_frontiers", []):
            result.antagonistic_frontiers.append(AntagonisticFrontier(
                **self._link(document, f.get("evidence", ""), None, None).__dict__,
                frontier_id="frontier_" + result.document_id[-12:] + str(len(result.antagonistic_frontiers)),
                us_label=f.get("us_label", ""), them_label=f.get("them_label", ""),
                rationale=f.get("rationale", "")))
        for inv in payload.get("affective_investments", []):
            result.affective_investments.append(AffectiveInvestment(
                **self._link(document, inv.get("evidence", ""),
                             inv.get("confidence"), None).__dict__,
                investment_id="inv_" + result.document_id[-12:] + str(len(result.affective_investments)),
                affect_label=inv.get("affect_label", ""),
                target_label=inv.get("target_label", "")))
        pop = payload.get("populist_configuration")
        if isinstance(pop, dict):
            result.populist_configuration = PopulistConfiguration(
                **self._link(document, pop.get("evidence", ""), None, None).__dict__,
                configuration_id="pop_" + result.document_id[-12:],
                populist=pop.get("populist"),
                non_populist_reason=pop.get("non_populist_reason"),
                us_label=pop.get("us_label"),
                frontier_label=pop.get("frontier_label"),
                us_affects=list(pop.get("us_affects", [])),
                frontier_affects=list(pop.get("frontier_affects", [])))
        for d in payload.get("discourses", []):
            result.discourses.append(DiscourseCandidate(
                **self._link(document, d.get("evidence", ""), None, None).__dict__,
                discourse_id="disc_" + result.document_id[-12:] + str(len(result.discourses)),
                label=d.get("label", ""), description=d.get("description")))
        return result


def analyze(text: str, *, model_call: ModelCall, source_type: str = "source_text",
            language: str | None = None, model: str | None = None) -> AnalysisResult:
    """One-shot convenience API:
        result = laclaugpt.analyze(text, model_call=my_ollama_call)"""
    return LaclauGPTAnalyzer(model_call, model=model).analyze(
        text, source_type=source_type, language=language)