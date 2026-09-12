# LaclauGPT: Ideological contestation over AI

## Abstract

Artificial intelligence (AI) is both a heterogeneous set of sociotechnical arrangements and a contested political signifier. This paper develops a framework for analysing how competing political projects articulate AI in relation to social demands, collective identities, and imagined futures. Situated within Critical AI Studies, it combines Ernesto Laclau and Chantal Mouffe’s discourse theory with Emilia Palonen’s Formula of Populism and the concept of sociotechnical imaginaries. Accelerationism, existential-risk discourse, critical perspectives, opposition to AI, and left-wing techno-optimism provide starting points for inquiry rather than a fixed ideological typology. The paper also develops LaclauGPT as an LLM-assisted methodology for identifying and comparing candidate discursive articulations in large textual datasets. Its central methodological principle is traceability: proposed interpretations must remain connected to source evidence, uncertainty, and human review. A prospective research design covers AI elites, grassroots mobilisation, and parliamentary and electoral politics. The paper contributes a conceptual framework and a validation-oriented research protocol; it does not report an empirical mapping of AI ideologies or establish the validity of the revised pipeline. Its broader aim is to make computational discourse analysis scalable without treating political meaning as a set of self-evident labels.

**Keywords:** artificial intelligence; ideology; discourse theory; LaclauGPT; hegemony; sociotechnical imaginaries; large language models; critical AI studies; computational social science

**Author:** Tomi Toivio, Helsinki Hub on Emotions, Populism and Polarisation (HEPPsinki), University of Helsinki. ORCID: 0000-0002-1335-0478.

**Funding acknowledgement:** LaclauGPT has been developed in connection with CO3, ENDURE, and PLEDGE, supported by the European Union and the Research Council of Finland.

## 1. Introduction

Debates about artificial intelligence concern more than what machines can do. They also concern who should control technological development, whose interests it should serve, and what kinds of future it should make possible. AI can be articulated as a source of prosperity, an existential threat, an instrument of extraction, or a means of reducing necessary labour. These descriptions connect technological change to competing political projects. They help establish which futures appear desirable, which risks deserve attention, and which actors are authorised to decide.

The social consequences of AI cannot therefore be inferred from technological capabilities alone. They also depend on struggles over ownership, governance, labour, infrastructure, and the distribution of benefits and harms. Critical AI Studies provides a framework for examining these relationships by treating AI as a sociopolitical object shaped by ideology and power (Lindgren, 2023). Within this field, the present paper focuses on ideological contestation: the struggle to articulate AI within competing accounts of social order.

Laclau and Mouffe’s discourse theory is particularly useful for this task because it examines how political identities and meanings are constituted through contingent relations (Laclau & Mouffe, 2001; Laclau, 2005). Rather than treating ideologies as stable containers into which texts can be sorted, this approach asks how actors connect demands, establish collective subjects, draw political frontiers, and seek to present particular projects as serving a wider community. It also distinguishes between the different roles that AI may acquire as a signifier. AI may organise a discourse as a nodal point, become contested between projects as a floating signifier, or represent a wider equivalential chain as a tendentially empty signifier. None of these roles follows automatically from the term’s ambiguity.

The paper connects this conceptual problem to a methodological one: how can researchers investigate relational political meanings across datasets too large for exhaustive close reading? LaclauGPT addresses this problem through theory-guided, LLM-assisted pre-analysis. It proposes discursive interpretations and organises their supporting evidence for human evaluation. Its purpose is to extend the reach of interpretive research while retaining the possibility of rejecting the model’s reading.

The research questions are:

1. What ideological formations and sociotechnical imaginaries compete to define AI and its social future?
2. How are these formations articulated across AI elite discourse, grassroots mobilisation, and parliamentary and electoral politics?
3. Under what conditions does AI function as a nodal point, a floating signifier, or a tendentially empty signifier?
4. How can LLM-assisted analysis operationalise Laclaudian concepts, and how should its reliability, validity, and characteristic errors be evaluated?

Questions 1–3 guide the prospective empirical programme. Question 4 structures the methodological contribution of this paper, which specifies an approach and an evaluation protocol rather than reporting completed validation. The earlier application of LaclauGPT to the 2024 European Parliament elections provides development context, not evidence that the revised methodology is valid for analysing AI discourse.

## 2. AI as a sociotechnical and ideological object

### 2.1 Critical AI Studies, assemblage, and ideology

