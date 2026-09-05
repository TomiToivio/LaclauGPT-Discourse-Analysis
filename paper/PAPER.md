# LaclauGPT: Ideological contestation over AI

## Abstract

This paper examines the ideological contestation over artificial intelligence (AI): the struggle between competing political projects to articulate and temporarily fix the meaning of AI as a contested signifier. Drawing on Ernesto Laclau's discourse theory, Emilia Palonen's Formula of Populism, and the concept of sociotechnical imaginaries, the paper maps the contemporary ideological field surrounding AI — accelerationism, existential-risk discourse, Critical AI studies, an emerging anti-AI backlash, and left-wing techno-optimist visions — and develops LaclauGPT, a computational methodology that operationalises Laclaudian discourse analysis with large language models. Rather than assigning texts to fixed ideologies, the methodology identifies candidate signifiers, equivalential and differential relations, antagonistic frontiers, affective investments, sociotechnical imaginaries, and ideological formations. Every discourse-theoretical model code must carry a source excerpt and remain provisional, while the model may abstain when a theoretical category is not evidenced. LaclauGPT produces theory-guided pre-analysis of large textual datasets for human researchers, who remain responsible for validation and final interpretation. The paper specifies a research design spanning three arenas: the discourse of AI elites, grassroots mobilisation around and against AI, and AI in parliamentary and electoral politics.

**Keywords:** artificial intelligence; ideology; discourse theory; Laclau; sociotechnical imaginaries; large language models; populism; hegemony; critical AI studies; computational social science

## Author note

Tomi Toivio, Helsinki Hub on Emotions, Populism and Polarisation (HEPPsinki), University of Helsinki. ORCID: 0000-0002-1335-0478. Funding: European Union (CO3, ENDURE, PLEDGE) and the Research Council of Finland.

## 1. Introduction

Artificial intelligence is developing rapidly and has become a key technology shaping the political, social, and economic trajectory of the future. However, its consequences are not technologically predetermined. They depend on political and ideological struggles over corporate power and user agency, economic growth and employment, and the environmental costs of expanding data-centre infrastructure. AI is therefore not only a technology but also a contested political object around which competing visions of the future are articulated. These descriptions do not merely predict the future: they help delimit which futures appear desirable, inevitable, governable, or impossible.

This paper examines the ideologies of AI within the emerging field of Critical AI Studies. It uses Ernesto Laclau's discourse theory as its primary theoretical framework and develops LaclauGPT as a computational methodology for analysing competing articulations of AI, its risks, and its imagined futures.

The research questions are:

1. What major ideological formations and sociotechnical imaginaries compete to define AI and its social future?
2. How are these positions articulated by AI industry elites, ideological movements, and actors in parliamentary politics, and how do their chains of equivalence and difference, nodal points, antagonistic frontiers, subjects, and affects vary across these arenas?
3. Under what empirical conditions does AI function as a nodal, floating, or tendentially empty signifier?
4. How can LLMs be used to operationalise Laclaudian discourse analysis across large textual datasets, and with what reliability, validity, and characteristic errors?

Questions 1–3 specify the empirical programme that the LaclauGPT pipeline is designed to address; Question 4 is answered methodologically in this paper. This paper is a theory-guided methodological position paper with a prospective research design; the EP24 study (Section 3.2) is presented as an earlier implementation of the pipeline, not as validation of the revised AI-contestation workflow.

The paper makes two related contributions: it develops a discourse-theoretical approach to the ideology of AI and advances LaclauGPT as a computational methodology for social data science.

## 2. Ideologies of AI

### 2.1 Critical AI Studies and the ideology of AI

Lindgren (2023) conceptualizes Critical AI Studies as an emerging multidisciplinary field concerned with the sociopolitics of AI and distinguished by its critical distance from the AI industry. Its central objects of critique include the political economy of AI, ideology, and power relations. This study focuses on the ideology of AI, understood as a contested field of competing ideological formations.

Situated within political science and Critical AI Studies, this study combines Laclaudian discourse theory with social data science methods to analyse ideological contestation over AI.

Simon Lindgren (2023) conceptualizes AI in two complementary ways: as an empty signifier and as an assemblage. The former draws on Ernesto Laclau's discourse theory, while the latter draws on Manuel DeLanda's assemblage theory.

In Laclau's (2005) discourse theory, an empty signifier is a signifier whose particular meaning becomes partially emptied as it comes to represent a wider and heterogeneous set of demands. Terms such as "justice" can perform this function by naming an absent social fullness rather than possessing a single fixed meaning. "Artificial Intelligence" can similarly signify very different things, such as existential risk, a transhumanist utopia, economic growth, or unemployment. As a nodal point, AI can anchor relations among other signifiers within a discourse and thereby contribute to the partial fixation of their meaning. This paper primarily draws on Laclau's discourse theory, which is discussed in more detail below.

In Laclau's account these functions are distinct and should not be conflated. The empty signifier names a constitutively irrepresentable place within a system of signification (Laclau, 2005, p. 105); the floating signifier is only partially fixed and remains contested across discourses (Laclau & Mouffe, 2001); the nodal point is the relational position from which a discourse partially fixes the meaning of its elements. How AI operates in each respect is an empirical question addressed in Section 2.2.

