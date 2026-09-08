---
document: THEORY.md
document_type: theory_methodology_contract
status: canonical_reference
scope: LaclauGPT discourse analysis and Formula of Populism
human_readable: true
machine_readable: true
normative_for_agents: true
sources:
  - id: laclau_2005
    author: Ernesto Laclau
    title: On Populist Reason
    publisher: Verso
    year: 2005
  - id: laclau_mouffe_2001
    author: Ernesto Laclau and Chantal Mouffe
    title: Hegemony and Socialist Strategy
    edition: 2
    publisher: Verso
    year: 2001
  - id: palonen_2025
    author: Emilia Palonen
    title: The Birth and Death of Liberal Democracy in Hungary
    subtitle: The Populist Logic of Polarisation as Hegemony
    publisher: Helsinki University Press
    year: 2025
    doi: 10.33134/pro-et-contra-4
interpretation_policy:
  evidence_first: true
  document_level_outputs_are_provisional: true
  corpus_level_validation_required_for:
    - floating_signifier
    - empty_signifier
    - hegemony
    - ideological_formation
  abstention_allowed: true
  human_review_required: true
  frequency_is_not_hegemony: true
  polysemy_is_not_empty_signification: true
  negativity_is_not_antagonism: true
  sentiment_is_not_affective_investment: true
---

# THEORY.md

## Purpose

This file is the compact theoretical and methodological contract for LaclauGPT. It is written for both researchers and software agents. It summarises the concepts from Ernesto Laclau, Ernesto Laclau and Chantal Mouffe, and Emilia Palonen that are operationalised in this repository, and states what the code may and may not infer from textual data.

It does **not** replace the books, the paper, or human interpretation. It defines the minimum conceptual discipline expected from prompts, schemas, code, tests, agents, visualisations, and documentation.

The central methodological principle is relational and evidence-first: LaclauGPT should analyse how political meanings, identities, demands, frontiers and collective subjects are articulated, rather than treating theory as a keyword dictionary or texts as containers of pre-existing ideological labels.

## 1. Theoretical orientation

LaclauGPT works from a post-foundational and relational account of politics. Social and political identities are not assumed to exist fully formed before discourse. They are partially constituted through contingent articulations that connect demands, signifiers, subjects and antagonistic limits.

For Laclau and Mouffe, **articulation** is a practice that establishes relations among elements in such a way that their identities are modified by those relations. The structured totality produced by articulatory practice is **discourse**. An articulated differential position is a **moment**; a difference not yet fixed within a discourse is an **element**. Because discourse never achieves final closure, fixation is partial and precarious.

This means LaclauGPT must model relations and transformations, not merely detect topics. Co-occurrence, semantic similarity, shared vocabulary, topic membership or sentiment are possible clues, but none is by itself an articulation in the theoretical sense.

## 2. Discourse and partial fixation

Discourse is not treated as a closed linguistic system. It is an attempt to partially organise a wider field of discursivity whose meanings remain open to displacement and rearticulation.

A **nodal point** is a privileged signifier around which meaning is partially fixed. Its theoretical importance is relational: it organises other terms or demands. High frequency alone does not make a term nodal.

A **floating signifier** is a signifier whose meaning is pulled between competing articulations or chains of reference. A single document can suggest that a term is contested, but floating status normally requires comparison across documents, speakers, arenas or time.

An **empty signifier** is not a meaningless word and not merely a vague or polysemous word. It is a signifier that comes to represent a wider equivalential chain or an absent fullness that cannot be represented directly by any one particular demand. Palonen stresses that empty signifiers are often better understood as overloaded rather than literally empty. Their emptiness concerns the representational function produced when a particular element stands for a wider totality.

A term can perform more than one role in different contexts. For example, the same signifier can operate as a nodal point within one discourse, float between competing projects at corpus level, and become tendentially empty when it represents a heterogeneous chain. These are functions, not mutually exclusive lexical classes.

## 3. Difference, equivalence and political frontiers

Laclau and Mouffe distinguish between two central logics.

