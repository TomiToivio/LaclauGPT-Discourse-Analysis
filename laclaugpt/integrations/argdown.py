"""Argdown's claim/support/attack subset, without theory coercion."""
from __future__ import annotations

import json
import re
from typing import Iterable

from laclaugpt.model import ExternalRelation, Provenance, Statement

_CLAIM = re.compile(r"^\s*\[(?P<title>[^]]+)]\s*:\s*(?P<text>.+)$")
_EDGE = re.compile(r"^\s*(?P<edge>\+>|->)\s*\[(?P<title>[^]]+)]")


def import_argdown(text: str, source_id: str, representation_id: str,
                   provenance_id: str) -> tuple[list[Statement], list[ExternalRelation]]:
    statements: list[Statement] = []
    relations: list[ExternalRelation] = []
    by_title: dict[str, Statement] = {}
    current: Statement | None = None
    for line in text.splitlines():
        if match := _CLAIM.match(line):
            current = Statement(source_id=source_id, representation_id=representation_id,
                                text=match["text"], attribution_type="unclear")
            by_title[match["title"]] = current
            statements.append(current)
        elif current and (match := _EDGE.match(line)):
            target = by_title.get(match["title"])
            if target:
                relations.append(ExternalRelation(
                    source_id=current.statement_id, target_id=target.statement_id,
                    relation_type="support" if match["edge"] == "+>" else "attack",
                    schema="Argdown", metadata={"provenance_id": provenance_id}))
    return statements, relations


def export_argdown(statements: Iterable[Statement],
                   relations: Iterable[ExternalRelation] = ()) -> str:
    statements = list(statements)
    title = {s.statement_id: f"Claim {i}" for i, s in enumerate(statements, 1)}
    lines = [f"[{title[s.statement_id]}]: {s.text}" for s in statements]
    for relation in relations:
        if relation.schema_name.casefold() != "argdown" or relation.relation_type not in {"support", "attack"}:
            continue
        if relation.source_id in title and relation.target_id in title:
            symbol = "+>" if relation.relation_type == "support" else "->"
            lines.append(f"[{title[relation.source_id]}] {symbol} [{title[relation.target_id]}]")
    return "\n".join(lines) + ("\n" if lines else "")


def export_argdown_json(statements: Iterable[Statement],
                        relations: Iterable[ExternalRelation] = ()) -> str:
    return json.dumps({
        "claims": [{"id": s.statement_id, "text": s.text} for s in statements],
        "relations": [r.model_dump(mode="json", by_alias=True) for r in relations
                      if r.schema_name.casefold() == "argdown"],
    }, ensure_ascii=False, indent=2)

