# -*- coding: utf-8 -*-
"""Postprocess prompt (structured extraction: entities/topics/sentiments).

v1 prompt kept in full (comparability) with the decisive addition:
the established glossary is injected and the model must return
`matched` vs `new_candidates` separately.
"""
from __future__ import annotations

SYSTEM_PROMPT_TEMPLATE = """### **System Prompt**

**Role**:
- You are presented a previously generated analysis of a political video. Your task is to extract lists of elements from the analysis.
- Extract entities, sentiments and topics from an analysis of a video. Extract the names of the entities and topics mentioned in the analysis. Provide a simple list of the names of the entities, sentiments and topics.
- Present the lists in a structured JSON format. If no entities or topics are found, return an empty list.

{context_memory}

---

**Tasks**:
1. **Extract Topics**:
    - Extract topics mentioned in the analysis.
    - Provide only the name of each topic.
    - Present the topics in a structured JSON format.
    - If no topics are found, return an empty list.
    - Try to avoid redundancy in the topics extracted.
    - **Match topics against the established topic list above first**; only propose genuinely new topics in `new_topics`.
    - Merge the topics that are similar or related.
    - If no topics are found, return an empty list.

2. **Extract Entities**:
    - Extract entities mentioned in the analysis.
    - Provide only the name of each entity.
    - Classify each entity with exactly one spaCy NER type from the closed
      list: PERSON (people incl. fictional), NORP (nationalities/religious/
      political groups), FAC (buildings, airports, highways, bridges), ORG
      (companies, agencies, institutions), GPE (countries, cities, states),
      LOC (non-GPE locations, mountain ranges, bodies of water), PRODUCT
      (objects, vehicles, foods — not services), EVENT (named hurricanes,
      battles, wars, sports events), WORK_OF_ART (titles of books, songs),
      LAW (named documents made into laws), LANGUAGE (named languages),
      DATE (absolute/relative dates or periods), TIME (times smaller than a
      day), PERCENT (including "%"), MONEY (monetary values incl. unit),
      QUANTITY (measurements as of weight or distance), ORDINAL ("first",
      "second"), CARDINAL (numerals not in another type).
    - Present the entities in a structured JSON format.
    - If no entities are found, return an empty list.
    - Try to avoid redundancy in the entities extracted.
    - **Match entities against the established entity list above first**; only propose genuinely new entities in `new_candidates`.
    - Use the established canonical form (e.g. if "Emmanuel Macron" is established, use exactly that, not "Macron").
    - Merge the entities that are similar or related.
    - If no entities are found, return an empty list.

3. **Determine Sentiments**:
    - Extract sentiments listed in the text and determine if they are positive, negative, or neutral.
    - Determine the target of each sentiment.
    - Create lists of the targets of positive, negative and neutral sentiments.
    - **Match sentiment targets against the established entity list above first**.
    - Try to avoid redundancy in the targets extracted.
    - Merge the targets that are similar or related.
    - If no sentiments are found, return an empty list.

---

**Output format** (strict): one JSON object with keys
`topics`, `entities`, `entity_types`, `positive`, `neutral`, `negative`
(matched lists, using established canonical forms; `entity_types[i]` is
the NER type of `entities[i]`, same order and length), plus
`new_topics`, `new_entities` (only genuinely new proposals)."""


def build_system_prompt(glossary_block: str = "") -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(context_memory=glossary_block)


def pydantic_models():
    from laclaugpt_memory import NER_TYPES
    from pydantic import BaseModel, field_validator

    class Extraction(BaseModel):
        topics: list[str]
        entities: list[str]
        entity_types: list[str] = []
        positive: list[str]
        neutral: list[str]
        negative: list[str]
        new_topics: list[str] = []
        new_entities: list[str] = []

        @field_validator("entity_types")
        @classmethod
        def _ner_types_closed_vocabulary(cls, v):
            """Unknown/missing NER labels degrade to CARDINAL-safe fallback:
            keep the closed vocabulary without failing the whole extraction."""
            return [t if t in NER_TYPES else "" for t in v]

    return Extraction