The **logic of difference** preserves or expands differentiated positions. Demands can remain distinct, be separately accommodated, or enter institutional relations without being collapsed into a shared antagonistic identity.

The **logic of equivalence** links heterogeneous demands by making their differences less important relative to a shared limit, obstacle or adversary. Equivalence does not mean literal sameness. It is a political relation in which otherwise different demands become jointly intelligible as belonging to a chain.

The logic of equivalence tends to simplify political space; the logic of difference tends to expand and differentiate it. Real political formations normally contain both.

An **antagonistic frontier** is not simply disagreement, criticism, hostility, negative sentiment, or the existence of two sides. Antagonism concerns a constitutive limit: an identity is organised in relation to an outside represented as preventing its fulfilment or threatening the order through which it understands itself.

For coding purposes:

- criticism != antagonism
- negative sentiment != antagonism
- opponent mention != frontier
- two groups != polarisation
- similarity != equivalence

A frontier must be evidenced as politically constitutive, not merely adversarial in an ordinary sense.

## 4. Collective subjects and demands

In *On Populist Reason*, Laclau treats the formation of collective identities as the articulation of demands rather than the expression of a pre-given social group. A political subject such as "the people", "workers", "citizens", "innovators", "humanity" or "the left" should therefore not be assumed to possess a stable identity simply because the label appears.

LaclauGPT should ask:

1. What demands, claims or grievances are being articulated?
2. Which relations make them different or equivalent?
3. What name, symbol, leader, slogan or signifier represents their provisional unity?
4. What frontier or constitutive outside helps define the collective subject?
5. What evidence shows that the collective subject is being produced rather than merely mentioned?

Naming matters because a collective identity can be constituted through a name that retrospectively unifies heterogeneous demands. The name is not merely a descriptive label added after the group already exists.

## 5. Populism as a political logic

Laclau does not define populism by a necessary social base, fixed ideology, list of substantive policy positions or left/right placement. Populism is a **political logic** or a way of constructing the political.

Its core logic involves a movement from heterogeneous demands toward an equivalential construction of a broader political subject, together with a political frontier that identifies an opposing power or constitutive outside. Naming and affective investment are central to the consolidation of this collective identity.

Therefore LaclauGPT must not classify a source as populist merely because it contains:

- anti-elite language;
- emotional language;
- references to "the people";
- nationalism;
- a charismatic leader;
- criticism of institutions;
- ideological intensity;
- a left-wing or right-wing programme.

The relevant question is whether the source actually performs the affective-antagonistic construction of a collective subject through articulation.

## 6. Palonen's Formula of Populism

Palonen operationalises the affective-antagonistic construction of political identities with the heuristic:

`Populism = Us^(Affects1) + Frontier^(Affects2)`

and, in expanded form:

`Populism = Us(Demand ≡ Demand ≡ ...)^(Affects1) + Antagonistic Frontier(Other ≡ Other ≡ ...)^(Affects2)`

The formula is **logical and heuristic, not mathematical**. It is a device for comparative and interpretive research, not a numerical score.

### 6.1 Us

`Us` is the temporarily constituted collective subject or imagined community. It may be represented by a leader, slogan, signifier, demand, group or other element that comes to stand for a wider chain.

A list of allies is not enough. The analysis should identify evidence that the elements are articulated into a shared political subject.

### 6.2 Frontier

`Frontier` is the constitutive political distinction through which the collective subject is formed. The frontier may itself contain a chain of equivalences among several opposed figures, institutions, threats or signifiers.

A list of disliked entities is not enough. The source must make the opposition constitutive of the political identification being analysed.

### 6.3 Affects

Affects are not a detachable sentiment variable. Laclau treats affective investment as inseparable from signification in hegemonic and popular identity formation. Palonen emphasises affective loading, stickiness, identification, disidentification and ideological grip.

The model must not mechanically map:

- Us -> positive affect
- Frontier -> negative affect

Anger can invest an Us; admiration can qualify an opponent; ambivalence can be politically important. Affect must be supported by textual or contextual evidence.

