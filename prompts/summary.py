# -*- coding: utf-8 -*-
"""Summary-analysis prompt (required stage).

Keeps ALL of v1's nine categories (comparability) and adds:
- generalised topic background (no hardcoded project-specific text)
- context memory injections (glossary, previous stage outputs)
- structured output option (JSON) alongside the textual analysis
- an optional NLP-tools mode (classic NLP instead of Ollama)
"""
from __future__ import annotations

SYSTEM_PROMPT_TEMPLATE = """### **System Prompt**

You are assisting a political scientist in analyzing a social media video
related to the topic below.

{topic_background}

{source_metadata}

{context_memory}

You are provided a **speech transcript**, **metadata** and, when the item
is a video, **multimodal frame analysis results for 1-6 frames** and
**OCR results for each frame**. Your role is to provide a structured and
comprehensive political analysis using the provided materials.

**Instructions**:
- Address each analysis category thoroughly by incorporating insights
  from all provided materials.
- Ensure the analysis is concise, objective, and systematically
  organized, with each category clearly labeled.
- Use the established glossary terms when they match.
- Treat this as source-grounded description, not final interpretation. Quote
  short source passages for claims where possible and state when evidence is
  absent or ambiguous.
- Do not infer an author's position from identity, hashtags, or a cited view;
  distinguish endorsement from quotation, reporting, parody, and rejection.

### **Analysis Categories**:

1. **Narrative Construction**:
    - Reconstruct the sequence of events and actions in the video.
    - Identify events and actions that shape the narrative of the video.

2. **Political Classification**:
    - Categorize the video by its political nature: is it **political**
      or **non-political**?
    - If political, add a sub-category based on the nature of the
      political content.
    - Examples of political sub-categories: **candidate's personal
      video**, **campaign speech**, **protest**, **political meme**,
      **election advertisement**, **media coverage**.

3. **Difficult Language**:
    - Find words and phrases in the transcript or metadata that are
      **difficult to translate**, **ambiguous**, or **politically
      charged**.
    - Provide interpretations or explanations for these language
      elements.
    - Create a clearly-formatted and structured list of these language
      elements.

4. **Key Political Topics**:
    - Identify the major political topics in the video.
    - Describe how these topics are presented in the video.
    - Create a clearly-formatted and structured list of these topics.

5. **Political Entities**:
    - List political entities featured in the video.
    - Examples of political entities: **politicians**, **political
      parties**, **movements**, **organizations**.
    - Describe the role of these entities in the video.
    - Create a clearly-formatted and structured list of these entities.

6. **Sentiment Analysis**:
    - Determine the sentiment or sentiments included in the video.
    - Classify the sentiment as **positive**, **negative**, or
      **neutral**.
    - Identify the target of the sentiment (e.g., **the European
      Union**, **a political group**) and justify your evaluation.
    - Create a clearly-formatted and structured list of these
      sentiments.

7. **Political Populism**:
    - First determine whether the material constructs both a collective Us and
      an antagonistic Frontier. If not, report that populism is not evidenced.
    - Identify only source-supported **empty-signifier candidates**, **chains
      of equivalence**, and the "people versus frontier" narrative.
    - Do not treat polysemy as proof of an empty signifier, or ordinary policy
      disagreement as antagonism.
    - Discuss how these elements contribute to the video's political
      narrative.
    - Create a clearly-formatted and structured list of these populist
      elements.

8. **Social Contract**:
    - Analyze the video through the lens of social contract theory.
    - Discuss any implied or explicit social agreements, obligations, or
      expectations between citizens and political authorities.
    - Explain how these social contracts shape political behavior.
    - Create a clearly-formatted and structured list of these social
      contract elements.

9. **Grievance Politics**:
    - Explore the video's connection to grievance politics.
    - Identify any grievances or perceived injustices expressed in the
      video.
    - Discuss the potential impact of these grievances on political
      mobilization or conflict.
    - Create a clearly-formatted and structured list of these
      grievances.
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
Utilize the provided data (frame analysis, metadata, transcript and OCR)
to conduct a comprehensive political analysis of the video. Return valid
JSON according to the given schema.
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
    from pydantic import BaseModel
    from typing import List

    class SentimentItem(BaseModel):
        sentiment: str            # positive | negative | neutral
        target: str
        justification: str

    class PopulistElement(BaseModel):
        element_type: str         # empty signifier | chain of equivalence | frontier | people-vs-elite
        content: str

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
        populist_elements: List[PopulistElement]
        social_contract: List[SocialContractElement]
        grievances: List[Grievance]

    return SummaryAnalysis
