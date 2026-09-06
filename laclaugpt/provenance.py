"""Provenance and evidence helpers — the traceability spine of the method.

Non-negotiables (paper §3.4):
- every theoretical interpretation links to exact source evidence
- model, model version, prompt version and pipeline version are recorded
- review status separates model proposals from human decisions
- a matching quote can still be irrelevant or stripped of context, so
  mechanical presence-checking and human review are both necessary
"""
from __future__ import annotations

from laclaugpt.models import (EvidenceLink, EvidenceSpan, Provenance,
                              ReviewStatus, SourceDocument)

PIPELINE_VERSION = "public-1.0"


def make_provenance(method: str = "llm", *, model: str | None = None,
                    model_version: str | None = None,
                    prompt_version: str | None = None,
                    run_id: str | None = None) -> Provenance:
    return Provenance(method=method, model=model, model_version=model_version,
                      prompt_version=prompt_version, run_id=run_id)


def evidence_span(document_id: str, text: str, quote: str) -> EvidenceSpan | None:
    """Locate a quote in the document text; None when absent. A returned
    span proves presence, not relevance — human review still decides."""
    start = text.find(quote)
    if start < 0:
        return None
    return EvidenceSpan(document_id=document_id, exact_text=quote,
                        start_offset=start, end_offset=start + len(quote))


def verify_evidence_links(links: list[EvidenceLink], document_text: str
                          ) -> tuple[list[EvidenceLink], list[EvidenceLink]]:
    """Mechanical check: does each proposed interpretation's evidence quote
    actually occur in the retained source representation? Returns
    (verified, unverified). This is presence-checking only — relevance,
    attribution and context are human-review questions."""
    verified, unverified = [], []
    for link in links:
        (verified if link.evidence and link.evidence in document_text
         else unverified).append(link)
    return verified, unverified


def strip_reviewed(links: list[EvidenceLink]) -> list[EvidenceLink]:
    """Keep only human-reviewed/accepted links (e.g. for corpus-level
    statistical analysis — inference operates on reviewed results)."""
    return [link for link in links
            if link.review_status in (ReviewStatus.HUMAN_REVIEWED,
                                      ReviewStatus.ACCEPTED)]