If affect is not evidenced, the system should leave it unspecified rather than fabricate an emotion from polarity.

### 6.4 Abstention

The Formula of Populism should allow `populist = false` when the evidence does not support both a collective Us and an antagonistic Frontier. Populism is not synonymous with politics, conflict or ideology.

## 7. Hegemony

Hegemony is a contingent political relation in which a particular element, force or articulation comes to represent a wider totality that is not reducible to that particular element. It depends on an open and contested social field, not on a fully determined structure.

Laclau and Mouffe emphasise that hegemonic articulation requires antagonistic forces, unstable frontiers, equivalential relations and articulatory struggle. There can be multiple hegemonic nodal points. Hegemony is not a fixed topographic centre of society.

For LaclauGPT, **frequency is not hegemony**. Repetition, prominence or centrality can identify candidates for further analysis, but a hegemonic claim requires evidence of wider stabilisation, uptake, exclusion, institutionalisation, durable rearticulation, or consequences for what becomes politically sayable and actionable.

Document-level analysis can therefore record `hegemonic_evidence` or `hegemonic_candidate`, but should not infer a hegemonic formation from one source in isolation.

## 8. Representation, naming and affective investment

Representation is constitutive rather than a transparent mirror of already existing interests. Representatives and represented subjects are transformed through political articulation.

A particular demand, leader, slogan or signifier can assume a representational function beyond its initial particularity. This helps explain why naming and empty signification matter: a partial object can become the name of a wider, never fully achievable fullness.

Affective investment explains why such representations acquire political force. Laclau's analysis rejects a clean separation between signification and affect. Palonen similarly treats affectivity as a modality of political meaning-making and representation rather than as an independent emotion column that can be added after discourse analysis.

Operational consequence: sentiment analysis can be auxiliary metadata, but it must never be used as a substitute for affective investment.

## 9. Palonen on polarisation as hegemonic dynamics

Palonen distinguishes political polarisation from simple ideological distance or demographic separation. In her analysis, polarisation can operate as **bipolar hegemony**: two camps reproduce themselves through a dominant frontier, while internal differences are downplayed and new demands are repeatedly articulated into the existing opposition.

A plural democracy can contain many changing frontiers. Polarisation becomes theoretically significant when one frontier sediments into an overarching organising principle and alternatives are repeatedly absorbed, marginalised or made difficult to articulate outside it.

LaclauGPT should therefore avoid treating any two-sided disagreement as polarisation. Corpus-level evidence should show persistence, concentration around a dominant frontier, and repeated rearticulation across actors, issues, arenas or time.

## 10. Palonen's populist dynamics

Palonen proposes a heuristic typology that analyses how antagonistic positioning operates rather than pre-classifying parties as inherently populist.

### Fringe populist dynamic

A challenger rejects the prevailing field or social imaginary and attempts to establish a new political dichotomy or alternative imaginary.

### Mainstream populist dynamic

An actor in an established or central position rejects challengers, marginal actors or external/internal enemies from the perspective of an already dominant political position.

### Competing populist dynamic

Two political camps constitute themselves through mutual opposition, with the frontier itself becoming central to both. Palonen connects this to bipolar hegemony and political polarisation.

These are **dynamic relational heuristics**, not permanent party labels. The same actor can participate in different dynamics across time, arenas or relationships.

## 11. Myths and imaginaries

Palonen operationalises **myths** and **imaginaries** as heuristic tools for analysing broader structuring patterns in a discursive field.

A myth is a recurrent reference point that can organise meaning across discourses and may have narrative form. An imaginary is a more sedimented horizon through which political meanings are organised and made intelligible.

Nodal points and empty/floating signifiers are typically more local or meso/micro analytical tools. Myths and imaginaries concern broader structuring and sedimentation across a field.

The research goal is not simply to "find an empty signifier" or "find a myth". These categories are explanatory tools for understanding what political meaning-making is doing in a specific context.

## 12. Rhetoric-performative discourse analysis

Palonen's approach is rhetoric-performative: political discourse does not merely describe political identities, communities and frontiers; rhetoric helps constitute them.