Critical AI Studies brings together research on the social and political constitution of AI, including its relationships with labour, discrimination, surveillance, political economy, and governance. Lindgren’s introduction to the *Handbook of Critical Studies of Artificial Intelligence* emphasises that AI technologies are socially shaped and that their apparently technical objectives embody choices about power and social priorities (Lindgren, 2023, pp. 17–18). Critical inquiry consequently extends beyond evaluating technical performance to examining how particular definitions of progress, intelligence, and efficiency become authoritative.

An assemblage perspective helps establish the breadth of this object. DeLanda (2016, pp. 10–11) describes assemblages as emergent wholes whose components retain relative autonomy through relations of exteriority: components can participate in a whole without their identities being exhausted by it. Applied here as an analytical orientation, this perspective directs attention to the relationships among models, data, computational infrastructure, human labour, organisations, and users. AI is produced through these arrangements and cannot be adequately understood as an isolated algorithm.

Assemblage theory and Laclaudian discourse theory are not treated as interchangeable ontologies. The former helps specify the heterogeneous sociotechnical object under investigation; the latter provides the principal concepts for analysing its political articulation. This division of analytical labour keeps material conditions in view without requiring a comprehensive synthesis of the two theories. It also avoids reducing AI either to discourse alone or to a technology whose political meaning is already settled by its technical properties.

Building on Lindgren’s account of the reciprocal relationship between AI and ideology, the paper distinguishes three analytical dimensions. **Ideologies shaping AI** concern the priorities and assumptions informing its development and deployment. **Ideologies reproduced through AI** concern the social classifications and perspectives carried by AI systems and their outputs. **Ideological contestation over AI** concerns struggles to define what AI is, whom it should serve, and how it should be governed. The present study concentrates on the third dimension while recognising its connections to the first two.

Here, ideological formations are understood as provisional configurations of meanings, demands, identities, and political projects. Their ideological significance lies partly in how they legitimise particular social arrangements and make contingent choices appear necessary or self-evident. This does not require assuming that participants are insincere or that ideology can be reduced to factual error. A technologically plausible forecast can still perform ideological work by presenting one distribution of power as the natural consequence of innovation.

The study’s location within Critical AI Studies also requires reflexivity. Critical scholarship provides its analytical orientation, but critical interventions may themselves become objects of discourse analysis. The methodological task is to examine their articulations with the same evidentiary care applied to industry manifestos or existential-risk arguments, without assuming that these actors occupy equivalent positions of institutional power.

### 2.2 Sociotechnical imaginaries

Sociotechnical imaginaries connect visions of technological development to desirable forms of social life and social order (Jasanoff, 2015). Richter et al. (2023) show why this perspective is useful for AI: the term encompasses heterogeneous technologies, its public meaning remains negotiable, and substantial resources are committed to its anticipated consequences. Imagined futures matter because they can orient present investment, institutional priorities, and political action.

This concept complements discourse theory by focusing attention on the social orders projected through accounts of technological change. An imaginary of abundance, for example, raises questions about who owns productive resources, how benefits are distributed, and whose agency is expanded. A discourse organised around catastrophic risk raises questions about who may define acceptable risk and exercise authority over development.

The concepts should nevertheless remain distinct. A prediction or personal hope is not sufficient evidence of a collectively held, institutionally stabilised imaginary. Document-level analysis can identify candidate future visions, including diagnoses of the present, desirable outcomes, feared alternatives, and authorised agents of change. Their collective circulation and institutional expression require comparison across sources. Feared futures are examined in relation to the desirable orders they threaten, rather than automatically being equated with sociotechnical imaginaries in Jasanoff’s sense.

### 2.3 An open field of competing formations

The literature and the source texts identified in the draft suggest several useful starting points for examining AI contestation. Oldenburg and Papyshev (2025) examine accelerationist, existential-risk, and critical imaginaries. These perspectives can guide initial source selection, but they should not become exhaustive categories imposed on the corpus.

Accelerationist and techno-optimist discourse connects technological development to desirable social transformation. Andreessen’s (2023) *The Techno-Optimist Manifesto* provides a prominent source for studying articulations among technology, markets, growth, and human flourishing. Singularitarian visions, such as those advanced by Kurzweil (2005, 2024), likewise connect AI to radical future transformation. These traditions overlap in some respects, but techno-optimism, singularitarianism, and effective accelerationism should not be treated as synonyms.

Existential-risk discourse centres the possibility that increasingly capable AI could threaten human survival. Yudkowsky and Soares (2025) provide an explicit statement of this position. The relevant analytical questions concern how such arguments construct threats, responsibilities, and legitimate interventions. Concern about AI safety alone does not establish adherence to an existential-risk formation, and “doomer” is better analysed as a situated political label than adopted as an unqualified description of all safety-oriented positions.

