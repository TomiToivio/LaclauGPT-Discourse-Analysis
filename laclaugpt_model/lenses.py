# -*- coding: utf-8 -*-
"""Multi-lens projection layer: one canonical store, many theories.

Design (Tomi's architecture note, 2026-09-04):
- the canonical model (laclaugpt_model) stays theory-light:
  Document/Actor/Concept/Annotation/Statement/Relation/AnalysisRun
- every theory is a PROJECTION over it — never a subclass:
    SNA / discourse network   (lens_sna)
    ANT actant networks       (lens_ant)
    ValueFlows political economy (lens_valueflows)
    Assemblage (ANA) + Multitude emergence (lens_assemblage)
- the paper documents one justified analysis path (Laclau);
  the software allows many. experimental/ analyses live outside the
  validated method and say so.

Rhizome is a design principle here, not an algorithm: no privileged
root, heterogeneous node types, multiple edge types, cross-layer links.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import networkx as nx

from laclaugpt_model import Actor, Concept, Document, Relation, Statement

# ── ANT lens ─────────────────────────────────────────────────────────
# Heterogeneous actants in one graph. The canonical types map to
# neutral super-types; an entity can carry SEVERAL types at once
# (multi-valued typing): gpt-5 is software, model, artifact AND actant.

ANT_TYPES: dict[str, list[str]] = {
    # canonical kind -> default actant supertypes
    "document": ["artifact", "text", "actant"],
    "actor": ["agent", "actant"],
    "concept": ["object_of_discourse", "actant"],
    "statement": ["event", "enunciation", "actant"],
    "relation": ["mediation"],
}


def ant_actant_graph(documents: Iterable[Document],
                     actors: Iterable[Actor],
                     concepts: Iterable[Concept],
                     statements: Iterable[Statement],
                     relations: Iterable[Relation],
                     extra_types: dict[str, list[str]] | None = None,
                     ) -> nx.Graph:
    """ANT: material heterogeneity in one graph. Humans, LLMs, datasets,
    GPUs, corporations, laws, prompts, papers, APIs, concepts as
    actants; edges are mediations with the canonical relation types."""
    g = nx.Graph()
    extra = extra_types or {}

    def add(node_id: str, label: str, types: list[str]) -> None:
        if node_id in g:
            return
        g.add_node(node_id, label=label, types=types)

    for d in documents:
        add(d.id, f"doc:{(d.text or d.id)[:40]}",
            ANT_TYPES["document"] + extra.get(d.id, []))
    for a in actors:
        add(a.id, a.name, ANT_TYPES["actor"] + extra.get(a.id, []))
    for c in concepts:
        add(c.id, c.label, ANT_TYPES["concept"] + extra.get(c.id, []))
    for s in statements:
        add(s.id, f"stmt:{s.concept_id}",
            ANT_TYPES["statement"] + extra.get(s.id, []))
    for r in relations:
        if r.source_id in g and r.target_id in g:
            g.add_edge(r.source_id, r.target_id,
                       type=r.type, weight=r.weight,
                       evidence=len(r.evidence_ids))
    # statement -> actor (performs) and statement -> concept (about)
    for s in statements:
        if s.actor_id and s.actor_id in g:
            g.add_edge(s.actor_id, s.id, type="performs", weight=1)
        g.add_edge(s.id, s.concept_id, type="articulates", weight=1)
    return g


# ── ValueFlows lens ──────────────────────────────────────────────────
# REA: Resources – Events – Agents. Political economy projection of the
# AI assemblage: OpenAI owns data center, data center consumes
# electricity, worker performs labour, labour contributes to model
# training, training produces model.
# Observation layer (EconomicEvent) is what happened; intents/commitments
# would live on the plan layer (not needed for discourse data yet).

VF_RELATION_MAP: dict[str, str] = {
    # canonical relation type -> ValueFlows action verb
    "associated_with": "participates",
    "derived_from": "produces",       # dataset -> model
    "uses_signifier": "consumes",
    "member_of": "participates",
    "mentions": "involves",
}


def vf_economic_graph(entities: dict[str, dict],
                      relations: Iterable[Relation],
                      role_types: dict[str, str] | None = None,
                      ) -> nx.DiGraph:
    """ValueFlows projection: Agent —[action]→ Resource/Process chains.

    entities: {id: {label, ...}} for all canonical objects worth mapping
    role_types: {id: 'agent'|'resource'|'process'} — the analyst's
    political-economy reading (OpenAI=agent, datacenter=resource,
    model training=process...). Default heuristic: actors→agent,
    documents/concepts→resource.
    """
    g = nx.DiGraph()
    roles = role_types or {}
    for eid, meta in entities.items():
        role = roles.get(eid, meta.get("vf_role"))
        if not role:
            # heuristic default: actors are agents, text artifacts resources
            role = "agent" if meta.get("kind") == "actor" else "resource"
        g.add_node(eid, label=meta.get("label", eid), vf_role=role)
    for r in relations:
        if r.source_id not in g or r.target_id not in g:
            continue
        action = VF_RELATION_MAP.get(r.type, "associated_with")
        # ValueFlows direction: agent does something to/together with resource
        src = r.source_id
        dst = r.target_id
        if g.nodes[src]["vf_role"] == "resource" and g.nodes[dst]["vf_role"] == "agent":
            src, dst = dst, src
        g.add_edge(src, dst, action=action, weight=r.weight)
    return g


# ── Assemblage / ANA lens ────────────────────────────────────────────
# Assemblage is the ontological assumption, not a separate graph: the
# canonical store IS the heterogeneous assemblage; every lens is a view.
# This module provides the emergent-structure analysis that Hardt/Negri
# Multitude (and movement/coalition/public detection) live in — same
# principle as AnalysisResult for nodal points: emergent structures are
# RESULTS, never raw node types.

def detect_emergent_structures(graph: nx.Graph,
                               resolution: float = 1.0,
                               ) -> list[dict]:
    """Community detection over any lens graph → candidate collectives.
    Labels stay candidate-level (cluster/community/coalition/...);
    interpreting one as 'multitude' is a later analytical step."""
    if graph.number_of_nodes() == 0:
        return []
    comms = nx.community.louvain_communities(graph, resolution=resolution)
    out = []
    for i, comm in enumerate(comms):
        internal = graph.subgraph(comm).number_of_edges()
        out.append({
            "community_id": f"comm_{i}",
            "size": len(comm),
            "internal_edges": internal,
            "density": (2 * internal / (len(comm) * (len(comm) - 1)))
                       if len(comm) > 1 else 0.0,
            "members": sorted(comm),
        })
    out.sort(key=lambda c: -c["size"])
    return out


def classify_collective(size: int, density: float,
                        heterogeneity: float = 0.0) -> str:
    """Emergent label ladder (candidate-level, provisional):
    small tight group → cluster/coalition; large + heterogeneous +
    cooperative → multitude candidate. NOT a raw type."""
    if size < 5:
        return "cluster"
    if density > 0.5:
        return size < 30 and "coalition" or "movement"
    if heterogeneity > 0.6 and size >= 30:
        return "multitude_candidate"
    return "community"