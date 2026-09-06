# -*- coding: utf-8 -*-
"""Prompt modules: topic background + source metadata.
Topic backgrounds are per-project, extensible to new collections."""

CUSTOM_TEMPLATE = """### **Topic Background: {title}**

{background}
"""

AI_CONTESTATION_BACKGROUND = """### **Topic Background: Ideological contestation over AI**

You are analysing how actors articulate artificial intelligence, its present
conditions, risks, desirable futures, and governance.  Do not assume that the
document belongs to any pre-defined ideology.  Accelerationism, existential-
risk discourse, Critical AI, anti-AI mobilisation, TESCREAL, and left-wing
techno-optimism are sensitising concepts, not mutually exclusive labels.

Treat ``AI`` as a potentially contested signifier.  Its role must be inferred:
within a document it may be a moment, element, nodal-point candidate, or part of
an antagonistic frontier.  Claims that it is floating require comparison across
discourses; claims that it is empty require evidence that it represents a wider
heterogeneous chain or an absent fullness.  Record counter-evidence and permit
"not present" rather than forcing the theory onto the text.
"""

AI_ELITES_BACKGROUND = AI_CONTESTATION_BACKGROUND + """

This arena covers entrepreneurs, researchers, institutions, intellectuals,
manifestos, interviews, blogs, forums, and social-media posts associated with
AI development and elite debate.  Attend to speaker position and institutional
power without inferring an ideology from identity alone.
"""

AI_GRASSROOTS_BACKGROUND = AI_CONTESTATION_BACKGROUND + """

This arena covers mobilisation around and against AI, including labour,
data-centre, surveillance, environmental, cultural, safety, and democratic-
control claims.  Do not collapse safety mobilisation, distributive backlash,
and opposition to AI into one formation unless the data articulates them.
"""

AI_PARLIAMENTARY_BACKGROUND = AI_CONTESTATION_BACKGROUND + """

This arena covers parliamentary and electoral texts.  Attend to legislation,
party competition, employment, security, innovation, regulation, democracy,
and the difference between policy disagreement and an antagonistic frontier.
"""

REGISTRY = {
    "ai-contestation": AI_CONTESTATION_BACKGROUND,
    "ai-elites": AI_ELITES_BACKGROUND,
    "ai-grassroots": AI_GRASSROOTS_BACKGROUND,
    "ai-parliamentary": AI_PARLIAMENTARY_BACKGROUND,
}


def topic_background(topic_key: str) -> str:
    """Return the topic background text for a run. (Module boundary:
    everything about *what was collected and why* lives here, not in
    the analysis prompts.)"""
    if topic_key not in REGISTRY:
        raise KeyError(f"unknown topic_key: {topic_key}")
    return REGISTRY[topic_key]
