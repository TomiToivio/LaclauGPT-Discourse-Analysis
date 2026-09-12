"""Experimental Scattertext helpers for comparative signifier exploration."""

from __future__ import annotations

from typing import Any

from ._optional import require


def build_scattertext_corpus(
    frame: Any,
    *,
    text_col: str = "text",
    category_col: str = "category",
) -> Any:
    """Build a Scattertext corpus from a pandas-like frame using whitespace parsing."""
    st = require("scattertext")
    parsed_col = "__laclaugpt_scattertext_parse"
    prepared = frame.copy()
    prepared[parsed_col] = prepared[text_col].astype(str).map(st.whitespace_nlp_with_sentences)
    return st.CorpusFromParsedDocuments(
        prepared,
        category_col=category_col,
        parsed_col=parsed_col,
    ).build()


def signifier_space_html(
    corpus: Any,
    *,
    category: str,
    category_name: str | None = None,
    not_category_name: str | None = None,
    **kwargs: Any,
) -> str:
    """Render an exploratory term/signifier comparison as standalone HTML."""
    st = require("scattertext")
    return st.produce_scattertext_explorer(
        corpus,
        category=category,
        category_name=category_name or category,
        not_category_name=not_category_name or f"not {category}",
        **kwargs,
    )