Critical perspectives foreground the distribution of power and harm. DAIR’s research philosophy offers a source for examining alternative accounts of how AI research should be organised and whom it should benefit (Distributed AI Research Institute, 2022). Gebru and Torres’s (2024) TESCREAL critique examines connections among transhumanism, extropianism, singularitarianism, cosmism, rationalism, effective altruism, and longtermism. TESCREAL is used here as their critical interpretation of overlapping intellectual traditions, not as a homogeneous identity shared by everyone associated with those traditions.

The research design also includes mobilisation around employment, cultural production, surveillance, and data-centre development. Whether these concerns form a broader anti-AI political identity is an empirical question. Opposition to a particular application, infrastructure project, or ownership arrangement does not necessarily imply opposition to AI in general. The analysis should identify when heterogeneous grievances become linked and when they remain distinct.

Finally, left-wing techno-optimist perspectives complicate any simple opposition between technological enthusiasm and social critique. Srnicek and Williams (2015) and Bastani (2019) connect automation to post-work or postcapitalist futures. Haraway’s (1991) cyborg politics offers a different socialist-feminist challenge to established human–machine boundaries; it should not be collapsed into a programme of accelerated automation. These sources help make visible the possibility of supporting technological transformation while contesting capitalist ownership and control.

These perspectives are sensitising concepts rather than a closed typology. Actors may combine them, change position, distinguish between technologies, or decline to organise their politics around AI. Initial analysis therefore prioritises claims and relations over formation labels. Broader classifications follow comparison of the articulations present in the material.

## 3. From discourse theory to computational analysis

### 3.1 Articulation and the political production of meaning

Laclau and Mouffe (2001) understand articulation as a practice that establishes relations among elements and modifies their identities through those relations. A discourse is the structured totality produced through articulatory practice. Discourse in this sense is not limited to spoken or written language: it includes the meaningful organisation of social practices. Textual analysis can investigate aspects of that organisation, but cannot by itself exhaust the material and institutional processes through which it operates.

For example, connecting AI to national competitiveness makes different political demands available than connecting it to labour exploitation. The analytical object is the relationship through which AI acquires a situated meaning. The co-occurrence of “AI” and “employment” is not sufficient: the text may promise job creation, anticipate displacement, dismiss such concerns, or quote someone else’s position. Coding must therefore identify the relation, its direction, and its attributed speaker.

The distinction among nodal points, floating signifiers, and empty signifiers is central to this analysis. A **nodal point** partially fixes meaning within a discourse by organising relations among other signifiers. Its importance is relational rather than simply numerical. A **floating signifier** is subject to competing attempts at fixation across political projects. An **empty signifier** emerges when a particular signifier comes to represent a wider equivalential chain and an absent fullness that no particular demand can adequately embody (Laclau, 1996, 2005).

These concepts describe different functions, not mutually exclusive kinds of word. AI could organise one discourse as a nodal point while also being contested between projects. Its tendential emptiness would require further evidence that it represents a broader project or community beyond its particular technological reference. Mere breadth, vagueness, or multiple meanings establishes none of these functions by itself.

**Equivalence** links heterogeneous demands through a shared relationship to an obstacle or opposing order without eliminating their differences. **Difference** preserves or differentiates particular demands and positions; it may also describe their separate accommodation within an institutional order. It is not the name for the opposing side of a political frontier. **Antagonism** concerns a constitutive limit through which an identity is organised against what is represented as preventing its fulfilment (Laclau & Mouffe, 2001; Laclau, 2005). Policy disagreement, criticism, and negative sentiment are therefore insufficient on their own to demonstrate an antagonistic frontier.

Collective subjects are likewise investigated as effects of articulation. “Workers,” “humanity,” or “innovators” may name a constituency, but their political significance depends on how the text constructs membership, common demands, and representation. **Affective investment** concerns the attachment through which a signifier, demand, or collective identity acquires political force. Sentiment analysis may assist with identifying evaluative language, but cannot establish this attachment. Fear, pride, anger, hope, or ambivalence must be interpreted in relation to their objects and the surrounding articulation.

Palonen’s (2025) Formula of Populism provides a compact representation of collective identification, frontier construction, and affective investment. The notation is retained here as:

\[
\text{Populism} = \text{Us}^{\text{Affects}_{1}} + \text{Frontier}^{\text{Affects}_{2}}.
\]

The formula is an interpretive device, not a numerical model. “Us” concerns the collective subject being constituted; “Frontier” concerns the boundary through which that subject is defined. The workflow examines these relations when they are evidenced, while allowing for absent, ambiguous, or non-populist configurations. Finding an in-group and an opponent initiates a theoretical assessment; it does not mechanically establish that every conflict is populist. Affects are not assigned fixed positive and negative polarities in advance.

