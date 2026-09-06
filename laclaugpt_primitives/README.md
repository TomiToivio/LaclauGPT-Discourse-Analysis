# Computational primitives: BERTopic + spaCy ANN Linker

Candidate generation, NOT truth. LLM + Laclaudian interpretation comes
after. Per Tomi's architecture note (2026-09-04): LaclauGPT's edge is
theory + ontology + memory + orchestration — borrow the best primitives.

## BERTopic — candidate discursive formations

Role: cluster documents into **candidate signifier clusters**; never
label them "discourses" directly. Output feeds the summary/populism
prompts as candidate context and the memory as PROVISIONAL objects.

```python
from laclaugpt_primitives import bertopic_candidates

# guided mode: seed with canonical signifier labels from memory
topics, probs = bertopic_candidates(
    docs,                      # list[str] document texts
    seeds=["ai safety", "economic growth"],  # from memory: S/T labels
    n_topics=12,
    language="multilingual",
)
# topics-over-time for temporal layer:
topics_over_time = bertopic_over_time(docs, timestamps, topics)
# hierarchical merges for consolidation hints:
hier = bertopic_hierarchical(topics)
```

Install on Roihu: `pip install bertopic` (brings umap/hdbscan deps;
GPU-accelerated UMAP optional). Optional, never required — the pipeline
must run without it.

## spaCy ANN Linker — entity resolution assistance

Microsoft's spacy-ann-linker builds an ANN index over a KnowledgeBase
of aliases and proposes entity-linking candidates for spaCy NER spans.
This is exactly the "Sam Altman"/"Altman"/"OpenAI CEO" problem, as a
library.

```python
from laclaugpt_primitives import build_ann_linker, ann_candidates

# one-time per codebook (or incremental): index aliases from memory
kb = memory.knowledgebase()   # [(alias, obj_id), ...]
linker = build_ann_linker(kb)
cands = ann_candidates(linker, "Altman said OpenAI will pause")
# -> [MemoryRef(E002=Sam Altman, score 0.93), ...]
# the resolver then treats these as high-priority candidates
```

Status: adapter slot prepared; enable when spacy + ann-linker are in
the Roihu venv. Resolution order stays:
normalise → alias table → fuzzy → embedding → ANN (when available) →
LLM resolver. ANN inserts before the LLM and after lexical matching.

## Both are OPTIONAL

`laclaugpt_primitives` degrades to no-op (functions return empty
lists) when the packages are missing — the Slurm job never fails
because an optional primitive is absent.