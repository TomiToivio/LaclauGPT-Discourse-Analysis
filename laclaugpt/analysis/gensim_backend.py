"""Gensim backend: classical topic/semantic baselines (LDA, LSI, HDP,
Word2Vec, Doc2Vec). Purpose: methodological comparison and backwards
compatibility — LDA vs BERTopic vs LLM extraction vs LaclauGPT reading.
Not mandatory; per-project config decides which methods run.
"""
from __future__ import annotations

from typing import Any, Iterable

from laclaugpt.analysis import BackendUnavailable, TopicModelResult
from laclaugpt.model import Provenance, Topic, TopicAssignment

_BACKEND = "gensim"


def is_available() -> bool:
    try:
        import gensim  # noqa: F401
        return True
    except ImportError:
        return False


def _version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("gensim")
    except Exception:
        return ""


def _tokenize(text: str) -> list[str]:
    # deterministic tokenizer shared by all gensim methods (no model needed)
    import re
    return re.findall(r"[a-zA-ZäöüåÄÖÜÅß0-9]{2,}", text.casefold())


def _simple_preprocess(documents: list[str]):
    from gensim.utils import simple_preprocess
    return [simple_preprocess(doc, deacc=True, min_len=2) for doc in documents]


def discover(documents: Iterable[str], *, model: str | None = None,
             timestamps: list[str] | None = None,
             provenance: Provenance | None = None) -> TopicModelResult:
    """model selects the gensim method: gensim_lda | gensim_lsi |
    gensim_hdp. Everything lands as Topic + TopicAssignment candidates."""
    if not is_available():
        raise BackendUnavailable("gensim is not installed")
    docs = [d for d in documents if d and d.strip()]
    method = (model or "gensim_lda").casefold()
    provenance_id = provenance.provenance_id if provenance else ""
    result = TopicModelResult(
        method=method, provenance_id=provenance_id,
        model_info={"library": "gensim", "library_version": _version(),
                    "n_documents": len(docs)},
    )
    if not docs:
        return result
    from gensim import corpora
    tokenized = _simple_preprocess(docs)
    dictionary = corpora.Dictionary(tokenized)
    dictionary.filter_extremes(no_below=2, no_above=0.8, keep_n=10000)
    corpus = [dictionary.doc2bow(text) for text in tokenized]
    if not any(corpus):
        return result

    if method == "gensim_lda":
        from gensim.models import LdaModel
        trained = LdaModel(corpus, id2word=dictionary, num_topics=8,
                           random_state=42, passes=5)
    elif method == "gensim_lsi":
        from gensim.models import LsiModel
        trained = LsiModel(corpus, id2word=dictionary, num_topics=8)
    elif method == "gensim_hdp":
        from gensim.models import HdpModel
        trained = HdpModel(corpus, id2word=dictionary)
    else:
        raise ValueError(f"unknown gensim method: {method}")

    for topic_id, terms in trained.show_topics(formatted=False, num_topics=8,
                                               num_words=8):
        keywords = [word for word, _ in terms]
        result.topics.append(Topic(
            topic_id=f"{method}_{topic_id}",
            canonical_label=", ".join(keywords[:4]),
            aliases=keywords,
            description=f"{method} topic {topic_id}: {', '.join(keywords[:5])}",
            metadata={"method": method, "gensim_version": _version(),
                      "provenance_id": provenance_id},
        ))
    for doc_index, bow in enumerate(corpus):
        for topic_id, score in trained.get_document_topics(bow,
                                                           minimum_probability=0.05):
            result.assignments.append(TopicAssignment(
                target_id=f"document_{doc_index}", topic_id=f"{method}_{topic_id}",
                score=float(score), confidence=None,
                provenance_id=provenance_id, review_status="model_proposed"))
    return result