DeLanda (2016, pp. 10–11) conceptualizes assemblages as irreducible wholes produced through relations of exteriority, whose components retain relative autonomy rather than being fused into a seamless totality. Lindgren (2023) conceptualizes AI as an assemblage consisting of (I) machines, (II) humans, (III) intelligence, (IV) automation, (V) neural networks, (VI) machine learning, (VII) algorithms, (VIII) predictions, (IX) deep learning, (X) data, (XI) imaginaries, (XII) sociotechnical systems, (XIII) environment, (XIV) tools and artefacts, (XV) ideology, (XVI) power, (XVII) identities and subjects that it interpellates, (XVIII) political economy, (XIX) labour, and (XX) potential additional elements.

For the purposes of this paper, the primary focus is on ideology, while sociotechnical imaginaries are also examined. Richter et al. (2023) argue that sociotechnical imaginaries are particularly useful for critical studies of AI because AI is sociopolitically consequential, open to multiple interpretations, and functions as a broad umbrella term encompassing heterogeneous technologies. Sociotechnical imaginaries are "collectively held, institutionally stabilized, and publicly performed visions of desirable futures" (Jasanoff, 2015, p. 4), linking imagined forms of social order to developments in science and technology.

Lindgren (2023) distinguishes between **ideology behind AI** and **ideology within AI**. The former refers to the ideological formations promoting and shaping AI, while the latter concerns ideological assumptions embedded within AI systems themselves. This study adds a third analytical dimension: **ideological contestation over AI**. This refers to struggles between competing political projects to articulate and temporarily fix the meaning of AI as a contested signifier. Such contestation can incorporate both the ideologies surrounding the development of AI and those reproduced through AI systems.

From this perspective, AI can be understood as both a **tendentially empty signifier** and a **floating signifier**. It becomes tendentially empty insofar as it condenses increasingly heterogeneous meanings and demands, and floating insofar as competing ideological projects struggle to fix its meaning in different ways. The two categories are distinct: a floating signifier is only partially fixed and remains contested across discourses, whereas an empty signifier names a constitutively irrepresentable place within signification that becomes the condition of any partial fixation (Laclau, 2005). Within particular discourses, AI may function as a **nodal point** around which other signifiers are organized. In others, it may occupy a less central position or be articulated as part of an antagonistic frontier. Some actors may remain largely indifferent to AI altogether.

### 2.2 AI as a contested signifier

Oldenburg and Papyshev (2025) identify three prominent sociotechnical imaginaries within contemporary AI debate: accelerationist, existential-risk, and Critical AI imaginaries:

1. Machine Intelligence Research Institute (MIRI)'s *The problem* (Machine Intelligence Research Institute [MIRI], 2025) is used as an example of X-Risk doomer imaginaries. The X-Risk doomer argument is crystallised in *If anyone builds it, everyone dies: Why superhuman AI would kill us all* (Yudkowsky & Soares, 2025).
2. The Distributed AI Research Institute (DAIR, 2022) provides a prominent example of a Critical AI perspective, explicitly centring on questions of power, labour, marginalized communities and the social harms of AI.
3. Marc Andreessen's *The techno-optimist manifesto* (Andreessen, 2023) is used as an example of accelerationism.

Effective Accelerationism (e/acc) is a contemporary pro-acceleration movement advocating rapid and minimally constrained AI development. It draws on broader accelerationist traditions and explicitly positions itself against AI doomers and decelerationists who advocate slower and more safety-oriented development (Okolo, 2025).

Gebru and Torres (2024) have criticized the AI ideologies as the TESCREAL bundle of ideologies: Transhumanism, Extropianism, Singularitarianism, Cosmism, Rationalism, Effective Altruism and Longtermism. Gebru and Torres (2024) conceptualize TESCREAL as a bundle of overlapping ideologies and argue that important elements of this intellectual tradition have historical roots in Anglo-American eugenics.

It is not necessary to define all of the TESCREAL ideologies in this paper, but Ray Kurzweil's theory of the technological singularity (Kurzweil, 2005, 2024) can be seen as one of the most influential ideas associated with them. According to the singularity hypothesis, accelerating technological development, including advances in artificial intelligence and recursive machine improvement, could lead to extremely rapid growth in machine intelligence and eventually to a radically transformed transhuman future.

There is also evidence of an emerging political backlash against AI (Borwein et al., 2026). This includes concerns over employment, the environmental and economic impacts of data centres, surveillance, cultural production and the concentration of power in technology corporations. In the United States, these concerns have increasingly entered mainstream politics, including through Bernie Sanders's calls for limits on AI development and AI data-centre expansion (Sanders, 2026). Whether a comparable anti-AI political formation is emerging in Finland remains an empirical question for this study.

There are also left-wing techno-optimist perspectives on AI. Cugurullo's (2025) concept of AIdeology includes visions of sustainable AI addressing environmental problems, a posthuman society populated by humans and artificial intelligences, and a post-work society in which both labour and capitalism become obsolete. Similar left-wing techno-optimist visions can be found in Srnicek and Williams's (2015) postcapitalist politics and Bastani's (2019) *Fully Automated Luxury Communism*. These perspectives also resonate with Haraway's (1991) *Cyborg Manifesto*, which challenges the boundaries between humans and machines and uses the cyborg as a figure for imagining new forms of socialist and feminist politics.

The purpose of this study is not to assume these categories in advance as fixed ideologies, but to investigate how such positions are articulated, how their boundaries overlap and shift, which nodal and floating signifiers organize them, and which articulations acquire hegemonic influence in political decision-making.

The contemporary ideological field surrounding AI cannot be reduced to a simple division between technological optimism and pessimism. Oldenburg and Papyshev (2025) identify three prominent sociotechnical imaginaries: accelerationism, existential-risk discourse, and Critical AI. These are increasingly joined by a broader anti-AI backlash concerned with labour displacement, data centres and the social consequences of automation, as well as by left-wing techno-optimist imaginaries in which automation is articulated with post-work, postcapitalist or posthuman futures.

