# -*- coding: utf-8 -*-
"""EXPERIMENTAL: interim pure-python temporal term-frequency view.

Stands in for pycorpdiff's validated temporal/semantic-shift tooling on
Python <3.11 (pycorpdiff requires >=3.11; see _optional.py). Pure
frequency counting — no semantics, no drift inference. Candidate term
lists for human inspection only; semantic drift ≠ floating signifier.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from ._optional import is_available


def temporal_drift(buckets: dict[str, list[str]]) -> dict[str, dict]:
    """Per-term frequency view across time-ordered text buckets.

    buckets: {"2026-01": [texts...], "2026-02": [...], ...}
    Returns {"<bucket>": {"counts": Counter, "total": int}}. Purely
    descriptive; replace with pycorpdiff.track(...).over_time once the
    runtime meets pycorpdiff's Python requirement.
    """
    out: dict[str, dict] = {}
    for bucket, texts in sorted(buckets.items()):
        counts: Counter = Counter()
        total = 0
        for text in texts:
            for token in str(text).lower().split():
                tok = token.strip(".,;:!?\"'()[]{}")
                if len(tok) >= 4:
                    counts[tok] += 1
                    total += 1
        out[bucket] = {"counts": counts, "total": total}
    return out


def pycorpdiff_available() -> bool:
    """Convenience gate for callers deciding between drift helpers."""
    return is_available("pycorpdiff")