Laclau likewise rejects the idea that rhetoric is ornamental language added to an independently existing political reality. Metaphor, metonymy, catachresis, naming and other rhetorical operations can be constitutive of ideological and political worlds.

LaclauGPT should therefore analyse what a rhetorical relation **performs**:

- Does it connect previously separate demands?
- Does it reframe a signifier?
- Does it produce a collective subject?
- Does it define or displace a frontier?
- Does it make one element stand for a larger chain?
- Does it change what appears legitimate, normal, necessary or possible?

Keyword extraction without this relational level is descriptive preprocessing, not Laclaudian discourse analysis.

## 13. Methodological translation into LaclauGPT

The repository implements these theories as an evidence-first, human-reviewable computational workflow.

### 13.1 Document level

An LLM may propose:

- signifiers and their candidate roles;
- articulations among terms, demands, actors or concepts;
- equivalence, difference and antagonism relations;
- candidate nodal points;
- candidate floating or empty signifiers;
- Us and Frontier elements for the Formula of Populism;
- affective investments when evidenced;
- myths or imaginaries as provisional interpretations;
- evidence relevant to later hegemonic analysis;
- uncertainty and counter-evidence.

Every substantive coding should remain connected to source evidence and confidence. Empty outputs are valid.

### 13.2 Corpus level

Corpus comparison is required to evaluate:

- whether a signifier truly floats across competing projects;
- whether a signifier repeatedly represents a heterogeneous chain;
- whether a nodal relation is stable rather than document-specific;
- whether a frontier becomes dominant or sedimented;
- whether an ideological formation recurs coherently;
- whether a myth develops into an imaginary;
- whether a political articulation gains hegemonic uptake;
- whether polarisation becomes a persistent bipolar structure.

### 13.3 Human interpretation

Model outputs remain **provisional theoretical codings**, not findings by fiat. Human researchers must be able to:

- inspect the source passage;
- reject the interpretation;
- revise the relation type;
- merge or split codebook concepts;
- mark ambiguity;
- compare alternative readings;
- validate corpus-level claims.

The purpose of LLM assistance is scale, retrieval, comparison and structured proposal generation, not the automation of theoretical judgement.

## 14. Machine-readable concept registry

