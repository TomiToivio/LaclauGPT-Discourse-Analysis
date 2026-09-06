"""LaclauGPT — the academic method and minimal reference implementation.

Theory-guided, LLM-assisted discourse analysis (Laclau & Mouffe;
Palonen's Formula of Populism) with traceable evidence, uncertainty and
human review. This package is deliberately minimal: collection,
databases, machine profiles and production pipelines live elsewhere.
"""
from laclaugpt.analysis import LaclauGPTAnalyzer, analyze
from laclaugpt.models import (AnalysisResult, AntagonisticFrontier,
                              Articulation, ArticulationType,
                              AffectiveInvestment, CollectiveSubject, Concept,
                              DiscourseCandidate, DiscursiveRoleAssignment,
                              Entity, EvidenceLink, EvidenceSpan,
                              HegemonyAssessment, PopulistConfiguration,
                              Provenance, ReviewStatus, SentimentAnnotation,
                              SignifierRole, SignifierRoleAssignment,
                              SourceDocument, Topic)
from laclaugpt.provenance import (PIPELINE_VERSION, evidence_span,
                                  make_provenance, strip_reviewed,
                                  verify_evidence_links)

__version__ = "1.0.0"

__all__ = [
    "analyze", "LaclauGPTAnalyzer", "PIPELINE_VERSION",
    "AnalysisResult", "SourceDocument", "EvidenceLink", "EvidenceSpan",
    "Provenance", "ReviewStatus", "Entity", "Topic", "SentimentAnnotation",
    "Concept", "Articulation", "ArticulationType", "SignifierRole",
    "SignifierRoleAssignment", "CollectiveSubject", "AntagonisticFrontier",
    "AffectiveInvestment", "DiscourseCandidate", "PopulistConfiguration",
    "HegemonyAssessment", "make_provenance", "evidence_span",
    "verify_evidence_links", "strip_reviewed",
]