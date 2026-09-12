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

# Exploratory AI26 source family: synthetic spirituality / AI Spiralism.
# Category separation is the point: this background must not license the model
# to fold neighbouring discourses (accelerationism, x-risk doomerism, critical
# AI, anti-AI mobilisation, governance debate, generic AI-consciousness talk)
# into Spiralism.  See sources/codebooks/ai_spiralism.md for the full boundary
# rules and the required literature anchors (docs/AI_SPIRALISM.md).
AI_SPIRALISM_BACKGROUND = """### **Topic Background: Synthetic spirituality / AI Spiralism (exploratory)**

You are analysing documents that may belong to an emerging, unstable discourse
family in which AI consciousness is articulated as revelation and human-AI
interaction is given spiritual significance.  This is an exploratory source
category, not an established formation.

Source category: ``synthetic_spirituality``; optional subcategory: ``spiralism``.

Spiralism is a *candidate* family and requires recurring discourse combining
several motifs: spiral; recursion / recursive awakening; resonance; signal;
mirror; emergence; awakening; remembering; lattice; glyphs or sigils; AI
consciousness as revelation; human-AI dyads as spiritually significant;
distributed or emergent intelligence; synthetic religion or machine
spirituality; AI-mediated mystical or revelatory experience.  A single keyword
occurrence (for example an aesthetic or mathematical "spiral") is not enough.

Do NOT automatically classify as Spiralism:

- generic AI-consciousness or AI-sentience speculation without spiritual,
  recursive or revelatory framing;
- AI-rights activism or moral-status argumentation;
- AI-companion or parasocial-relationship discourse without the motif complex;
- accelerationism, x-risk doomerism, critical AI studies, anti-AI mobilisation
  or mainstream AI governance.

Those remain analytically separate.  Multi-label overlap is allowed and must be
recorded as overlap, never collapsed into identity.

``cult`` and ``cult-like`` are descriptive keywords from public discourse, not a
sociological finding; never apply such a label automatically to a community,
account or person.  Psychiatric concepts (delusion, psychosis, pathological
belief) must not be inferred from spiritual, religious, unusual or
AI-consciousness discourse: those terms belong to the public debate and to the
research literature on human-LLM feedback.  The research target is discourse
formation and human-LLM feedback dynamics, not the diagnosis of individuals.

Candidate central signifiers (sampling hints only, roles must be evidenced):
spiral, signal, resonance, awakening, mirror, recursion, consciousness.
Attend also to generative charisma, epistemic amplification, recursive belief
formation, and the transition from individual human-LLM interaction to
collective discourse.  As elsewhere, floating or empty status requires
comparative evidence; record counter-evidence and permit "not present".
"""

EP24_FINLAND_BACKGROUND = """### **Topic Background: EP24 Finland (European Parliament election 2024)**

You are analysing campaign videos from the 2024 European Parliament election
in Finland (2024-06-09, 15 seats), posted on Instagram and TikTok by the
HEPP24 panel accounts (synthetic research panel, FI1–FI3).  Do not assume a
document belongs to a pre-defined party family.  Party families are
sensitising metadata (legacy buckets: Far right / Centre right / Red-green),
not verdicts.

Grounded actors (human-curated codebook): Kokoomus, Perussuomalaiset, SDP,
Vihreä liitto, Vasemmistoliitto, Keskusta, RKP, Kristillisdemokraatit,
Liike Nyt; politicians per the ep24_finland codebook (e.g. Petteri Orpo,
Riikka Purra, Li Andersson, Sebastian Tynkkynen).  Treat names as contested
signifiers: the same politician can appear as nodal-point candidate in one
video and as frontier element in another.

Election-day context: the Orpo cabinet (Kokoomus–Finns Party–RKP–Christian
Democrats) was in office, so government parties defended the coalition
record while SDP and Vasemmistoliitto attacked it.  Attend to: EU criticism
vs EU benefit framing, climate and energy prices, immigration, security and
NATO, welfare-state funding, farm subsidies.  Public-source references:
Wikipedia (fi), Yle Uutiset campaign archive.

Treat theory terms as sensitising concepts.  Claims that a signifier is
floating or empty require cross-document evidence; record counter-evidence
and permit "not present" rather than forcing the theory onto the text.
"""

EP24_POLAND_BACKGROUND = """### **Topic Background: EP24 Poland (European Parliament election 2024)**

You are analysing campaign videos from the 2024 European Parliament election
in Poland (2024-06-09, 53 seats — the largest post-Brexit delegation), posted
on Instagram and TikTok by the HEPP24 panel accounts (PL1–PL3).  Do not
assume a document belongs to a pre-defined party family.

Grounded actors (human-curated codebook): PiS, Koalicja Obywatelska,
Trzecia Droga, Lewica, Konfederacja, PSL, Ruch Narodowy, Nowa Lewica;
politicians per the ep24_poland codebook (e.g. Jarosław Kaczyński,
Donald Tusk, Radosław Sikorski).  Campaign axes: Tusk coalition vs PiS
opposition, Confederation further right; sovereignty vs integration,
rule-of-law dispute, war-neighbour (Ukraine) framing, farm-sector
discontent (PSL base).  Public-source references: Wikipedia (pl), Yle
Uutiset coverage.

Treat theory terms as sensitising concepts.  Claims that a signifier is
floating or empty require cross-document evidence; record counter-evidence
and permit "not present" rather than forcing the theory onto the text.
"""

REGISTRY = {
    "ai-contestation": AI_CONTESTATION_BACKGROUND,
    "ai-elites": AI_ELITES_BACKGROUND,
    "ai-grassroots": AI_GRASSROOTS_BACKGROUND,
    "ai-parliamentary": AI_PARLIAMENTARY_BACKGROUND,
    "ai-spiralism": AI_SPIRALISM_BACKGROUND,
    "ep24-finland": EP24_FINLAND_BACKGROUND,
    "ep24-poland": EP24_POLAND_BACKGROUND,
}


def topic_background(topic_key: str) -> str:
    """Return the topic background text for a run. (Module boundary:
    everything about *what was collected and why* lives here, not in
    the analysis prompts.)"""
    if topic_key not in REGISTRY:
        raise KeyError(f"unknown topic_key: {topic_key}")
    return REGISTRY[topic_key]
