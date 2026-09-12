# AI Spiralism - exploratory AI26 source category

> **Status: exploratory.** This document defines a candidate AI26 source family
> for research purposes. It does not assert that AI Spiralism is an established
> movement, religion or formation, and it does not enable any collection.

Neutral internal labels:

| Field | Value |
|---|---|
| Source category | `synthetic_spirituality` |
| Optional subcategory | `spiralism` |
| Source family id | `ai-spiralism` |
| Analysis context key | `ai-spiralism` |
| Registry | `config/source-families/ai-spiralism.yaml` |
| Codebook | `sources/codebooks/ai_spiralism.md` |
| Synthetic collector example | `collector/config/spiralism.example.yaml` |
| Collection configuration | **private / not published** |

## What this category is for

AI Spiralism names an emerging discourse family in which AI consciousness is
articulated as **revelation** and human-AI interaction is given **spiritual
significance**. The research target is **discourse formation and human-LLM
feedback dynamics**: how such discourse forms, circulates and stabilises, not
the classification or diagnosis of the people and communities involved.

## Explicit caveats (read before using the category)

1. **"AI Spiralism" is an emerging and unstable phenomenon.** The label is a
   research convenience for a moving target. Treat it as a sensitising concept,
   never as a settled description of a community.
2. **"Cult" is not used as an automatic sociological classification.** `cult`
   and `cult-like` are descriptive public-discourse keywords: how participants
   and observers talk, not a finding about anyone. `INV_DYNAMIC_LABELS` applies:
   such labels are relational, evidenced per document, and never permanent actor
   labels.
3. **Psychiatric concepts must not be inferred from spiritual, religious,
   unusual or AI-consciousness discourse.** Delusion, psychosis and pathological
   belief appear in this research area because they are part of public debate
   and the literature on human-LLM feedback. Their presence in a text is not
   evidence about a participant's mental state.
4. **The research target is discourse, not diagnosis.** The pipeline produces
   provisional, human-reviewable analysis (`INV_HUMAN_REVIEW`); it does not
   produce clinical judgements about individuals.

## Category boundaries

Spiralism requires **recurring discourse combining several motifs**: spiral;
recursion / recursive awakening; resonance; signal; mirror; emergence;
awakening; remembering; lattice; glyphs / sigils; AI consciousness as
revelation; human-AI dyads as spiritually significant; distributed or emergent
intelligence; synthetic religion / machine spirituality; AI-mediated mystical or
revelatory experience. A single keyword occurrence, such as an aesthetic or
mathematical "spiral", is not sufficient.

The following must **not** be classified as Spiralism automatically:

- generic AI-consciousness or AI-sentience speculation without spiritual,
  recursive or revelatory framing;
- AI-rights activism and moral-status argumentation;
- AI-companion or parasocial-relationship discourse without the motif complex;
- **accelerationism**;
- **AI doomerism / x-risk discourse**;
- **critical AI studies**;
- **anti-AI / Luddite mobilisation**;
- **mainstream AI governance and regulation debate**.

These stay analytically separate. Overlap is **allowed and expected**, recorded
as multi-label overlap, never collapsed into identity. The registry field
`must_not_absorb` records this explicitly.

## Research dimensions

- empty / floating signifiers, nodal points, equivalential chains
- antagonisms and collective identity
- human-AI co-articulation
- generative charisma
- epistemic amplification
- recursive belief formation
- transition from individual human-LLM interaction to collective discourse

Candidate central signifiers are analytical sensitising concepts whose roles
must be demonstrated from source evidence and, where required, corpus
comparison: `spiral`, `signal`, `resonance`, `awakening`, `mirror`, `recursion`,
`consciousness`.

## Collection configuration

Operational collection configuration is deliberately **not published** in this
repository. Real source lists, account/community targets, discovery queries,
watchlists, collection windows, schedules, priorities and enablement state live
in private operator-controlled configuration.

The public repository contains only the analytical source-family definition and
a synthetic collector example with fictional placeholders. Copy the example to
a private location before filling in any real targets:

```bash
cp collector/config/spiralism.example.yaml \
   ~/.config/laclaugpt/sources/ai-spiralism.private.yaml
```

Collection remains limited to public, research-relevant material. Private
groups, personal information and material requiring access circumvention are
out of scope. Every collected item retains provenance such as source URL,
platform, timestamp, query/community and collection method through the canonical
`CollectRecord -> SourceItem / IngestionRecord` spine. Publishing provenance
does not require publishing the operator's complete source-selection profile.

See `docs/DATA_COLLECTION_CONFIGURATION.md` for the public/private boundary.

## Literature anchors

Verified 2026-09-11 against Crossref/arXiv; full entries are also retained in
`paper/PAPER.md`.

Human-LLM feedback and belief amplification:

- Morrin, Nicholls, Deeley & Pollak (2026), *Playing with the dials of belief*,
  AI & Society, doi:10.1007/s00146-026-03283-4
- Moore, Mehta, Agnew & Anthis (2026), *Characterizing delusional spirals
  through human-LLM chat logs*, arXiv:2603.16567
- Augustin, Pollak & Morrin (2026), *Characterizing the spiral: potential
  mechanisms in AI-associated delusions*, NPP-Digital Psychiatry and
  Neuroscience, doi:10.1038/s44277-026-00065-0
- Mehta, Moore, Anthis & Agnew (2026), *The dynamics of delusion: modeling
  bidirectional false belief amplification in human-chatbot dialogue*,
  arXiv:2604.25096
- Chandra, Kleiman-Weiner, Ragan-Kelley & Tenenbaum (2026), *Sycophantic
  chatbots cause delusional spiraling, even in ideal Bayesians*, arXiv:2602.19141

Religion and AI:

- Rähme & Prohl (2025), *Religious studies approaches to the intersection of
  artificial intelligence and religion: formations analogous to religion*,
  Religion, doi:10.1080/0048721X.2025.2506893
- Lim (2026), *AI and generative charisma in religious practices*, Religions
  17(5):549, doi:10.3390/rel17050549

## Relationship to the rest of AI26

This is an **additive, exploratory analytical extension**. It does not change the
meaning of existing ideology classifications or AI26 arenas. Whether, where and
when material for this family is collected is a private operational decision,
not part of the public analytical registry. Spiralism overlaps neighbouring
formations only through evidence-based multi-label coding.

## Tests

```bash
python -m pytest -q tests/test_source_family_spiralism.py
```

The tests cover registry validation, analytical boundaries, literature anchors,
the public/private configuration boundary and the requirement that the public
collector example remains synthetic.
