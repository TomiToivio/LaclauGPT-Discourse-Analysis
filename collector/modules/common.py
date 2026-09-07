"""Shared helpers for the platform parsing modules.

The platform modules are Python ports of the Zeeschuimer capture/map_item
logic (see modules/README attribution headers). The JS helpers used by the
upstream auto-generated 4CAT sync blocks (py_get, MissingMappedField) are
reimplemented here so ported logic stays line-comparable with upstream.
"""
from __future__ import annotations

from typing import Any


class MissingMappedField:
    """Marks a field the upstream parser could not extract.

    Mirrors 4CAT's MissingMappedField sentinel: comparisons against real
    values are False, and str() yields the fallback so exports keep a
    stable shape even when a platform omits a field.
    """

    __slots__ = ("value",)

    def __init__(self, value: Any = "") -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"MissingMappedField({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, MissingMappedField):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(("missing", str(self.value)))


def py_get(obj: Any, path: str, default: Any = None) -> Any:
    """Upstream-style deep getter: py_get(tweet, "legacy.full_text", "").

    Dotted path lookup that never raises. Returns `default` when any
    segment is missing or the container is not a mapping.
    """
    if not isinstance(path, str):
        return default
    cur: Any = obj
    for segment in path.split("."):
        if isinstance(cur, MissingMappedField):
            return default
        if not isinstance(cur, dict) or segment not in cur:
            return default
        cur = cur[segment]
    return cur


def strip_tags(html: str) -> str:
    """Upstream strip_tags: remove <...> fragments from source strings."""
    import re

    return re.sub(r"<[^>]*>", "", html or "")