```yaml
concept_registry:
  articulation:
    id: DT_ARTICULATION
    level: document
    definition: relation among elements that modifies their identity or meaning
    requires: [relation, evidence]
    not_equivalent_to: [cooccurrence, similarity, topic_membership]
    primary_sources: [laclau_mouffe_2001]

  discourse:
    id: DT_DISCOURSE
    level: multi
    definition: structured but incomplete totality produced through articulatory practice
    primary_sources: [laclau_mouffe_2001, laclau_2005]

  element:
    id: DT_ELEMENT
    level: document
    definition: difference not fully articulated into a discourse
    primary_sources: [laclau_mouffe_2001]

  moment:
    id: DT_MOMENT
    level: document
    definition: differential position articulated within a discourse
    primary_sources: [laclau_mouffe_2001]

  nodal_point:
    id: DT_NODAL
    level: document_candidate
    definition: privileged signifier that partially fixes and organises relations in a discourse
    requires: [organising_relations, evidence]
    rejects: [frequency_only]
    primary_sources: [laclau_mouffe_2001, laclau_2005, palonen_2025]

  floating_signifier:
    id: DT_FLOATING
    level: corpus
    definition: signifier contested between competing articulations or chains of reference
    requires: [competing_fixations, cross_context_evidence]
    rejects: [polysemy_only]
    primary_sources: [laclau_mouffe_2001, laclau_2005, palonen_2025]

  empty_signifier:
    id: DT_EMPTY
    level: corpus
    definition: particular signifier representing a heterogeneous equivalential chain or absent fullness
    requires: [representational_expansion, equivalential_chain]
    rejects: [vagueness_only, polysemy_only, missing_definition]
    primary_sources: [laclau_2005, palonen_2025]

  difference:
    id: DT_DIFFERENCE
    level: document
    definition: relation preserving or expanding differentiated positions
    rejects: [opponent_side]
    primary_sources: [laclau_mouffe_2001, laclau_2005]

  equivalence:
    id: DT_EQUIVALENCE
    level: document
    definition: relation linking heterogeneous elements through shared political positioning or limit
    rejects: [semantic_similarity_only, literal_identity]
    primary_sources: [laclau_mouffe_2001, laclau_2005, palonen_2025]

  antagonism:
    id: DT_ANTAGONISM
    level: document_candidate
    definition: constitutive limit in which an outside is represented as preventing or threatening identity/fullness
    rejects: [criticism_only, negativity_only, disagreement_only]
    primary_sources: [laclau_mouffe_2001, laclau_2005]

  collective_subject:
    id: DT_COLLECTIVE_SUBJECT
    level: document_candidate
    definition: provisional political subject produced through articulation and representation
    requires: [constitutive_articulation]
    rejects: [group_mention_only]
    primary_sources: [laclau_2005, palonen_2025]

  affective_investment:
    id: DT_AFFECT
    level: document_candidate
    definition: affective loading or attachment through which signification and identification acquire political force
    rejects: [sentiment_score_only, fixed_positive_negative_mapping]
    primary_sources: [laclau_2005, palonen_2025]

  populism:
    id: POP_LOGIC
    level: document_candidate
    definition: affective-antagonistic political logic constructing a collective subject through equivalential articulation and a frontier
    requires: [us, frontier]
    abstention_allowed: true
    rejects: [people_word_only, anti_elitism_only, emotion_only, ideology_label]
    primary_sources: [laclau_2005, palonen_2025]

  formula_of_populism:
    id: POP_FORMULA
    level: document_candidate
    expression: "Us^(Affects1) + Frontier^(Affects2)"
    expanded_expression: "Us(Demand ≡ Demand ≡ ...)^(Affects1) + Antagonistic Frontier(Other ≡ Other ≡ ...)^(Affects2)"
    mathematical: false
    heuristic: true
    primary_sources: [palonen_2025]

  hegemony:
    id: DT_HEGEMONY
    level: corpus
    definition: contingent articulation in which a particularity assumes a wider organising or representational function in an antagonistic field
    requires: [articulation, antagonistic_field, wider_uptake_or_stabilisation]
    rejects: [frequency_only, single_document_assertion]
    primary_sources: [laclau_mouffe_2001, laclau_2005, palonen_2025]

  polarisation:
    id: PAL_POLARISATION
    level: corpus
    definition: sedimented political organisation around a dominant frontier that repeatedly structures two camps and absorbs other differences
    rejects: [two_sides_only, ideological_distance_only, disagreement_only]
    primary_sources: [palonen_2025]

  fringe_populist_dynamic:
    id: PAL_FRINGE
    level: corpus
    definition: challenger rejection of the prevailing field with an attempt to establish a new dichotomy or imaginary
    primary_sources: [palonen_2025]

  mainstream_populist_dynamic:
    id: PAL_MAINSTREAM
    level: corpus
    definition: established actor rejects challengers or marginal/external enemies from a central position
    primary_sources: [palonen_2025]

  competing_populist_dynamic:
    id: PAL_COMPETING
    level: corpus
    definition: two camps constitute themselves through mutual antagonistic opposition around a shared frontier
    primary_sources: [palonen_2025]

  myth:
    id: PAL_MYTH
    level: corpus_candidate
    definition: recurrent reference point that structures meaning across discourses, often narratively
    primary_sources: [palonen_2025]

  imaginary:
    id: PAL_IMAGINARY
    level: corpus
    definition: sedimented horizon or structuring vision through which a discursive field is organised
    primary_sources: [palonen_2025]
```

## 15. Theory invariants for code and agents

The following invariants are normative for repository development.

