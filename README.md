# LaclauGPT

**LaclauGPT: the academic method and minimal reference implementation.**

LaclauGPT is a theory-guided, LLM-assisted discourse-analysis method that
combines Laclau and Mouffe's discourse theory with Emilia Palonen's
Formula of Populism. It proposes candidate discursive interpretations of
textual material — articulations, signifier roles, collective subjects,
antagonistic frontiers, affective investments — and links every proposal
to exact source evidence for human review. It is named as a tribute to
[Ernesto Laclau](https://en.wikipedia.org/wiki/Ernesto_Laclau) and is
developed by [Tomi Toivio](mailto:tomi.toivio@helsinki.fi) at the
University of Helsinki.

## Theoretical framework

- **Laclau & Mouffe**: articulation, discourse, nodal/floating/empty
  signifiers, equivalence, difference, antagonism, collective subjects,
  hegemony — all as *candidate interpretations*, never as facts a model
  produces.
- **Palonen**: Populism = Us^Affects1 + Frontier^Affects2, recorded as an
  interpretive structure (not a numerical score), with explicit support
  for *non-populist* configurations.
- **Methodological core**: traceability, evidence spans, uncertainty,
  provenance, review status, and abstention. Model proposal ≠ accepted
  interpretation.

## What this repository contains

- `paper/PAPER.md` — the academic paper (the method's source of truth).
- `laclaugpt/` — the minimal reference implementation:
  `models.py` (canonical data model), `analysis.py` (the analyzer),
  `prompts.py`, `provenance.py`, `cli.py`.
- `tests/test_core.py` — a small synthetic-text test suite.

Install and analyse one text:

```bash
pip install -e ".[ollama]"
echo "some political text..." > /tmp/text.txt
laclaugpt analyse --file /tmp/text.txt --model gemma3:12b
```

Or as a library with any model provider callable:

```python
from laclaugpt import analyze

def my_model_call(system: str, user: str) -> str:
    ...  # call your LLM endpoint

result = analyze("some political text...", model_call=my_model_call)
print(result.articulations[0].evidence)   # exact quote from the text
```

## What this repository deliberately does NOT contain

This is a **minimal academic reference implementation**, not the complete
research infrastructure. Data collection, research datasets, project
configurations, machine/cluster profiles, databases, context-memory
infrastructure, scheduling, dashboards and production pipelines are
maintained separately. The public core accepts **already-collected
textual or textualized material** (plain text, transcripts, OCR output,
frame descriptions) and demonstrates the method — nothing more.

Heavier analytical stacks (spaCy, BERTopic, Gensim, Transformers,
SentenceTransformers, scikit-learn, statsmodels) are used in the larger
system for preprocessing, topic discovery and statistical validation;
they are intentionally not dependencies of this minimal core.

## Where is the paper?

[`paper/PAPER.md`](paper/PAPER.md) — *LaclauGPT: Ideological contestation
over AI*. The paper defines the method; the code here reflects it.

## License

MIT — see [LICENSE](LICENSE).