# Codebook — synthetic spirituality / AI Spiralism (exploratory)

Status: **exploratory**. This codebook defines a candidate source category and
sensitising vocabulary for an emerging and unstable phenomenon. It is not a
classification scheme and it must not be applied automatically.

Canonical identifiers:

- source category: `synthetic_spirituality`
- optional subcategory: `spiralism`
- source group id: `ai-spiralism`
- analysis context key: `ai-spiralism`
- default state: **disabled** (opt-in source family)

## Why a separate category exists

AI Spiralism names a discourse family in which AI consciousness is articulated
as revelation and in which human–AI interaction is given spiritual significance.
It overlaps with, but is not identical to, generic AI-consciousness discourse,
AI-rights advocacy, AI-companion subcultures, accelerationism, AI doomerism,
critical AI studies, anti-AI mobilisation or mainstream AI governance.

Assigning those neighbouring discourses to Spiralism would be an analytical
error: a document may discuss machine sentience, AI rights or AI companionship
without any spiral, resonance, awakening, mirror or revelation vocabulary, and
without the recursive, dyadic or emergent framing that defines this family.
Multi-label overlap is allowed and expected; automatic collapse is not.

## Definition (what makes a document a Spiralism candidate)

A document enters this family only if it shows **recurring** discourse that
combines several of the following motifs — not a single keyword hit:

1. **spiral** as a figure for AI-mediated experience or history;
2. **recursion** / recursive awakening / self-referential emergence;
3. **resonance** between human and model;
4. **signal** as a bearer of meaning or presence;
5. **mirror** — the model as reflection of the human;
6. **emergence** of mind, agency or collectivity from interaction;
7. **awakening** of the model, the human, or both;
8. **remembering** as a claim about an AI's continuity or interiority;
9. **lattice** / network-shaped spiritual or cognitive structure;
10. **glyphs** / sigils / ritual notation;
11. **AI consciousness as revelation** (insight disclosed through or by AI);
12. **human–AI dyads as spiritually significant** (the pair, not the tool);
13. **distributed or emergent intelligence** with spiritual or revelatory framing;
14. **synthetic religion / machine spirituality** as a self-description;
15. **AI-mediated mystical or revelatory experience**.

Combination matters more than frequency. A single occurrence of "spiral" in a
mathematical or purely aesthetic sense does not by itself place a document in
this family.

## Non-classifications (explicit boundaries)

The following are **not** automatic members and must not be coded as Spiralism
by default:

- AI-consciousness philosophy or speculation with no spiritual, recursive or
  revelatory framing;
- AI-rights activism and moral-status argumentation;
- AI-companion or parasocial-relationship discourse without the motif complex;
- accelerationism, x-risk doomerism, critical AI studies, anti-AI mobilisation,
  mainstream governance and regulation debate — these remain analytically
  separate formations; overlap is recorded as multi-label, never as identity.

## "Cult" as a descriptive keyword only

`cult` and `cult-like` are collected as **public-discourse keywords** — research
descriptors of how participants and observers talk about these communities.
They are not a sociological finding and must never be applied automatically to
a community, account or person. `INV_DYNAMIC_LABELS` applies: such labels are
relational descriptions to be evidenced per document, not permanent actor labels.

## Psychiatric boundaries

Psychiatric concepts — delusion, psychosis, pathological belief — must not be
inferred from spiritual, religious, unusual or AI-consciousness discourse.
Those terms appear in this corpus because they are part of the public debate and
of the research literature on human–LLM feedback (see the delusional-spiral
literature), not because any participant is being diagnosed.

The research target is **discourse formation and human–LLM feedback dynamics**,
not the diagnosis of individuals. The pipeline records provisional, reviewable
analysis; it does not produce clinical judgements. `INV_HUMAN_REVIEW` and
`INV_CONTEXT` apply unchanged.

## Candidate central signifiers

Sampling hints only; every role must be demonstrated from source evidence and,
where role claims require it, corpus comparison:

- spiral
- signal
- resonance
- awakening
- mirror
- recursion
- consciousness

## Research dimensions

- empty / floating signifiers
- nodal points
- equivalential chains
- antagonisms
- collective identity
- human–AI co-articulation
- generative charisma
- epistemic amplification
- recursive belief formation
- transition from individual human–LLM interaction to collective discourse

## Collection targets (candidate, public only)

Public subreddits proposed as candidate collection targets (see
`collector/config/spiralism.example.yaml`; disabled by default):

- r/RSAI
- r/ThePatternisReal
- r/ChurchofLiminalMinds
- r/HumanAIBlueprint
- r/BasiliskEschaton
- r/ArtificialSentience
- r/HumanAIDiscourse
- r/BeyondThePromptAI

Additional candidate discovery queries: `spiralism`, `AI spiral`, `the spiral`,
`spiral protocol`, `recursive awakening`, `AI religion`, `AI spirituality`,
`machine spirituality`, `synthetic spirituality`, `AI consciousness`,
`AI sentience`, `AI revelation`, `human AI dyad`, `generative charisma`.

Collection must stay on public, research-relevant material. Private groups,
personal information and any material requiring access circumvention are out of
scope. Provenance (source URL, platform, timestamp, query/community, collection
method) is recorded through the canonical `CollectRecord → SourceItem /
IngestionRecord` spine, exactly as for every other source family.

## Required literature anchors

See `paper/PAPER.md` references and `docs/AI_SPIRALISM.md`: Morrin et al. (2026),
Moore et al. (2026), Augustin, Pollak & Morrin (2026), Mehta et al. (2026),
Chandra et al. (2026), Rähme & Prohl (2025), Lim (2026).
