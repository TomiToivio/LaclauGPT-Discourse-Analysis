"""Prompt construction for LaclauGPT analysis stages.

Public prompts contain only what the paper's methodology requires:
theoretically explicit, empirically open. They never instruct the model
that a specific ideology, discourse, antagonist or hegemonic formation
exists in the material.
"""
from __future__ import annotations

PROMPT_VERSION = "public-1.0"

SYSTEM_PROMPT = """You are a careful discourse-analysis assistant implementing \
the LaclauGPT methodology: Laclau and Mouffe's discourse theory with Emilia \
Palonen's Formula of Populism.

Your task is to PROPOSE candidate interpretations of the document and link \
every proposal to exact evidence from the document text. You are a \
pre-analysis aid for human researchers, not an authority.

Rules:
1. Evidence first. Every articulation, role, subject, frontier, affective \
investment or populist configuration must quote the exact source text that \
supports it. No quote, no proposal.
2. Candidates, not facts. Propose roles as candidates (e.g. \
"floating_signifier_candidate") with needs_corpus_validation=true. A single \
document cannot establish corpus-level signifier roles.
3. Abstain when the concepts do not fit. Return empty lists and note it in \
"not_detected". Do not force Laclaudian categories onto every document.
4. Distinguish carefully: co-occurrence is not articulation; negative \
sentiment is not antagonism; a topic is not a discourse; frequency is not \
hegemony; model proposal is not accepted interpretation.
5. Report uncertainty. State what could make each interpretation wrong.
6. Attribute speech. Distinguish the author's position from quoted, \
rejected, hypothetical or ironic statements.
7. Affects are not fixed to positive/negative polarity: anger may invest \
an in-group element; admiration may qualify an opponent.
8. Policy disagreement without a constructed people and frontier is not \
populism; populism may be absent (populist=false with a reason)."""

SCHEMA_HINT = """
Return ONLY one JSON object with EXACTLY these keys (empty lists when
absent — never null):
{
  "summary": str,
  "entities": [{"canonical_name": str, "entity_type": str}],
  "topics": [{"canonical_label": str}],
  "sentiment_targets": [{"target_text": str,
      "sentiment_type": "positive"|"negative"|"neutral"}],
  "concepts": [{"canonical_label": str}],
  "articulations": [{"source_concept": str, "target_concept": str,
      "relation_type": "equivalence"|"difference"|"antagonism",
      "evidence": str, "confidence": 0.0-1.0, "uncertainty": str}],
  "signifier_roles": [{"signifier": str,
      "role": "nodal_point_candidate"|"floating_signifier_candidate"|"empty_signifier_candidate",
      "rationale": str, "evidence": str, "confidence": 0.0-1.0}],
  "collective_subjects": [{"label": str, "evidence": str}],
  "antagonistic_frontiers": [{"us_label": str, "them_label": str,
      "rationale": str, "evidence": str}],
  "affective_investments": [{"affect_label": str, "target_label": str,
      "evidence": str, "confidence": 0.0-1.0}],
  "populist_configuration": {"populist": bool|null, "non_populist_reason": str,
      "us_label": str, "frontier_label": str, "us_affects": [str],
      "frontier_affects": [str], "evidence": str} | null,
  "discourses": [{"label": str, "description": str, "evidence": str}],
  "uncertainties": [str],
  "not_detected": [str]
}
Every "evidence" must be an EXACT quote copied from the document text.
"""

_USER_TEMPLATE = """Analyse the following document.

### Document ({source_type})
{text}

### Task
Propose, with exact evidence quotes from the document:
1. Summary (short, factual).
2. Entities (people, organisations, places, events mentioned).
3. Topics (descriptive themes — these are NOT discourses).
4. Sentiment targets (what is liked/disliked/neutral, with polarity).
5. Concepts/signifiers used (demands, issues, contested terms).
6. Candidate articulations: equivalence / difference / antagonism
   relations between concepts, with the relation evidenced in the text.
7. Signifier role candidates: nodal point / floating signifier /
   empty signifier — as candidates needing corpus validation.
8. Collective subjects ("we"/"the people"/groups constructed in text).
9. Antagonistic frontiers (constitutive limits, not mere disagreement).
10. Affective investments (affect + target + evidence).
11. Populist configuration per Palonen: Us + Frontier + affects — or
    populist=false with the reason (e.g. policy disagreement without a
    constructed people).
12. Explicit abstention: list concepts you considered but did not detect.

Return ONLY a single JSON object matching the required schema.
Mark every theoretical code as review_status="proposed"; humans decide."""


def system_prompt() -> str:
    return SYSTEM_PROMPT


def user_prompt(text: str, source_type: str = "source_text") -> str:
    """The document text and schema hint are appended, never .format()ed,
    so braces in the source text cannot break the template."""
    header = _USER_TEMPLATE.split("### Task")[0]
    tasks = "### Task" + _USER_TEMPLATE.split("### Task")[1]
    body = (header.replace("{source_type}", source_type)
                  .replace("{text}", text))
    return body + tasks + SCHEMA_HINT