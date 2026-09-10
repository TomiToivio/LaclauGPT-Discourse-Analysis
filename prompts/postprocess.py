# -*- coding: utf-8 -*-
"""Postprocess prompt (structured descriptive extraction).

The postprocess stage is shared by topics, entities and descriptive sentiment,
but the canonical project switches are authoritative: disabled families are not
requested from the model. Sentiment observations are evidence-bearing, limited
to the source author's/narrator's asserted voice, and stay strictly separate
from Laclaudian affective investment.
"""
from __future__ import annotations

PROMPT_VERSION = "postprocess-v2.3"


def build_system_prompt(
    glossary_block: str = "",
    *,
    include_topics: bool = True,
    include_entities: bool = True,
    include_sentiment: bool = True,
) -> str:
    tasks: list[str] = []
    output_fields: list[str] = []

    if include_topics:
        tasks.append("""1. **Extract Topics**:
- Extract topics mentioned in the analysis.
- Provide only the name of each topic.
- Match topics against the established topic list first; only propose genuinely
  new topics in `new_topics`.
- Avoid redundancy and merge closely related duplicate surface forms.
- If no topics are found, return an empty list.""")
        output_fields.extend(["topics", "new_topics"])

    if include_entities:
        tasks.append("""2. **Extract Entities**:
- Extract entities mentioned in the source/analysis as descriptive mentions.
- Entity presence never implies endorsement, authorship, ideology, or sentiment;
  an entity mentioned only inside quoted/reported/rejected speech is still a
  mention, not the document author's position.
- Provide only the name of each entity.
- Classify each matched entity with exactly one spaCy NER type from this closed
  list: PERSON, NORP, FAC, ORG, GPE, LOC, PRODUCT, EVENT, WORK_OF_ART, LAW,
  LANGUAGE, DATE, TIME, PERCENT, MONEY, QUANTITY, ORDINAL, CARDINAL.
- Match entities against the established entity list first; only propose
  genuinely new entities in `new_entities`.
- Use the established canonical form when a match exists.
- Avoid redundancy. If no entities are found, return an empty list.""")
        output_fields.extend(["entities", "entity_types", "new_entities"])

    if include_sentiment:
        tasks.append("""3. **Determine descriptive sentiment**:
- Identify only source-supported positive, neutral or negative sentiment
  expressed in the document author's/speaker's OWN ASSERTED VOICE and its
  target.
- Do NOT turn sentiment contained only in quoted, reported, parodied, cited, or
  rejected speech into a document-level sentiment observation. If attribution
  is unclear, abstain rather than assigning it to the author.
- For every reading return the target, polarity, one short verbatim
  `evidence_quote` from the SOURCE MATERIAL, and `uncertainty` from 0.0 to 1.0
  (0 = no uncertainty recorded, 1 = maximally uncertain).
- Do not infer sentiment from political side, ideology label or disagreement
  alone. If the evidence does not support a polarity, abstain by returning no
  reading.
- Match targets against the established target/entity list when possible.
- `sentiments` is descriptive polarity only. It is NOT Laclaudian affective
  investment and must never be used as a substitute for it.
- The legacy `positive`, `neutral` and `negative` target lists are retained for
  compatibility and should mirror only the author-voice structured readings.""")
        output_fields.extend(["sentiments", "positive", "neutral", "negative"])

    if not tasks:
        tasks.append("No descriptive coding family is enabled. Return the empty schema.")

    disabled = []
    if not include_topics:
        disabled.extend(["topics", "new_topics"])
    if not include_entities:
        disabled.extend(["entities", "entity_types", "new_entities"])
    if not include_sentiment:
        disabled.extend(["sentiments", "positive", "neutral", "negative"])

    return f"""### System Prompt

**Role**:
You are presented source material plus a preliminary analysis. Extract only the
descriptive coding families enabled below. This stage is descriptive and does
not make final discourse-theoretical claims.

{glossary_block}

---

**Enabled tasks**:

{chr(10).join(tasks)}

---

**Output format**:
Return one strict JSON object. Enabled fields are: {', '.join(output_fields) or '(none)'}.
The full schema also contains disabled fields; they MUST be empty when disabled:
{', '.join(disabled) or '(none)'}.
"""


def pydantic_models():
    from typing import Literal

    from laclaugpt_memory import NER_TYPES
    from pydantic import BaseModel, Field, field_validator

    class SentimentReading(BaseModel):
        target: str = Field(min_length=1)
        polarity: Literal["positive", "neutral", "negative"]
        evidence_quote: str = Field(min_length=1)
        uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)

    class Extraction(BaseModel):
        topics: list[str] = []
        entities: list[str] = []
        entity_types: list[str] = []
        positive: list[str] = []
        neutral: list[str] = []
        negative: list[str] = []
        new_topics: list[str] = []
        new_entities: list[str] = []
        sentiments: list[SentimentReading] = []

        @field_validator("entity_types")
        @classmethod
        def _ner_types_closed_vocabulary(cls, v):
            return [t if t in NER_TYPES else "" for t in v]

    return Extraction
