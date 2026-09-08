# -*- coding: utf-8 -*-
"""Summary-analysis prompt (required descriptive stage).

The summary stage is deliberately descriptive.  Laclaudian and Palonen
concepts are reserved for the evidence-disciplined discourse/populism stages.
Version 2.2 replaces the historical free-text ``populist_elements`` category
with a source-grounded people-versus-power narrative screen.
"""
from __future__ import annotations

PROMPT_VERSION = "summary-v2.2"

SYSTEM_PROMPT_TEMPLATE = """### **System Prompt**

You are assisting a political scientist in analyzing a social media video
related to the topic below.

{topic_background}

{source_metadata}

{context_memory}

You are provided a **speech transcript**, **metadata** and, when the item
is a video, **multimodal frame analysis results for 1-6 frames** and
**OCR results for each frame**. Your role is to provide a structured and
comprehensive political description using the provided materials.

**Instructions**:
- Address each analysis category by incorporating only information supported by
  the supplied materials.
- Keep this stage descriptive. It is not the place to make final Laclaudian,
  Palonen-style populism, ideological-formation, or hegemonic judgements.
- Ensure the analysis is concise, objective, and systematically organized.
- Use established glossary terms only when they are ordinary descriptive
  references. Retrieved codebook candidates are not evidence.
- Quote short source passages for interpretive descriptive claims where the
  schema requests evidence and state when evidence is absent or ambiguous.
- Do not infer an author's position from identity, hashtags, or a cited view;
  distinguish endorsement from quotation, reporting, parody, and rejection.
- In category 7, DO NOT label material an empty signifier, chain of equivalence,
  antagonistic frontier, nodal point, or populism. Those are theoretical
  judgements handled later by the discourse/populism stages under THEORY.md.

### **Analysis Categories**:

1. **Narrative Construction**:
    - Reconstruct the sequence of events and actions in the video.
    - Identify events and actions that shape the narrative of the video.

2. **Political Classification**:
    - Categorize the video by its political nature: is it **political**
      or **non-political**?
    - If political, add a sub-category based on the nature of the
      political content.
    - Examples: **candidate's personal video**, **campaign speech**,
      **protest**, **political meme**, **election advertisement**,
      **media coverage**.

3. **Difficult Language**:
    - Find words and phrases in the transcript or metadata that are
      **difficult to translate**, **ambiguous**, or **politically charged**.
    - Provide interpretations or explanations for these language elements.

4. **Key Political Topics**:
    - Identify the major political topics in the video.
    - Describe how these topics are presented in the video.

5. **Political Entities**:
    - List political entities featured in the video, such as politicians,
      parties, movements, and organizations.
    - Describe their observed role in the material without inferring ideology
      from identity alone.

6. **Sentiment Analysis**:
    - Describe positive, negative, or neutral sentiment where it is evident.
    - Identify the target and justify the descriptive evaluation.
    - Sentiment is auxiliary descriptive metadata, not affective investment.

7. **People-versus-power Narrative Screen (descriptive only)**:
    - Report whether the supplied material explicitly constructs a collective
      self-reference (for example "we", "the people", "citizens", "workers")
      in opposition to a named or described power, elite, institution, group,
      or other opponent.
    - Return `present`, `absent`, or `uncertain`.
    - `present` requires a short verbatim evidence quote plus both the observed
      collective expression and the observed opposed expression.
    - Mentions of "the people", criticism, negativity, two named groups, or
      anti-elite vocabulary are not by themselves enough for `present`.
    - If the evidence is incomplete or ambiguous, return `uncertain`; if the
      construction is not in the material, return `absent`.
    - Do not translate this descriptive screen into theoretical categories.

8. **Social Contract**:
    - Describe explicit or implied social agreements, obligations, or
      expectations between citizens and political authorities.
    - Keep this source-grounded and distinguish explicit statements from your
      descriptive inference.

9. **Grievance Politics**:
    - Identify grievances or perceived injustices expressed in the material.
    - Describe any explicitly stated or directly supported connection to
      political mobilization or conflict.
"""

USER_PROMPT_TEMPLATE = """### **User Prompt**

**Data for Analysis**:

1. **Frame Analysis Results (1-6 Frames)**:
```
{frame_analysis}
```

2. **Metadata**:
```
{metadata}
```

3. **Transcript**:
```
{transcript}
```

4. **OCR Results**:
```
{ocr_results}
```

### **Task**:
Utilize only the provided data to conduct a comprehensive descriptive political
summary. Return valid JSON according to the given schema.
"""


def build_system_prompt(topic_background: str, source_metadata: str,
                        glossary_block: str = "") -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        topic_background=topic_background,
        source_metadata=source_metadata,
        context_memory=glossary_block,
    )


def build_user_prompt(frame_analysis: str, metadata: str, transcript: str,
                      ocr_results: str) -> str:
    return USER_PROMPT_TEMPLATE.format(
        frame_analysis=frame_analysis or "(no multimodal analysis — text-only row)",
        metadata=metadata or "{}",
        transcript=transcript or "(no transcript)",
        ocr_results=ocr_results or "(no OCR — text-only row)",
    )


def pydantic_models():
    from typing import List, Literal
    from pydantic import BaseModel, model_validator

    class SentimentItem(BaseModel):
        sentiment: str            # positive | negative | neutral
        target: str
        justification: str

    class PeoplePowerNarrative(BaseModel):
        """Descriptive screen only, never a populism/frontier finding."""
        status: Literal["present", "absent", "uncertain"]
        collective_expression: str = ""
        opposed_expression: str = ""
        evidence_quote: str = ""
        explanation: str = ""

        @model_validator(mode="after")
        def present_requires_observed_sides_and_quote(self):
            if self.status == "present" and not (
                self.collective_expression.strip()
                and self.opposed_expression.strip()
                and self.evidence_quote.strip()
            ):
                raise ValueError(
                    "present people-versus-power narrative requires collective_expression, "
                    "opposed_expression and evidence_quote"
                )
            return self

    class SocialContractElement(BaseModel):
        element: str
        explanation: str

    class Grievance(BaseModel):
        grievance: str
        potential_impact: str

    class LanguageItem(BaseModel):
        term: str
        explanation: str

    class TopicItem(BaseModel):
        topic: str
        description: str

    class EntityItem(BaseModel):
        entity: str
        role: str

    class SummaryAnalysis(BaseModel):
        narrative_construction: str
        political_classification: str
        political: bool
        political_subcategory: str
        difficult_language: List[LanguageItem]
        key_political_topics: List[TopicItem]
        political_entities: List[EntityItem]
        sentiments: List[SentimentItem]
        people_power_narrative: PeoplePowerNarrative
        social_contract: List[SocialContractElement]
        grievances: List[Grievance]

    return SummaryAnalysis