### 2.3 A field of formations, not a closed typology

These categories are used as **sensitising concepts and seed candidates**, not as a closed codebook. A text mentioning safety is not therefore classified as "x-risk"; opposition to a data centre is not automatically "anti-AI"; support for public automation is not automatically accelerationist. The analysis must show how elements are articulated, by whom, against what alternatives, and with which institutional consequences. Hybrid, ambivalent, and indifferent positions remain possible outcomes.

The empirical scope is weighted toward the United States, the European Union, and Finland. This is a sampling boundary, not a claim that these sites exhaust the global field. Research on the US–China dual core of global AI collaboration provides relevant geopolitical context (Zhang et al., 2026), but a Western-weighted corpus cannot support universal claims about global AI ideology.

## 3. LaclauGPT

### 3.1 Theoretical foundation

Anarcho-Computational / Discourse-Theoretical (AC/DT) framework (Koljonen et al., 2025) is inspired by Laclaudian discourse theory, Feyerabendian methodological experimentation (Feyerabend, 1975) and computational social science methods presented in books Text as Data (Grimmer et al., 2022) and Data Theory (Lindgren, 2020).

This paper uses the LaclauGPT social data science framework developed by the AC/DT research team at Helsinki Hub on Emotions, Populism and Polarisation (HEPPsinki). LaclauGPT is named after Ernesto Laclau, whose discourse theory, developed with Chantal Mouffe (Laclau & Mouffe, 2001) and further elaborated in Laclau (2005), is the framework's main component. Emilia Palonen's Formula of Populism (Palonen, 2025) is used with Laclau's and Mouffe's theory to create a more compact summary of the Laclaudian theory.

Sociotechnical imaginaries (Jasanoff & Kim, 2015) are an analytical complement to Laclaudian discourse theory: the way AI is seen as a threat or opportunity is a key determinant in the ideological stance, as the long-term social consequences of AI remain uncertain and politically contested. It has to be noted that sociotechnical imaginaries are different from Laclau's and Mouffe's social imaginaries. An imaginary is not merely a topic or an attitude: its coding should capture at least a diagnosis of the present, a normative or feared future, the role assigned to technology, the distribution of human agency, and the actors authorised to govern the transition.

In Laclau and Mouffe's (2001) discourse theory, articulation refers to any practice establishing a relation among elements such that their identity is modified as a result of the articulatory practice; elements thus articulated become moments in a discourse. The element of artificial intelligence can be connected to economic growth, existential risk or loss of jobs, giving it a rather different meaning. "AI" articulated with abundance, markets, and human flourishing is not the same object as "AI" articulated with extraction, surveillance, and precarious labour. Consequently, co-occurrence alone is not an articulation, and frequent occurrence alone does not establish a nodal point: the analysis must identify a relation and show how it conditions meaning.

A nodal point is a privileged signifier that anchors the meaning of other signifiers in the discourse (Laclau & Mouffe, 2001). We can think about the nodal point of risk, around which the entire question of AI is framed in the X-Risk ideology.

A floating signifier refers to a signifier with a somewhat different meaning in different discourses: in the case of AI, regulation is typically seen quite differently by the accelerationist and critical sides of discourse (Laclau & Mouffe, 2001). Care is needed here: Hegemony and Socialist Strategy uses "floating" sparingly, and the regulation example is better treated as an illustration of contestation than as a canonical application of the concept. A floating signifier is subject to competing attempts at fixation across discourses; its identification is therefore comparative, and a single document can nominate a floating-signifier candidate but cannot establish floating status.

The empty signifier, developed by Laclau in the 1990s (Laclau, 1996) and fully elaborated in Laclau (2005), is distinct from the floating signifier: where the floating signifier is only partially fixed and contested across discourses, the empty signifier names a constitutively irrepresentable place within signification — "there is a place, within the system of signification, which is constitutively irrepresentable; in that sense it remains empty, but this is an emptiness which I can signify" (Laclau, 2005, p. 105). An empty signifier is not simply an ambiguous, broad, or multiply used word: it emerges when a particular signifier comes to represent a heterogeneous equivalential chain and names an absent or impossible fullness. For the purposes of this study artificial intelligence is the main empty-signifier candidate (Lindgren, 2023), meaning the possibility of utopian progress to some and existential risk to others — but this status must be demonstrated for each discourse rather than assumed.

