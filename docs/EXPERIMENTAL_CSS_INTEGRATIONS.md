# Experimental computational social science integrations

Status: **experimental, opt-in, disabled by default**

This layer provides small lazy adapters for external computational social science
and discourse-analysis packages. It is intentionally separate from the canonical
LaclauGPT pipeline.

Install all experimental backends in an isolated research environment with:

```bash
pip install -e ".[research-experimental]"
```

Importing `laclaugpt.experimental` does not import any of the optional packages.
They are loaded only when an experimental helper is called.

## Included backends

| Backend | Experimental use | Important limitation |
| --- | --- | --- |
| `pycorpdiff` | keyness, corpus comparison, semantic/temporal change | semantic drift is not evidence by itself that a signifier is floating |
| `scattertext` | comparative term/signifier-space visualisation | lexical association/distinctiveness is not Laclaudian articulation |
| `convokit` | thread and conversation structures | conversational structure is descriptive evidence, not a political-theory conclusion |
| `hypothesaes` | inductive latent-concept/hypothesis discovery | latent SAE concepts are not ideological formations |
| `textnets` | document-term/network exploration | centrality or community membership is not a nodal point or hegemony measure |
| `edsl` | explicit multi-model questions/annotation experiments | model agreement is not validation or ground truth |

`textnets` is GPL-3.0-only. It remains an optional third-party dependency and is
not imported, vendored, or required by the LaclauGPT base package.

The current project extra excludes ConvoKit on Python 3.13 because its published
support metadata currently covers Python 3.10-3.12. Capability detection will
therefore report it unavailable on unsupported environments.

## Minimal synthetic examples

Capability detection:

```python
from laclaugpt.experimental import available_integrations

print(available_integrations())
```

Comparative corpus work with native `pycorpdiff` corpus objects:

```python
from laclaugpt.experimental import compare_keyness, track_signifier

keyness = compare_keyness(corpus_a, corpus_b, min_count=3)
trajectory = track_signifier(corpus_a, "safety", freq="M")
```

Scattertext signifier-space prototype:

```python
import pandas as pd
from laclaugpt.experimental import build_scattertext_corpus, signifier_space_html

frame = pd.DataFrame(
    {
        "text": ["AI means progress", "AI threatens workers", "faster AI now", "protect labour"],
        "category": ["optimist", "critical", "optimist", "critical"],
    }
)
corpus = build_scattertext_corpus(frame)
html = signifier_space_html(
    corpus,
    category="optimist",
    category_name="optimist",
    not_category_name="critical",
)
```

Thread preparation for ConvoKit:

```python
from laclaugpt.experimental import build_conversation_corpus

conversation = build_conversation_corpus(
    [
        {"id": "1", "speaker": "alice", "text": "AI is progress", "conversation_id": "thread"},
        {
            "id": "2",
            "speaker": "bob",
            "text": "Progress for whom?",
            "conversation_id": "thread",
            "reply_to": "1",
        },
    ]
)
```

Text-network candidate generation:

```python
import pandas as pd
from laclaugpt.experimental import build_text_network

documents = pd.Series(
    ["AI safety and regulation", "AI innovation and growth"],
    index=["document-a", "document-b"],
)
network = build_text_network(documents)
```

HypotheSAEs requires embeddings and a trained SAE supplied by the researcher:

```python
from laclaugpt.experimental import discover_latent_concepts

hypotheses = discover_latent_concepts(
    texts=texts,
    labels=labels,
    embeddings=embeddings,
    sae=trained_sae,
    cache_name="synthetic-pilot",
)
```

EDSL preparation is side-effect free; execution remains explicit:

```python
from laclaugpt.experimental import prepare_model_comparison

question, models = prepare_model_comparison(
    "Which claims and evidence spans are present in this synthetic passage?",
    ["model-a", "model-b"],
)
# No request has been made. The researcher must explicitly construct/run the EDSL job.
```

## Epistemic boundary

These utilities may generate **candidates for investigation**. They do not
operationalise Laclau, Mouffe or Palonen automatically.

In particular:

- semantic drift **does not equal** a floating signifier;
- network centrality **does not equal** a nodal point;
- latent SAE concepts **do not equal** ideological formations;
- term association **does not equal** articulation;
- cross-model agreement **does not equal** validity.

Any theoretical claim must still be tied back to inspectable source evidence,
uncertainty, comparative corpus interpretation, and human review.

## Runtime boundary

Nothing in `laclaugpt.experimental` is enabled from:

- AI26 collection;
- collector configuration;
- analysis workers;
- the canonical/default pipeline;
- Streamlit dashboard startup;
- cron/systemd/runtime jobs;
- existing project or arena profiles.

Experimental utilities become active only when a researcher imports and calls
them explicitly.
