"""Experimental HypotheSAEs bridge for inductive hypothesis generation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ._optional import require


def discover_latent_concepts(
    texts: Sequence[str],
    labels: Sequence[Any],
    embeddings: Any,
    sae: Any,
    **kwargs: Any,
) -> Any:
    """Generate exploratory hypotheses from a trained SAE.

    Returned concepts are candidate patterns only. They must not be promoted to
    ideological formations or Laclaudian roles without independent evidence and
    human/theory-guided interpretation.
    """
    hypothesaes = require("hypothesaes")
    return hypothesaes.generate_hypotheses(
        texts=list(texts),
        labels=list(labels),
        embeddings=embeddings,
        sae=sae,
        **kwargs,
    )
