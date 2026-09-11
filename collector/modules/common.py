"""Small shared helpers for LaclauGPT-native platform parsers."""
from __future__ import annotations

import re
from typing import Any, Iterable, TypeVar

T = TypeVar("T")


def as_string(value: Any) -> str:
    return "" if value is None else str(value)


def first_value(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def unique(values: Iterable[T]) -> list[T]:
    seen: set[T] = set()
    out: list[T] = []
    for value in values:
        if value in (None, "") or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]*>", "", html or "")
