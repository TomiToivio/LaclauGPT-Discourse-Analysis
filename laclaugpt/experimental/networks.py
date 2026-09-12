"""Experimental textnets bridge for document-term network exploration."""

from __future__ import annotations

from typing import Any

from ._optional import require


def build_text_network(
    documents: Any,
    *,
    min_docs: int = 1,
    remove_weak_edges: bool = False,
    **kwargs: Any,
) -> Any:
    """Build a descriptive document-term network with textnets.

    Centrality or community membership is never interpreted here as a nodal point,
    hegemony, ideological formation, or other Laclaudian theoretical judgement.
    """
    tn = require("textnets")
    corpus = tn.Corpus(documents)
    return tn.Textnet(
        corpus.tokenized(),
        min_docs=min_docs,
        remove_weak_edges=remove_weak_edges,
        **kwargs,
    )
