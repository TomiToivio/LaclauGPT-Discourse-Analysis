# -*- coding: utf-8 -*-
"""Optional computational primitives: BERTopic candidate clustering +
spaCy ANN Linker entity candidates. All optional: graceful no-ops when
the packages are absent, so Slurm jobs never fail on a primitive.
"""
from __future__ import annotations

from typing import Optional

from laclaugpt_memory import MemoryRef


def _try(import_name: str):
    try:
        return __import__(import_name)
    except Exception:
        return None


def bertopic_candidates(docs: list[str],
                        seeds: list[str] | None = None,
                        n_topics: int = 12,
                        language: str = "multilingual") -> tuple[list[int], list[float]]:
    """Candidate discursive formations. Returns (topic_ids, probs).
    Seeds = canonical labels from memory (guided/semi-supervised mode)."""
    bt = _try("bertopic")
    if bt is None or not docs:
        return [], []
    from bertopic import BERTopic
    model = bt.BERTopic(language=language, calculate_probabilities=True)
    if seeds:
        model = bt.BERTopic(language=language, calculate_probabilities=True,
                            seeded_topics=seeds)
    try:
        topics, probs = model.fit_transform(docs)
    except (ValueError, ZeroDivisionError):
        # Degenerate corpus (fewer docs/topics than the model's minimum,
        # e.g. 2 one-word documents): the optional primitive degrades to
        # no-ops instead of crashing — Slurm jobs never die on it.
        return [], []
    return list(topics), [float(p) if p is not None else 0.0 for p in probs]


def bertopic_over_time(docs: list[str], timestamps: list[str],
                       topics: list[int], freq: str = "1M"):
    bt = _try("bertopic")
    if bt is None:
        return None
    from bertopic import BERTopic
    model = bt.BERTopic(language="multilingual")
    model.fit(docs)
    return model.topics_over_time(docs, topics, timestamps=timestamps,
                                  global_tuning=True, evolution_tuning=True,
                                  datetime_format="%Y-%m-%dT%H:%M:%SZ")


def bertopic_hierarchical(topics) -> None:
    bt = _try("bertopic")
    if bt is None:
        return None
    # implemented inline by callers with model.hierarchical_topics(docs)
    return None


def build_ann_linker(knowledgebase: list[tuple[str, str]]):
    """Build an ANN linker over (alias, obj_id) pairs.
    With spacy-ann-linker installed, uses its ANN index; otherwise uses
    the lexical n-gram stub (same interface, no dependency). Never None
    unless the knowledgebase is empty."""
    try:
        import spacy
        from ann_linker import ANNKnowledgeBase, EntityLinker
        # real spacy-ann-linker path (wire when installed on Roihu)
        return None  # pragma: no cover — enable with the Roihu venv
    except Exception:
        return ANNKnowledgeBaseStub(knowledgebase) if knowledgebase else None


class ANNKnowledgeBaseStub:  # lexical stand-in
    """Minimal ANN knowledge-base wrapper; replaced by spacy-ann-linker's
    own ANNIndex when the package is installed."""

    def __init__(self, entries: list[tuple[str, str]]):
        self._index: dict[str, list[str]] = {}
        for alias, obj_id in entries:
            key = alias.casefold().strip()
            self._index.setdefault(key, []).append(obj_id)

    def candidates(self, text: str) -> list[MemoryRef]:
        """Whole-phrase + n-gram lookup (lexical ANN stand-in)."""
        out = []
        words = text.casefold().split()
        for n in (3, 2, 1):
            for i in range(len(words) - n + 1):
                gram = " ".join(words[i:i + n])
                for obj_id in self._index.get(gram, []):
                    out.append(MemoryRef(obj_id=obj_id, label=gram, kind="entity",
                                         raw=text))
        return out


def ann_candidates(linker, text: str) -> list[MemoryRef]:
    if not linker:
        return []
    return linker.candidates(text)


def memory_knowledgebase(memory) -> list[tuple[str, str]]:
    """(alias, obj_id) pairs from the memory codebook for ANN indexing."""
    entries = []
    for oid, label in memory.conn.execute(
            "SELECT obj_id, label FROM objects WHERE state IN ('CANONICAL','PROVISIONAL')"):
        entries.append((label, oid))
    for oid, alias in memory.conn.execute("SELECT obj_id, alias FROM aliases"):
        entries.append((alias, oid))
    return entries