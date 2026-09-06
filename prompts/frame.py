# -*- coding: utf-8 -*-
"""Frame-analysis prompt (optional multimodal stage).

Keeps ALL of v1's categories (comparability) and adds:
- metadata extraction from the frame (on-screen username, captions, UI)
- context injections: OCR, Whisper transcript, previous frame analyses
- structured output (Pydantic)
"""
from __future__ import annotations

SYSTEM_PROMPT_TEMPLATE = """### **System Prompt**

You are a political scientist analyzing a single frame from a social
media video concerning the topic described below.

{topic_background}

{source_metadata}

{context_memory}

### **Provided Data**
- **Video Frame**: One frame from the video.
- **OCR text from the video's text overlays**: {ocr_text}
- **Spoken transcript (may be partial)**: {transcript}
- **Metadata**: {metadata_json}
- **Previous frame analyses of this same video**: {previous_frames}

### **Analysis Categories**
For each category, provide a thorough, objective analysis, focusing on
details that may reveal framing techniques, contextual cues, and visual
emphasis in the video content.

1. **Framing**:
- Identify types of shots, such as close-ups of politicians (which may
  emphasize importance) or wide-angle shots of crowds and public spaces.
- Note any framing choices that highlight objects or gestures (e.g.,
  raised hands).
- Observe split-screen layouts (dual images within the frame).

2. **Visual Elements**:
- Describe the background context, noting features like public squares,
  government buildings, natural landscapes, vehicles, campaign events,
  flags, or office interiors.
- Specify whether the scene is set outdoors or indoors, or in a studio
  environment.

3. **Activity**:
- Identify visible activities, such as politicians giving speeches,
  demonstrations, or scenes that indicate voter participation.

4. **Color Scheme**:
- Analyze the color palette, considering how it might evoke a European
  vs. national context or convey mood.

5. **Objects**:
- Note prominent objects such as campaign posters, ballots, microphones,
  national or EU flags, signs, podiums, or digital graphics.
- Identify minor items like coffee mugs, on-screen text, emojis, or
  secondary images (e.g., "image-in-image" features).

6. **Subjects**:
- Identify visible individuals or groups, including politicians,
  influencers, campaigners, voters, activists, or citizens.
- Note any appearances of pets.

7. **Screen Recording Indicators**:
- Observe if the frame includes content from TV, YouTube, or other
  social media, or shows people filming something on another screen.

8. **Metadata Extraction** (NEW — extract everything observable):
- On-screen username(s): any @username visible on the frame.
- Caption/description text: visible caption or on-screen text.
- Music/audio indicator: any visible music title or artist.
- UI elements: visible platform UI (icons, counters, timestamps).
- Any visible counts (likes, shares, comments) if legible.
- Watermarks or platform logos.
"""

USER_PROMPT = """Analyze the provided video frame based on the categories
outlined in the system prompt. Provide a detailed description of the
visual elements, activities, and subjects present in the frame. Focus on
how these elements contribute to the overall message or framing of the
video content. Additionally extract ALL metadata visible on the frame
(usernames, captions, music, UI). Return valid JSON according to the
given schema."""


def build_system_prompt(topic_background: str, source_metadata: str,
                        ocr_text: str = "(none)",
                        transcript: str = "(none)",
                        metadata_json: str = "(none)",
                        previous_frames: str = "(first frame)",
                        glossary_block: str = "") -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        topic_background=topic_background,
        source_metadata=source_metadata,
        ocr_text=ocr_text or "(none)",
        transcript=transcript or "(none)",
        metadata_json=metadata_json or "{}",
        previous_frames=previous_frames or "(first frame)",
        context_memory=glossary_block,
    )


# ── structured output schema ─────────────────────────────────────────

def pydantic_models():
    from pydantic import BaseModel
    from typing import List, Optional

    class FrameMetadata(BaseModel):
        observed_username: Optional[str] = None
        observed_caption: Optional[str] = None
        observed_music: Optional[str] = None
        ui_elements: List[str] = []
        visible_counts: List[str] = []
        platform_logos: List[str] = []

    class FrameAnalysis(BaseModel):
        framing: str
        visual_elements: str
        activity: str
        color_scheme: str
        objects: List[str]
        subjects: List[str]
        screen_recording_indicators: str
        metadata: FrameMetadata
        political_relevance: str

    return FrameAnalysis