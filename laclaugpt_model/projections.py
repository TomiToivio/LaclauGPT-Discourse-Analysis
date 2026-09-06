# -*- coding: utf-8 -*-
"""Graph projections over the canonical model.

"Store observations and assertions. Generate networks." — projections
are pure functions from statements/relations/documents to NetworkX
graphs. Nothing here mutates the canonical data.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import networkx as nx

from laclaugpt_model import Actor, Concept, Document, Relation, Statement


def actor_concept_graph(statements: Iterable[Statement],
                        actors: dict[str, Actor],
                        concepts: dict[str, Concept],
                        min_agreement: int = 1) -> nx.Graph:
    """DNA-style affiliation graph: Actor —[stance/weight]— Concept."""
    g = nx.Graph()
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for s in statements:
        if s.actor_id and s.concept_id:
            counts[(s.actor_id, s.concept_id, s.stance.value)] += 1
    for (aid, cid, stance), n in counts.items():
        if n < min_agreement:
            continue
        a = actors.get(aid)
        c = concepts.get(cid)
        if a and c:
            g.add_node(aid, label=a.name, kind="actor")
            g.add_node(cid, label=c.label, kind="concept")
            w = g.get_edge_data(aid, cid, {}).get("weight", 0)
            g.add_edge(aid, cid, stance=stance, weight=w + n)
    return g


def actor_congruence_graph(statements: Iterable[Statement],
                           actors: dict[str, Actor],
                           concepts: dict[str, Concept]) -> nx.Graph:
    """DNA congruence network: actors tied by agreeing on the same
    concepts (both support / both oppose)."""
    by_concept: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for s in statements:
        if s.actor_id and s.concept_id:
            sign = 1 if s.stance.value == "support" else (-1 if s.stance.value == "oppose" else 0)
            if sign:
                by_concept[s.concept_id][s.actor_id] += sign
    g = nx.Graph()
    for cid, actor_stances in by_concept.items():
        ids = list(actor_stances)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                same = (actor_stances[a] > 0) == (actor_stances[b] > 0)
                if same:
                    w = g.get_edge_data(a, j := b, {}).get("weight", 0)
                    g.add_edge(a, b, weight=w + 1)
    for nid in g.nodes:
        a = actors.get(nid)
        if a:
            g.nodes[nid]["label"] = a.name
    return g


def signifier_graph(concepts: dict[str, Concept],
                    relations: Iterable[Relation],
                    edge_types: set[str] | None = None) -> nx.Graph:
    """Signifier graph: Concept —[articulates/co_occurs/assoc]— Concept."""
    allowed = edge_types or {"articulates", "co_occurs", "semantically_associated"}
    g = nx.Graph()
    for r in relations:
        if r.type in allowed:
            g.add_edge(r.source_id, r.target_id,
                       type=r.type, weight=r.weight)
    for nid in g.nodes:
        c = concepts.get(nid)
        if c:
            g.nodes[nid]["label"] = c.label
    return g


def social_interaction_graph(documents: Iterable[Document],
                             actors: dict[str, Actor]) -> nx.DiGraph:
    """AS2-flavoured interaction graph: reply/repost/mention edges
    derived from thread structure (parent_id) and authorship."""
    g = nx.DiGraph()
    docs = {d.id: d for d in documents if d.author_id}
    for d in docs.values():
        g.add_node(d.author_id)
    for d in docs.values():
        parent = docs.get(d.parent_id) if d.parent_id else None
        if parent and parent.author_id and parent.author_id != d.author_id:
            g.add_edge(parent.author_id, d.author_id, type="replies_to")
    for nid in g.nodes:
        a = actors.get(nid)
        if a:
            g.nodes[nid]["label"] = a.name
    return g


def temporal_slices(statements: Iterable[Statement],
                    buckets: str = "month") -> dict[str, list[Statement]]:
    """Group statements into time buckets for dynamic graphs (GEXF
    intervals live in the exporter, not here)."""
    out: dict[str, list] = defaultdict(list)
    for s in statements:
        if s.timestamp:
            key = s.timestamp.strftime("%Y-%m")
            out[key].append(s)
    return dict(sorted(out.items()))