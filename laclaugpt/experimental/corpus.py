"""Experimental comparative-corpus adapters.

These helpers deliberately accept native pycorpdiff corpus objects. They are thin
opt-in bridges, not a second corpus model and not theory-level classifiers.
"""

from __future__ import annotations

from typing import Any

from ._optional import require


def compare_keyness(left_corpus: Any, right_corpus: Any, **kwargs: Any) -> Any:
    """Compare two corpora using pycorpdiff keyness."""
    pcd = require("pycorpdiff")
    return pcd.compare(left_corpus, right_corpus).keyness(**kwargs)


def semantic_shift(
    left_corpus: Any,
    right_corpus: Any,
    term: str,
    **kwargs: Any,
) -> Any:
    """Explore semantic change for ``term``; never infer floating-signifier status."""
    pcd = require("pycorpdiff")
    return pcd.compare(left_corpus, right_corpus).semantic_shift(term, **kwargs)


def track_signifier(corpus: Any, term: str, **kwargs: Any) -> Any:
    """Return pycorpdiff's descriptive trajectory for a term over time."""
    pcd = require("pycorpdiff")
    return pcd.track(corpus, term).over_time(**kwargs)