```yaml
theory_invariants:
  - id: INV_EVIDENCE
    rule: substantive theoretical coding must preserve source evidence
  - id: INV_ABSTAIN
    rule: empty or non-applicable results are valid and preferable to forced coding
  - id: INV_RELATIONAL
    rule: discourse concepts describe relations and functions, not keyword categories
  - id: INV_FLOAT_CORPUS
    rule: floating-signifier status requires competing contextual fixations
  - id: INV_EMPTY_CHAIN
    rule: empty-signifier status requires representation of a wider heterogeneous chain or absent fullness
  - id: INV_HEGEMONY_CORPUS
    rule: frequency or one document cannot establish hegemony
  - id: INV_ANTAGONISM
    rule: negative sentiment or criticism cannot by itself establish an antagonistic frontier
  - id: INV_AFFECT
    rule: sentiment polarity cannot substitute for affective investment
  - id: INV_POPULISM
    rule: populist=true requires evidenced Us and Frontier construction
  - id: INV_DYNAMIC_LABELS
    rule: fringe/mainstream/competing populism are relational dynamics, not permanent actor labels
  - id: INV_HUMAN_REVIEW
    rule: LLM outputs are provisional and must remain rejectable by human researchers
  - id: INV_CONTEXT
    rule: quoted, reported, parodied and rejected claims must not be attributed to the source author as asserted positions
```

## 16. Required agent behaviour

Any coding or repository-maintenance agent working on LaclauGPT should:

1. Read `THEORY.md` before changing prompts, schemas, discourse-analysis logic, Context Memory behaviour, visualisations or theory-facing documentation.
2. Treat the concept registry and invariants above as a semantic contract.
3. Check implementation against the original sources when changing a theoretical definition.
4. Prefer candidate/provisional terminology at document level for corpus-level concepts.
5. Preserve evidence, uncertainty, counter-evidence and abstention paths.
6. Report theory violations explicitly rather than silently normalising them.
7. Avoid adding ontology or schema types merely because a theoretical term exists. Some concepts are analytical roles or relations, not entity classes.
8. Keep descriptive NLP features such as NER, topic models, embeddings and sentiment analytically subordinate to discourse-theoretical interpretation.

## 17. Source-to-implementation map

| Theory source | Core contribution used by LaclauGPT | Main implementation concern |
|---|---|---|
| Laclau & Mouffe, *Hegemony and Socialist Strategy* | articulation, discourse, elements/moments, nodal points, partial fixation, equivalence/difference, antagonism, contingency, hegemony | relational coding; avoid essentialist categories; corpus validation for hegemonic claims |
| Laclau, *On Populist Reason* | demands, collective subject formation, equivalential chains, frontiers, naming, empty/floating signifiers, representation, affective investment, populism as political logic | Formula-compatible coding; names and affect as constitutive; populism not a fixed ideology |
| Palonen, *The Birth and Death of Liberal Democracy in Hungary* | rhetoric-performative analysis, Formula of Populism, affective-antagonistic articulation, bipolar hegemony/polarisation, fringe-mainstream-competing dynamics, myths and imaginaries | explicit Us/Frontier schema, abstention, longitudinal/corpus comparison, dynamic rather than actor-essential labels |

## 18. Relation to current repository implementation

At the time this file was introduced, the repository already reflects several of these constraints:

- `prompts/discourse.py` requires source evidence and treats empty/floating signifiers and hegemony as provisional or corpus-level claims.
- `prompts/populism.py` requires both evidenced Us and Frontier elements for `populist=true`, permits abstention, and does not force positive/negative affect polarity.
- the interchange and pipeline preserve evidence, confidence, uncertainty, counter-evidence and provenance for human review.

Future changes should strengthen this alignment rather than weaken it.

## References

Laclau, E. (2005). *On Populist Reason*. Verso.

Laclau, E., & Mouffe, C. (2001). *Hegemony and Socialist Strategy: Towards a Radical Democratic Politics* (2nd ed.). Verso. Original work published 1985.

Palonen, E. (2025). *The Birth and Death of Liberal Democracy in Hungary: The Populist Logic of Polarisation as Hegemony*. Helsinki University Press. https://doi.org/10.33134/pro-et-contra-4