Logics of equivalence and difference are important in the construction of the antagonistic discourse. Chains of equivalence are used to construct "us": the signifiers that are welded together into a political identity. This identity is also constructed by using chains of difference to construct the "frontier" which is antagonistic to "us" (following Palonen's operationalisation, 2025). We can think about how Marc Andreessen (2023) constructs artificial intelligence as part of an articulation of "us" — while anti-AI protesters would place AI in the antagonistic frontier. Difference is not synonymous with hostility: antagonism names a limit at which an identity is constituted against an outside, and ordinary criticism or policy disagreement is not sufficient evidence of it.

Laclau argues that the affective dimension is central to hegemonic articulation: "the affective dimension plays a central role here" and "there is no populism without affective investment in a partial object" (Laclau, 2005). Affective investment refers to the affects attached to the elements of an articulation — and it is precisely this affective component that the Formula of Populism operationalises and that the LaclauGPT pipeline codes for. Affects are coded from evidence rather than assigned by polarity: an Us may be invested with anger or grievance, and an opponent may be represented with envy, admiration, anxiety, or ambivalence.

Palonen (2025) proposes a Formula of Populism, in which the antagonistic sides are articulated as Us and the Frontier. Us is the community populism argues for, and the frontier is the limit of the community. The formula also captures the affects related to the Us and Frontier elements.

    Populism = Us^(Affects1) + Frontier^(Affects2)

Us contains the elements that are articulated as a political subject; frontier contains the antagonistic outside elements. The formula also contains the affective investment in the "us" and "frontier" sides of the equation. The formula is applied only when a text constructs both a collective political subject and a constitutive frontier.

Hegemony, finally, is not a document label or a synonym for the most common topic. A claim of hegemonic influence requires evidence that an articulation has travelled across actors or arenas, stabilised categories, shaped institutional practice, excluded alternatives, or entered binding decisions. Frequency and centrality can be indicators, but they must be interpreted alongside temporality, institutional position, uptake, contestation, and policy effects.

### 3.2 Computational discourse analysis

LaclauGPT is a computational political science pipeline for collecting and analysing multimodal social media data. It was developed by the first author for three research projects conducted by the Helsinki Hub on Emotions, Populism and Polarisation: CO3, which examined the social contract; ENDURE, which studied the post-pandemic world; and PLEDGE, which investigated grievance politics. These projects received funding from the European Union and the Research Council of Finland.

An earlier version of LaclauGPT was used to collect and analyse TikTok and Instagram data concerning the 2024 European Parliament elections. Data collection ran from 1 May until election day on 9 June 2024 and employed the usernames of official election candidates, election-related hashtags, and search queries. The resulting dataset covered Bulgaria, Croatia, Finland, France, Germany, Hungary, Portugal, Spain, and Sweden. The source code is publicly available in separate repositories for multimodal data analysis (Toivio, 2025a) and data collection (Toivio, 2025b). Because the collected social media data cannot currently be released owing to data-protection requirements under the General Data Protection Regulation (GDPR), the public repositories instead contain synthetic demonstration data.

It is important to notice that computational social science tools are always used as interpretive tools that form a preanalysis with human researchers providing the final analysis. There is also a human-in-the-loop element in the way LaclauGPT is developed.

LaclauGPT is the LLM-powered version of AC/DT. Multimodal LLMs were needed to convert TikTok and Instagram videos to text data to be analysed; after this LLMs were also used to create a Laclaudian pre-analysis for human researchers to verify and use as a basis of their work. LaclauGPT is used together with older, more established social data science tools.

Recent scholarship has drawn connections between large language models and structuralist theories of language. Kozlowski (2025) describes this approach as computational structuralism, arguing that LLMs provide computational models in which linguistic meaning emerges relationally rather than from isolated symbols. Vromen (2024) similarly describes LLMs as semiotic machines, while Weatherby (2025) interprets contemporary language models through the history of structuralist theories of language. These approaches share an important affinity with Saussure's conception of linguistic value: signs acquire meaning through their relations and differences with other signs rather than through an intrinsic correspondence between individual signs and objects.

This relational conception of meaning provides a useful bridge between LLMs and Laclaudian discourse analysis. Laclau and Mouffe (2001) extend the structuralist insight into a poststructuralist theory in which meanings are relational but never permanently fixed; political discourse consists of attempts to articulate and temporarily stabilise these relations. LLMs need not be understood as validating this theory in order to be useful for its computational operationalisation. Rather, their capacity to represent and process contextual relationships between linguistic elements makes them potentially useful instruments for identifying relational patterns of articulation in large textual datasets.

Nelimarkka (2026) demonstrates an alternative approach to theory-guided LLM analysis by fine-tuning a language model on Marxist texts to create MarxistLLM. This illustrates how an explicit theoretical worldview can be incorporated into an LLM and subsequently influence computational analysis. LaclauGPT takes a different approach. Rather than fine-tuning the underlying model, it uses prompt and context engineering to operationalise concepts derived from Laclaudian discourse theory. One practical reason is the absence of a sufficiently large gold-standard dataset of human-coded Laclaudian discourse analysis suitable for supervised fine-tuning; creating such a dataset would itself require extensive expert annotation and interpretation. This practical choice must not be presented as evidence that prompting is theoretically neutral: prompts instantiate a reading protocol and can force the framework onto weakly fitting material. The workflow therefore requires negative cases, abstention, counter-evidence, and blinded human evaluation.

LaclauGPT therefore does not attempt to train an LLM to become an autonomous Laclaudian discourse analyst. Instead, it uses existing LLMs as theory-guided analytical instruments for the preliminary analysis of large textual datasets. The model identifies candidate discursive structures and provides evidence from the source material, while human researchers remain responsible for validation and final discourse-theoretical interpretation.

Operationally, the pipeline distinguishes three epistemic layers in its output. Measurement-level claims concern what is present in the text: elements, articulations, and affect terms with evidence spans. Interpretation-level claims treat structural patterns — candidate chains of equivalence, nodal-point candidates — as analytical proposals. Theoretical inference remains the human researcher's responsibility, including all corpus-level judgements about empty signifiers, hegemonic articulations and discursive formations. Every model claim is stored with its evidence quote and provenance, so that each downstream inference can be traced back to the data that supports it.

### 3.3 The LaclauGPT workflow

The primary unit of machine-assisted analysis is a **source document**: a post, speech segment, manifesto section, parliamentary intervention, interview turn, podcast segment, or digital-ethnography note. Longer objects must be segmented upstream before analysis; the pipeline preserves stable parent and sequence identifiers when the collector supplies them, but does not yet perform automatic long-document segmentation or reconstruct missing parent context. The versioned export retains platform, author or speaker when lawfully available, timestamp, language, collection query, collector, arena, URL or source identifier, available modalities, parent context identifiers, and declared transformations such as transcription or translation.

The workflow consists of:

1. **Ingestion and source preservation.** Validate that source text exists, assign a stable document identifier, retain raw wording, and record collection and transformation provenance.
2. **Descriptive summary.** Produce a structured account of actors, topics, claims, difficult language, sentiment, grievances, and source context. This stage is descriptive and may not override the source.
3. **Discourse-theoretical coding.** Propose signifiers and their situated roles; articulation, equivalence, difference, and antagonism relations; sociotechnical imaginaries; formation candidates; counter-evidence; and uncertainties. Every item requires a source quote and a confidence estimate.
4. **Resolve-first codebook matching.** Match surface forms to stable identifiers while preserving aliases. New objects remain provisional; similarity is a retrieval aid, not a semantic decision.
5. **Conditional populism diagnosis.** Apply the Formula of Populism only if both Us and Frontier are evidenced. Store elements, affects, quotations, uncertainty, and the reasons for a non-populist result.
6. **Corpus synthesis.** Compare articulations across actors, time, arenas, and languages. Only here can floating-signifier and hegemony claims be evaluated.
7. **Human review and export.** Review proposed objects and relations, correct or reject them, adjudicate disagreements, and export a versioned analytical dataset. Final discourse interpretation remains a human-authored research product.

The current open-source implementation covers stages 1–6: the analysis pipeline (stages 1–5) exports schema-versioned provisional annotations, and a corpus-synthesis module (stage 6) assembles mechanically verified corpus-level evidence — signifier frequencies and role distributions, floating-signifier candidates with their per-document evidence, and articulation-relation frequencies — as descriptive statistics that human researchers adjudicate. The synthesis module deliberately issues no corpus-level theoretical claims: floating, empty, and hegemonic status remain human judgements over the assembled evidence. The codebook review CSV concerns candidate identity and merging; it is not a substitute for independent annotation review. A complete reviewer interface and adjudication workflow are development requirements rather than completed features.

Inference runs through Ollama and is routed by machine tier. CSC Roihu GPU nodes, the project's Laskin workstation, and other sufficiently capable GPU computers run a local open-source Gemma 4 model. Computers below the configured GPU-memory threshold use an Ollama cloud model, while an explicitly configured external `OLLAMA_HOST` uses that remote server without treating the client computer's GPU as the limiting resource. Automatic selection can be overridden in the run configuration. Gemma 4 is the default model family for this project, not an already validated methodological optimum; the validation design therefore compares the primary configuration with at least one alternative model. Protected or personal data must remain on an endpoint approved by the study's data-management plan, so automatic cloud routing must be disabled for such corpora.

A separate Streamlit prototype has been used to inspect analysed data and visualisations, but it is not part of the open-source implementation evaluated here. Consequently, the present workflow's implemented review artifact is the codebook review CSV; claims about a complete reviewer interface are reserved for future work.

These can be augmented with other theoretical and methodological tools, but it will be a question of continuous development. For the earlier version these tools included topic modelling (ManifestoBERTa and Gensim LDA) and Named Entity Recognition (spaCy). On the other hand, use of Social Network Analysis was not possible due to limitations of the collected data.

One of the key issues with the earlier LaclauGPT is multiplication of NER entities, topics and targets of sentiments: in the earlier implementation, entity and topic consolidation remained unreliable despite experiments with contextual memory approaches. The revised workflow therefore resolves every surface form against a persistent codebook of stable identifiers before output, and many of the limitations of the earlier 2025 version can already be fixed with the improved LLM models and related technologies of 2026.

Earlier exploratory development compared temperature settings and motivated a deterministic primary setting of 0.0. Because those exploratory comparisons are not a reported validation dataset for the revised workflow, temperature 0.0 is treated here as a preregistered configuration choice rather than evidence of superior validity. Model and prompt robustness must still be assessed with the protocol in Section 3.6.

The annotation and codebook layers jointly retain the raw surface form, stable codebook identifier, role or relation, source quotation, document identifier, stage, resolved model, prompt versions, run configuration, timestamp, confidence, uncertainty, and review status. The interchange schema also retains the source field supporting each theoretical code, available modalities, declared transformations, and the evidence-bearing Us and Frontier assessments rather than only their resolved identifiers. Every theoretical quotation is mechanically checked against a retained source or declared derived-source field and carries an explicit verification flag. Unmatched evidence is surfaced as an uncertainty and excluded from descriptive corpus synthesis rather than silently trusted. Model-produced entries remain PROVISIONAL regardless of repetition; only an explicit human action can make them CANONICAL, and merges preserve superseded identifiers and aliases. Deterministic settings do not guarantee identical output across model builds, hardware, or serving software: the model name alone is therefore insufficient, and the model digest and serving-stack version remain required additions to a production run manifest.

Local inference is preferred for protected or personal data and for reproducibility. GDPR compliance, however, does not follow from local inference alone; lawful basis, purpose limitation, data minimisation, access control, retention, data-subject rights, and publication risk still require a documented data-management process.

Multimodal inputs can be prepared with dedicated utilities: speech can be transcribed with automatic speech recognition, and selected video frames can be described and processed with OCR. These utilities remain separate from the canonical analysis pipeline, which ingests prepared transcript, OCR, and frame-description columns rather than orchestrating media processing itself. When upstream data declares an ASR, OCR, frame-description, or translation model, the interchange export preserves that declaration and identifies the source field containing each theoretical evidence excerpt. Missing transformation metadata cannot be reconstructed retrospectively. Visual inference must not silently substitute for missing speech or metadata, and text-only sources bypass multimodal preparation. For multilingual comparison the source language should be preserved alongside any translation, and a validation sample should be coded both in the source language and in translation to estimate whether politically charged terms, pronouns, negation, irony, and affect shift across representations.

Earlier exploratory LaclauGPT runs were used to analyse the three texts studied by Oldenburg and Papyshev (2025). The following formulae are retained as motivating illustrations, not as results of the current schema-versioned pipeline: their run manifests, model digests, evidence-bearing JSONL output, and independent human validation have not yet been archived in this repository. They must therefore be rerun before they can enter the empirical analysis. For the accelerationist text (Andreessen, 2023), the exploratory run produced the following restatement of Palonen's formula:

    Populism-like articulation = Us (technology ≡ growth ≡ markets ≡ intelligence ≡
    energy ≡ abundance ≡ agency ≡ excellence ≡ human flourishing)
    [hope, pride, ambition, confidence] + Frontier (stagnation ≡
    deceleration ≡ degrowth ≡ bureaucracy ≡ centralized planning ≡
    socialism ≡ precaution ≡ anti-technology expertise) [resentment,
    anger, fear, contempt]

The Critical AI text (Distributed AI Research Institute, 2022) constructed Us and Frontier quite differently:

    Populism-like articulation = Us (community control ≡ participation ≡
    non-extractive research ≡ epistemic justice ≡ redistribution ≡
    accountability ≡ solidarity) [solidarity, hope] + Frontier (market-driven AI ≡
    technical solutionism ≡ extractive research ≡ tech elites ≡
    exclusionary institutions ≡ deceptive AI hype) [distrust, indignation]

The existential-risk text (Machine Intelligence Research Institute, 2025) received this result:

    Populism-like articulation = Us (human survival ≡ AI safety ≡ alignment ≡
    precaution ≡ international cooperation ≡ democratic/political control ≡
    shutdown capability) [hope, resolve] + Frontier (misaligned ASI ≡
    uncontrolled frontier AI ≡ reckless scaling ≡ inadequate safety ≡
    AI laboratories ≡ technological rivalry) [fear, alarm, distrust]

These compact displays omit the evidence and uncertainty fields required by
the current method. A contemporary rerun must export each Us and Frontier
element with its verbatim excerpt, source field, confidence, nodal/empty
candidate flags, mechanical evidence-verification result, counter-evidence,
and provisional review status. The formula alone is not an auditable research
result.

### 3.4 Research design

The research project will analyse AI discourse across several political and social arenas, using different sources for data collection.

Data collection uses two methods: digital ethnography with human researchers collecting data (using a plugin like Zeeschuimer) and adding their own digital ethnography reports; additionally, data is collected using automatic data collection tools (Toivio, 2025b) based on hashtags, user accounts and search terms.

The first target is the discourse of AI elites, including entrepreneurs, researchers, and intellectuals associated with major AI companies and institutions. This also includes ideological movements associated with elite AI discourse, such as the TESCREAL ideologies identified by Gebru and Torres (2024). Relevant data sources include blogs, discussion forums, podcast interviews, and the social media accounts of AI entrepreneurs, researchers, and intellectuals.

The second target is grassroots mobilisation around and against AI. This includes movements seeking to challenge, restrict, or halt particular forms of AI development. PauseAI, for example, advocates pausing the development of increasingly powerful AI systems until they can be developed safely and democratically (PauseAI, 2026). Other forms of mobilisation may emerge around issues such as employment, data centres, surveillance, environmental impacts, and cultural opposition to AI.

The third target is AI discourse within parliamentary and electoral politics. Here, the data would consist of AI-related subsets of larger political datasets, following an approach similar to the EP24 election research discussed above. This would enable analysis of how established political actors articulate AI in relation to issues such as technological development, employment, regulation, security, and democracy. At the European level, the EU Artificial Intelligence Act provides an important example of AI governance already translated into legislation (Regulation (EU) 2024/1689, 2024) — a governance anchor for analysis rather than proof of any one ideology.

The arenas use declared observation periods. Actor lists, queries, hashtags, and inclusion criteria are frozen before primary analysis and versioned when amended. Digital ethnography can add context and discover vocabulary, while automated collection increases scale; researcher fieldnotes are analytically valuable but remain a distinct source type rather than being blended with public posts.

Within each arena, the study reports the sampling frame, platform access constraints, missingness, removals, duplicates, language coverage, and the share of material obtained through account-, hashtag-, query-, or event-based sampling. Platform engagement metrics are not measures of public opinion. Comparison proceeds within documents, within actor trajectories, between competing discourses in one arena, and across arenas over time; this design permits tests of whether a term floats between projects, whether an imaginary travels from elite discourse to legislation, and whether grassroots articulations are incorporated, displaced, or excluded.

### 3.5 Ethics and data protection

The study distinguishes public availability from ethical acceptability. Collection and processing plans specify lawful basis, sensitive-data risks, minimisation, pseudonymisation, retention, access, quotation policy, and the risk that searchable quotations re-identify users. Synthetic demonstration data can document software behaviour but cannot validate performance on naturally occurring political language.

### 3.6 Validation and limitations

There are several limitations to the use of LLMs in ideological research. The key to all of this is human validation. The final discourse analysis is a human product, with LLM analysis used only as a preliminary step.

The problems to be taken into account in the final human analysis step include:

- LLMs are trained using the human-produced data available online: this means they will reproduce the ideological biases of the real world (Lindgren, 2024).
- LLMs have a tendency to hallucinate: this is likely to be an unsolvable problem in LLM technology itself (Xu et al., 2024).
- Theory-guided prompting may lead an LLM to impose the theoretical framework encoded in the prompt on the data, producing apparently convincing interpretations even when the supplied theory does not fit the empirical material well (Wachinger et al., 2025).
- The alignment problem is about the LLM following the intent of human users — in this case, the human researcher writing the prompt. This problem may also be unsolvable (Melo et al., 2025).

Hallucination, bias, the alignment problem and theoretical forcing are most likely unsolvable problems and have to be taken into account in the phase of final human analysis. Human interpretation is also fallible, but human researchers and LLMs exhibit different error profiles. LaclauGPT therefore treats model output as provisional analytical coding rather than authoritative interpretation, and the only solution is to use human judgment in the final analysis step.

Human validation is specified as a protocol rather than invoked in the abstract. A stratified validation sample covers all arenas, languages, source types, predicted formations, low- and high-confidence outputs, and model abstentions. At least two trained human coders independently code the source without seeing the model answer, after which the team compares human–human and model–human agreement at the level of category presence, evidence-span overlap, relation type, Us/Frontier membership, affect, and formation assessment. Nominal categories are reported with percent agreement and an appropriate chance-corrected statistic; span and set-valued outputs require overlap, precision, recall or F1 measures, with low base rates and nested categories reported. Disagreement is not reduced to one score: adjudication notes identify whether errors arose from missing evidence, invented evidence, theoretical forcing, source attribution, irony, translation, entity resolution, or defensible interpretive plurality.

The primary configuration is compared with at least one alternative model and with prompt ablations that remove ideological seed labels. A robustness table reports how often classifications, relations, and evidence spans change. Seeded categories must be tested for priming: if formation assignments collapse when the labels are removed, the analysis may reflect the prompt more than the corpus. Negative controls include non-political AI texts, political texts unrelated to AI, policy disagreements without antagonistic frontiers, and texts that quote an ideology in order to reject it — the expected outcome for these is often abstention.

These limitations also discipline what the method may claim. Because prompting encodes theory, findings operationalise the framework rather than test it: LaclauGPT structures the search for articulations, chains and frontiers; it cannot confirm that a corpus contains a hegemonic formation. Accordingly, corpus-level results in the empirical programme are reported as candidate classifications — nodal-point candidates, empty-signifier candidates — each with its evidence, and each open to competing human classifications. This is the same firewall that separates model measurement from researcher interpretation throughout the design.

## 4. Conclusion

The politics of AI concerns struggles over meaning as well as material systems. Laclaudian discourse theory provides concepts for analysing how actors connect AI to demands, identities, enemies, affects, and futures, while sociotechnical imaginaries foreground the forms of social order enacted by those visions. AI is analysed primarily as a floating signifier subject to hegemonic contestation, while particular articulations may also render it tendentially empty or establish it as a nodal point.

LaclauGPT operationalises part of this work as a human-validated computational workflow. Its legitimate output is not a final ideological map but a set of versioned, source-grounded, provisional coding proposals. The method is strongest when it distinguishes concepts that are easy to collapse: mention from articulation, difference from antagonism, polysemy from emptiness, frequency from hegemony, sentiment from affective investment, and political conflict from populism.

The empirical contribution will depend on a frozen sampling design, comparative corpus-level analysis, and reported validation across the three arenas — AI elites, grassroots mobilisation, and parliamentary and electoral politics. Until those stages are completed, LaclauGPT should be read as a research programme and an implemented pre-analysis pipeline rather than as a validated autonomous method. Entity resolution and prompt versioning are implemented but still require empirical evaluation. The next software requirements are a complete reviewer and adjudication interface, automatic long-document segmentation with recoverable context, a production run manifest containing model digests and serving-stack versions, and optional orchestration of provenance-preserving multimodal preparation.

## 5. References

Andreessen, M. (2023, October 16). *The techno-optimist manifesto*. Andreessen Horowitz.

Bastani, A. (2019). *Fully automated luxury communism*. Verso.

Borwein, S., Magistro, B., Alvarez, E., & Bonikowski, B. (2026). Causal beliefs and the potential for political backlash against AI. *Public Opinion Quarterly*. https://doi.org/10.1093/poq/nfag033

Cugurullo, F. (2025). AIdeology: Unpacking the ideology of artificial intelligence and its spaces. *Antipode*. https://doi.org/10.1111/anti.70065

DeLanda, M. (2016). *Assemblage theory*. Edinburgh University Press.

Distributed AI Research Institute. (2022). *DAIR Research Philosophy, Version 1.0* (28 November 2022). https://dair-institute.org/research-philosophy/

Feyerabend, P. (1975). *Against method: Outline of an anarchistic theory of knowledge*. New Left Books.

Gebru, T., & Torres, É. P. (2024). The TESCREAL bundle: Eugenics and the promise of utopia through artificial general intelligence. *First Monday*, 29(4). https://doi.org/10.5210/fm.v29i4.13636

Grimmer, J., Roberts, M. E., & Stewart, B. M. (2022). *Text as data: A new framework for machine learning and the social sciences*. Princeton University Press.

Haraway, D. J. (1991). A cyborg manifesto: Science, technology, and socialist-feminism in the late twentieth century. In *Simians, cyborgs, and women: The reinvention of nature* (pp. 149–181). Routledge.

Jasanoff, S. (2015). Future imperfect: Science, technology, and the imaginations of modernity. In S. Jasanoff & S.-H. Kim (Eds.), *Dreamscapes of modernity: Sociotechnical imaginaries and the fabrication of power* (pp. 1–33). University of Chicago Press. https://doi.org/10.7208/chicago/9780226276663.001.0001

Jasanoff, S., & Kim, S.-H. (Eds.). (2015). *Dreamscapes of modernity: Sociotechnical imaginaries and the fabrication of power*. University of Chicago Press.

Koljonen, J., Carrilho, K., & Palonen, E. (2025). The struggle over masks on Twitter: An AC/DT approach to Finnish pandemic governance. In E. Kerr, E. Bužinkić, & J. Foley (Eds.), *The organisation of irresponsibility? Reassessing COVID-19 in Europe* (pp. 132–163). Brill. https://doi.org/10.1163/9789004747784_007

Kozlowski, A. C. (2025). Computational structuralism: Toward a formal theory of meaning in the age of digital intelligence. *Theory and Society*. https://doi.org/10.1007/s11186-025-09585-z

Kurzweil, R. (2005). *The singularity is near: When humans transcend biology*. Viking.

Kurzweil, R. (2024). *The singularity is nearer: When we merge with AI*. Viking.

Laclau, E. (1996). *Emancipation(s)*. Verso.

Laclau, E. (2005). *On populist reason*. Verso.

Laclau, E., & Mouffe, C. (2001). *Hegemony and socialist strategy: Towards a radical democratic politics* (2nd ed.). Verso.

Lindgren, S. (2020). *Data theory: Interpretive sociology and computational methods*. Polity.

Lindgren, S. (Ed.). (2023). *Handbook of critical studies of artificial intelligence* (1st ed.). Edward Elgar Publishing. https://doi.org/10.4337/9781803928562

Lindgren, S. (2024). *Critical theory of AI: A field guide for critical theory in the age of artificial intelligence*. Polity.

Machine Intelligence Research Institute. (2025). *The problem*. https://intelligence.org/the-problem/

Melo, G. A., Máximo, M. R. O. A., Soma, N. Y., & Castro, P. A. L. (2025). Machines that halt resolve the undecidability of artificial intelligence alignment. *Scientific Reports*, 15, 15591. https://doi.org/10.1038/s41598-025-99060-2

Nelimarkka, M. (2026). MarxistLLM: Fine-tuning a language model with a Marxist worldview. *Big Data & Society*, 13(2).

Okolo, C. T. (2025). The paradox of AI accelerationism and the promise of public interest AI. *Science*, 390(6768), eaeb5789. https://doi.org/10.1126/science.aeb5789

Oldenburg, N., & Papyshev, G. (2025). The stories we govern by: AI, risk, and the power of imaginaries. *Proceedings of the AAAI/ACM Conference on AI, Ethics, and Society (AIES '25)*. https://doi.org/10.1609/aies.v8i2.36686

Palonen, E. (2025). *The birth and death of liberal democracy in Hungary: The populist logic of polarisation as hegemony*. Helsinki University Press. https://doi.org/10.33134/pro-et-contra-4

PauseAI. (2026, April 5). *PauseAI proposal*. https://pauseai.info/proposal

Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence (Artificial Intelligence Act). (2024). *Official Journal of the European Union*, L, 2024/1689. https://eur-lex.europa.eu/eli/reg/2024/1689/oj

Richter, V., Katzenbach, C., & Schäfer, M. S. (2023). Imaginaries of artificial intelligence. In *Handbook of critical studies of artificial intelligence*. Edward Elgar Publishing. https://doi.org/10.4337/9781803928562.00024

Sanders, B. (2026, August 10). *Sanders calls on tech giants to pause development of out-of-control AI*. United States Senate.

Srnicek, N., & Williams, A. (2015). *Inventing the future: Postcapitalism and a world without work*. Verso.

Toivio, T. (2025a). *LaclauGPT multimodal analysis* [Computer software]. GitHub. https://github.com/TomiToivio/LaclauGPT-Multimodal-Analysis

Toivio, T. (2025b). *LaclauGPT TikTok scraper* [Computer software]. GitHub. https://github.com/TomiToivio/LaclauGPT-TikTok-Scraper

Vromen, E. (2024). Language models as semiotic machines: Reconceptualizing AI language systems through structuralist and post-structuralist theories of language.

Wachinger, J., Bärnighausen, K., Schäfer, L. N., Scott, K., & McMahon, S. A. (2025). Prompts, pearls, imperfections: Comparing ChatGPT and a human researcher in qualitative data analysis. *Qualitative Health Research, 35*(9), 951–966. https://doi.org/10.1177/10497323241244669

Weatherby, L. (2025). *Language machines: Cultural AI and the end of remainder humanism*. University of Minnesota Press.

Xu, Z., Jain, S., & Kankanhalli, M. (2024). Hallucination is inevitable: An innate limitation of large language models. arXiv. https://doi.org/10.48550/arXiv.2401.11817

Yudkowsky, E., & Soares, N. (2025). *If anyone builds it, everyone dies: Why superhuman AI would kill us all*. Little, Brown and Company.

Zhang, M. Y., Wang, S., Wei, Y., & Chen, Z. (2026). When science meets geopolitics: Global AI research network transformation (2000–2025). *Science and Public Policy*. https://doi.org/10.1093/scipol/scag017