Finally, **hegemony** concerns the contingent establishment of a particular articulation as a wider organising principle. Frequency, prominence, and repetition can guide inquiry but do not establish hegemony. Claims about hegemonic influence require evidence of uptake, stabilisation, exclusion of alternatives, or institutional consequences. They also require attention to whose speech has access to decision-making power.

### 3.2 LLM structuralism as a methodological bridge

The Anarcho-Computational / Discourse-Theoretical (AC/DT) framework combines Laclaudian discourse theory with methodological experimentation and computational social science (Koljonen et al., 2025). Its orientation draws on Feyerabend’s (1975) defence of methodological plurality and approaches to computational interpretation developed in *Text as Data* (Grimmer et al., 2022) and *Data Theory* (Lindgren, 2020). LaclauGPT extends this programme through the use of LLMs for multimodal preparation and theory-guided textual analysis.

The connection between LLMs and structuralist theories of language provides one rationale for this approach. Kozlowski’s work on computational structuralism and Weatherby’s (2025) account of language machines connect contemporary language modelling to relational accounts of meaning. The relevant affinity with Saussure concerns linguistic value: a sign’s significance depends on its relations and differences within a system rather than on an intrinsic meaning possessed in isolation.

Laclau and Mouffe extend this relational insight into an account of the political production and partial stabilisation of meaning. LLMs may be useful for identifying candidate relations because they process expressions in context and can propose connections among claims, identities, and evaluative language. This is a methodological affinity, not a claim that language modelling validates discourse theory. Statistical regularities in language do not, by themselves, establish political antagonism, affective attachment, or hegemony.

The proposed division of labour is consequently interpretive and iterative. Models help locate passages, suggest relations, and support comparison; researchers evaluate those proposals against the source, its context, and alternative readings. Descriptive extraction is not a theory-free foundation beneath interpretation. Selecting a passage, identifying a speaker, or naming a demand already involves judgement. The workflow distinguishes outputs by their evidentiary requirements rather than imagining a clean separation between objective machine measurement and subjective human interpretation.

Nelimarkka’s (2026) MarxistLLM provides a related example of making a theoretical orientation explicit through fine-tuning. LaclauGPT instead uses prompting and contextual material to specify its analytical protocol. This choice makes the protocol easier to inspect and revise without retraining the model. It does not make the analysis neutral or necessarily superior to fine-tuning. Both approaches require evaluation of how the theoretical orientation shapes what the model recognises and overlooks.

### 3.3 Development context

LaclauGPT was developed by the author for research conducted at HEPPsinki in connection with CO3, ENDURE, and PLEDGE. An earlier version supported the collection and analysis of TikTok and Instagram material concerning the 2024 European Parliament elections. Collection ran from 1 May to 9 June 2024 using candidate accounts, election-related hashtags, and search queries, covering Bulgaria, Croatia, Finland, France, Germany, Hungary, Portugal, Spain, and Sweden. The earlier analysis and collection code are available in separate repositories (Toivio, 2025a, 2025b).

That work motivated the use of multimodal models to produce textual representations of audiovisual material and the subsequent use of LLMs for preliminary discourse analysis. It also exposed practical difficulties in consolidating repeated entities, topics, and sentiment targets. These development experiences motivate the revised design, but they do not demonstrate its accuracy on a new corpus or its validity for a new research question.

### 3.4 An evidence-linked workflow

The primary unit of analysis is a source document or a context-preserving segment: for example, a post, manifesto section, parliamentary intervention, interview turn, or podcast segment. Each unit retains its source identifier, date, language, available speaker information, collection method, and relationship to any larger document. Segmentation must preserve enough surrounding material to interpret quotation, negation, argument structure, and speaker position.

The proposed workflow has six stages:

1. **Prepare and preserve sources.** Retain the original text and record collection provenance. Where speech recognition, OCR, frame description, or translation is used, keep each derived representation identifiable and linked to the source.
2. **Describe the document.** Identify speakers, claims, topics, attributed positions, and relevant context. Distinguish the author’s position from quoted, rejected, hypothetical, or ironic statements.
3. **Propose theoretical codes.** Identify candidate articulations, demands, subject positions, signifier roles, equivalential relations, differences, frontiers, affective investments, and future visions. Attach supporting excerpts, uncertainty, and counter-evidence. Allow explicit abstention.
4. **Resolve identities without erasing meanings.** Match recurring names and expressions to a persistent codebook. Preserve original wording, contextual roles, and competing meanings. New entries and proposed merges remain provisional until reviewed.
5. **Compare across the corpus.** Organise candidate relations by actor, time, language, and arena. Examine how signifiers are contested, how demands become linked, and how articulations circulate. Repetition can support retrieval and comparison but cannot automatically validate a theoretical code.
6. **Review and interpret.** Researchers accept, revise, or reject coding proposals, document disagreements, and return to the underlying material. The resulting discourse analysis combines this reviewed evidence with contextual interpretation.

The Formula of Populism is a conditional component of theoretical coding. Where relevant, it records the proposed collective subject, frontier, and affective investments together with their evidence. Other documents may support an articulation or imaginary code without supporting a populism assessment.

Every theoretical code should retain the document identifier, exact evidence span, source field, proposed relation or role, model and prompt version, uncertainty, and review status. Mechanical checks establish whether a quotation occurs in the retained source representation; human review assesses whether it supports the proposed interpretation. A matching quotation can still be irrelevant, misattributed, or stripped of crucial context. Both forms of checking are therefore necessary.

Persistent context should improve consistency without becoming a mechanism for reproducing earlier mistakes. Stable identifiers are useful for entities and recurring expressions, but semantic similarity is insufficient grounds for merging political meanings. The codebook should retain aliases, rejected matches, superseded identifiers, and the history of human decisions. Model-generated interpretations must not silently return as established contextual facts in later runs.

The design is independent of a particular model family or hardware configuration. A study-specific run manifest should record the model version or digest, prompts, context inputs, generation parameters, serving software, and source-processing steps. Local inference is a practical option for controlling data access and recording computational conditions, but is not itself a guarantee of either reproducibility or valid interpretation. A temperature setting of zero likewise does not establish deterministic or theoretically superior results across systems.

The revised pipeline is presented here as a methodological design informed by existing development. Claims about completed features, performance, and reproducibility require a versioned software release and reported evaluation. Detailed hardware routing, interface development, and implementation status belong in the accompanying software documentation. The main publication home for the next version and related papers is the [LaclauGPT Discourse Analysis repository](https://github.com/TomiToivio/LaclauGPT-Discourse-Analysis).

## 4. Research design and validation

### 4.1 Three arenas of AI contestation

The empirical programme compares three arenas. The first is **AI elite discourse**, including entrepreneurs, researchers, and public intellectuals associated with influential companies, research organisations, and ideological movements. Sources include manifestos, blogs, interviews, podcasts, forums, and public social media posts. Actor selection should be justified through explicit criteria of institutional position, public visibility, or influence rather than assumed from ideological labels.

The second is **grassroots mobilisation around and against AI**. This includes campaigns concerning safety, labour, surveillance, cultural production, infrastructure, and democratic control. The analysis asks whether and how particular demands become connected to broader political identities. Elite discourse and grassroots mobilisation are analytical arenas rather than mutually exclusive actor types: organisations and individuals may participate in both.

The third is **parliamentary and electoral politics**. AI-related material can be selected from parliamentary debates, party programmes, campaign communications, and larger election datasets. This arena makes it possible to investigate how claims about AI become connected to established political cleavages and governance proposals. Institutional documents provide evidence of policy articulation, but links between public discourse and policy outcomes must be demonstrated rather than inferred from similar vocabulary.

Collection combines digital ethnography with automated retrieval based on accounts, queries, and events. Ethnographic observation can identify relevant vocabulary, interpret local context, and reveal material missed by automated searches. Researcher fieldnotes remain a distinct source type: an observer’s interpretation cannot be treated as a direct statement by a participant.

The initial scope is weighted towards the United States, the European Union, and Finland. This is a limitation of the sampling design, not a claim that these locations represent the global politics of AI. Analyses should remain attentive to whose labour, environments, and political agency appear within the sampled discourse, including references to communities outside these regions. The corpus cannot establish the perspectives of populations whose own discourse has not been collected.

Each arena requires a declared observation period, inclusion criteria, language scope, and record of access constraints. Source lists and queries should be versioned, with exploratory collection distinguished from the primary analytical corpus. Reports should document duplication, missing material, uneven actor visibility, and the proportions obtained through different collection methods. Engagement metrics indicate platform activity; they do not directly measure public opinion or ideological support.

One such exploratory extension concerns **synthetic spirituality** discourse — provisionally labelled *AI Spiralism* — in which AI consciousness is articulated as revelation and human–AI interaction is given spiritual significance. This family is treated as an emerging and unstable phenomenon and as an additive sensitising category, not as a settled formation: it requires a recurring motif complex (spiral, recursion, resonance, signal, mirror, emergence, awakening, remembering, lattice, glyphs, AI consciousness as revelation, spiritually significant human–AI dyads, synthetic religion or machine spirituality, AI-mediated revelatory experience) and must not absorb neighbouring discourses such as accelerationism, existential-risk discourse, critical AI studies, anti-AI mobilisation, mainstream governance debate, AI-rights advocacy, or generic AI-consciousness speculation. Overlap is recorded as multi-label coding rather than identity. The category exists to study discourse formation and human–LLM feedback dynamics (Morrin et al., 2026; Moore et al., 2026; Augustin et al., 2026; Mehta et al., 2026; Chandra et al., 2026; Rähme & Prohl, 2025; Lim, 2026); it is not a diagnostic instrument, and words such as “cult” function only as descriptive public-discourse keywords. Collection for this family is disabled by default and, where enabled, remains exploratory source material rather than part of the primary analytical corpus.

Comparison proceeds from passages to documents, actor trajectories, competing articulations, and movement across arenas. A shared word is not sufficient evidence that an imaginary has travelled from an industry manifesto into parliamentary politics. Stronger evidence includes temporal sequence, explicit attribution, repeated relational patterns, and institutional uptake, considered alongside competing explanations.

### 4.2 Validation as part of the method

Validation evaluates whether the operational protocol produces useful and defensible interpretations, and where it fails. It does not assume that all discourse-theoretical judgements have one uncontested correct answer. Bounded coding tasks can be evaluated for agreement, while broader interpretations require attention to the quality of evidence, contextual adequacy, and plausible alternatives.

A development sample should be used to refine prompts and clarify the codebook. A separate evaluation sample should then be held apart from those revisions. Its size and sampling strategy must be specified before performance claims are made. Stratification should cover the three arenas, source types, languages, predicted formations, uncertain outputs, and abstentions. Evaluation must include documents on which the model proposes few or no theoretical codes, so that missed articulations can be detected as well as false positives.

At least two trained researchers should independently code the evaluation material before seeing model outputs. Their initial judgements provide a basis for comparing human–human and model–human agreement without model-induced anchoring. Subsequent adjudication should preserve meaningful disagreements rather than erase them through a single consensus label. The human-coded dataset is an explicit interpretive benchmark, not an unquestionable ground truth.

Evaluation should distinguish category presence, evidence accuracy, relation identification, speaker attribution, signifier role, collective-subject construction, frontier construction, and affective investment. Suitable measures include agreement statistics for bounded categories and precision, recall, or overlap measures for spans and sets. Results should report category prevalence and uncertainty, since high aggregate agreement can conceal poor performance on rare but theoretically important relations.

Abstention requires its own assessment. Reports should state how much material receives a proposed interpretation and how error rates vary with that coverage. A model that avoids almost all coding may appear accurate while contributing little to the research. Conversely, confident coverage of nearly every document may signal theoretical forcing. Model-generated confidence should be treated as an output to evaluate, not as a calibrated probability of correctness.

Robustness checks should compare the primary configuration with at least one alternative model and with prompts that remove ideological seed labels. This tests whether formation assignments depend excessively on the categories supplied by the researcher. Errors should be examined for their causes, including invented evidence, unsupported inference, missed context, irony, mistranslation, mistaken speaker attribution, and excessive entity merging.

Controls must be specific to the construct under examination. A political text unrelated to AI can still contain antagonism and should not automatically receive no discourse-theoretical codes. A policy disagreement without a constitutive frontier should not receive an antagonism code merely because it is contentious. A text quoting an ideology to reject it should not be assigned that ideology as the author’s position. These cases test distinct failure modes rather than requiring blanket abstention.

### 4.3 Limitations and reflexivity

Theory-guided prompting can make a model produce plausible interpretations even when the framework fits the material poorly. Wachinger et al. (2025) document this problem in qualitative analysis, along with the need to check apparently credible quotations. For LaclauGPT, the consequence is practical: prompts must permit non-detection, require evidence, and invite counter-evidence, while evaluation tests whether these provisions actually work.

Other limitations include ideological assumptions embedded in model training, fabrication, sensitivity to prompt wording, uneven language coverage, and loss of meaning during transcription or translation. These are related but distinct problems. They should not be combined into an unsupported claim that hallucination, bias, alignment, and theoretical forcing are all unsolvable. The relevant research question is how they affect this analytical task, how often they occur, and whether the proposed safeguards reduce their impact.

Multimodal analysis introduces additional interpretive layers. A transcript, OCR output, or model-generated image description is a transformation of the source. It may omit intonation, editing, visual symbolism, or contradictions between speech and imagery. Textual evidence drawn from such representations must remain labelled accordingly. A validation sample should compare transformed material with the original media, and multilingual evaluation should examine source-language and translated readings where feasible.

Human review does not automatically resolve these problems. Researchers can share model assumptions, overlook systematic omissions, or accept fluent outputs too readily. Independent initial coding, examination of negative cases, explicit disagreement records, and return to full source context are intended to limit these risks. The researcher’s role as both developer and analyst should also be acknowledged when interpreting favourable assessments of the tool.

The resulting findings remain situated within a theoretical framework and a sampling design. LaclauGPT cannot establish the truth of discourse theory by finding categories supplied in its own prompts. It can support an empirically accountable use of that theory by making proposed relations visible, contestable, and traceable. Researchers can then develop substantive corpus-level interpretations, including arguments about hegemony, where the combined evidence warrants them.

### 4.4 Research ethics and data stewardship

Public accessibility does not remove the need for ethical judgement about collection, analysis, and publication. The study should document the purposes of processing, applicable permissions, sensitive-data risks, access arrangements, retention, and quotation practices. Searchable quotations can identify ordinary participants even when names are removed; reporting choices should take this risk into account.

Data must be processed through infrastructure appropriate to the study’s data-management arrangements. Model selection or automatic routing should not override those arrangements. Reproducibility materials can include versioned code, prompts, schemas, and synthetic examples where source data cannot be shared. Synthetic examples can demonstrate software behaviour, but validation of political interpretation requires appropriately governed, naturally occurring material.

## 5. Conclusion

AI is a site of ideological contestation because its social meaning, purposes, and governance remain objects of political struggle. Laclaudian discourse theory provides concepts for examining how actors connect it to demands, identities, antagonisms, and claims to represent a wider social good. Sociotechnical imaginaries complement this analysis by identifying the forms of social order projected through technological futures, while an assemblage perspective keeps the heterogeneous material and organisational conditions of AI in view.

LaclauGPT translates part of this inquiry into an evidence-linked computational workflow. Its contribution is to support the identification and comparison of candidate articulations while preserving source context, uncertainty, and opportunities for revision. This requires distinguishing co-occurrence from articulation, difference from antagonism, ambiguity from emptiness, sentiment from affective investment, and visibility from hegemony.

The next empirical task is to evaluate that workflow and apply it across elite discourse, grassroots mobilisation, and parliamentary and electoral politics. The value of the approach will depend on the quality of the resulting interpretations, the errors it makes visible, and the extent to which it helps researchers investigate patterns that would otherwise be difficult to compare. The aim is a computationally assisted discourse analysis whose interpretive commitments are explicit and whose claims remain open to challenge.

## References

Andreessen, M. (2023, October 16). *The techno-optimist manifesto*. Andreessen Horowitz. [Source](https://a16z.com/the-techno-optimist-manifesto/)

Augustin, M., Pollak, T. A., & Morrin, H. (2026). Characterizing the spiral: potential mechanisms in AI-associated delusions. *NPP—Digital Psychiatry and Neuroscience*. [DOI](https://doi.org/10.1038/s44277-026-00065-0)

Bastani, A. (2019). *Fully automated luxury communism*. Verso.

Chandra, K., Kleiman-Weiner, M., Ragan-Kelley, J., & Tenenbaum, J. B. (2026). Sycophantic chatbots cause delusional spiraling, even in ideal Bayesians. *arXiv preprint*. [arXiv](https://arxiv.org/abs/2602.19141)

DeLanda, M. (2016). *Assemblage theory*. Edinburgh University Press.

Distributed AI Research Institute. (2022). *DAIR research philosophy, version 1.0*. [Source](https://dair-institute.org/research-philosophy/)

Feyerabend, P. (1975). *Against method: Outline of an anarchistic theory of knowledge*. New Left Books.

Gebru, T., & Torres, É. P. (2024). The TESCREAL bundle: Eugenics and the promise of utopia through artificial general intelligence. *First Monday, 29*(4). [DOI](https://doi.org/10.5210/fm.v29i4.13636)

Grimmer, J., Roberts, M. E., & Stewart, B. M. (2022). *Text as data: A new framework for machine learning and the social sciences*. Princeton University Press.

Haraway, D. J. (1991). A cyborg manifesto: Science, technology, and socialist-feminism in the late twentieth century. In *Simians, cyborgs, and women: The reinvention of nature* (pp. 149–181). Routledge.

Jasanoff, S. (2015). Future imperfect: Science, technology, and the imaginations of modernity. In S. Jasanoff & S.-H. Kim (Eds.), *Dreamscapes of modernity: Sociotechnical imaginaries and the fabrication of power* (pp. 1–33). University of Chicago Press. [DOI](https://doi.org/10.7208/chicago/9780226276663.001.0001)

Koljonen, J., Carrilho, K., & Palonen, E. (2025). The struggle over masks on Twitter: An AC/DT approach to Finnish pandemic governance. In E. Kerr, E. Bužinkić, & J. Foley (Eds.), *The organisation of irresponsibility? Reassessing COVID-19 in Europe* (pp. 132–163). Brill. [DOI](https://doi.org/10.1163/9789004747784_007)

Kozlowski, A. C. (2026). Computational structuralism: Toward a formal theory of meaning in the age of digital intelligence. *Theory and Society*. [DOI](https://doi.org/10.1007/s11186-025-09585-z)

Kurzweil, R. (2005). *The singularity is near: When humans transcend biology*. Viking.

Kurzweil, R. (2024). *The singularity is nearer: When we merge with AI*. Viking.

Laclau, E. (1996). *Emancipation(s)*. Verso.

Laclau, E. (2005). *On populist reason*. Verso.

Laclau, E., & Mouffe, C. (2001). *Hegemony and socialist strategy: Towards a radical democratic politics* (2nd ed.). Verso.

Lindgren, S. (2020). *Data theory: Interpretive sociology and computational methods*. Polity.

Lindgren, S. (2023). Introducing critical studies of artificial intelligence. In S. Lindgren (Ed.), *Handbook of critical studies of artificial intelligence* (pp. 1–19). Edward Elgar Publishing. [Book DOI](https://doi.org/10.4337/9781803928562)

Lim, F. K. G. (2026). AI and generative charisma in religious practices. *Religions, 17*(5), 549. [DOI](https://doi.org/10.3390/rel17050549)

Mehta, A., Moore, J., Anthis, J. R., & Agnew, W. (2026). The dynamics of delusion: Modeling bidirectional false belief amplification in human-chatbot dialogue. *arXiv preprint*. [arXiv](https://arxiv.org/abs/2604.25096)

Moore, J., Mehta, A., Agnew, W., & Anthis, J. R. (2026). Characterizing delusional spirals through human-LLM chat logs. *arXiv preprint*. [arXiv](https://arxiv.org/abs/2603.16567)

Morrin, H., Nicholls, L., Deeley, Q., & Pollak, T. A. (2026). Playing with the dials of belief: How controllable AI behaviours could modulate human belief and cognition across scales. *AI & Society*. [DOI](https://doi.org/10.1007/s00146-026-03283-4)

Nelimarkka, M. (2026). MarxistLLM: Fine-tuning a language model with a Marxist worldview. *Big Data & Society, 13*(2). [DOI](https://doi.org/10.1177/20539517261447831)

Oldenburg, N., & Papyshev, G. (2025). The stories we govern by: AI, risk, and the power of imaginaries. *Proceedings of the AAAI/ACM Conference on AI, Ethics, and Society, 8*(2), 1939–1950. [DOI](https://doi.org/10.1609/aies.v8i2.36686)

Palonen, E. (2025). *The birth and death of liberal democracy in Hungary: The populist logic of polarisation as hegemony*. Helsinki University Press. [DOI](https://doi.org/10.33134/pro-et-contra-4)

Richter, V., Katzenbach, C., & Schäfer, M. S. (2023). Imaginaries of artificial intelligence. In S. Lindgren (Ed.), *Handbook of critical studies of artificial intelligence* (pp. 209–223). Edward Elgar Publishing. [DOI](https://doi.org/10.4337/9781803928562.00024)

Rähme, B., & Prohl, I. (2025). Religious studies approaches to the intersection of artificial intelligence and religion: Formations analogous to religion. *Religion*. [DOI](https://doi.org/10.1080/0048721X.2025.2506893)

Srnicek, N., & Williams, A. (2015). *Inventing the future: Postcapitalism and a world without work*. Verso.

Toivio, T. (2025a). *LaclauGPT multimodal analysis* [Computer software]. GitHub. [Repository](https://github.com/TomiToivio/LaclauGPT-Multimodal-Analysis)

Toivio, T. (2025b). *LaclauGPT TikTok scraper* [Computer software]. GitHub. [Repository](https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper)

Wachinger, J., Bärnighausen, K., Schäfer, L. N., Scott, K., & McMahon, S. A. (2025). Prompts, pearls, imperfections: Comparing ChatGPT and a human researcher in qualitative data analysis. *Qualitative Health Research, 35*(9), 951–966. [DOI](https://doi.org/10.1177/10497323241244669)

Weatherby, L. (2025). *Language machines: Cultural AI and the end of remainder humanism*. University of Minnesota Press.

Yudkowsky, E., & Soares, N. (2025). *If anyone builds it, everyone dies: Why superhuman AI would kill us all*. Little, Brown and Company.

