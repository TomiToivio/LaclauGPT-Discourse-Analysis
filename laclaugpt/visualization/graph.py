"""Dashboard adapter for canonical discourse-graph projections."""
from __future__ import annotations

from typing import Iterable

from laclaugpt.graph import PROJECTIONS, build_discourse_graph, project_graph
from laclaugpt_interchange import DocumentAnnotation


DASHBOARD_PROJECTIONS = (
    "actor_signifier",
    "signifier_field",
    "formation_map",
    "populism",
    "temporal",
    "evidence_claim",
)


def graph_projection_data(
    annotations: Iterable[DocumentAnnotation], projection: str
) -> dict:
    """Return JSON-ready graph data for the dashboard without a parallel schema."""
    if projection not in DASHBOARD_PROJECTIONS:
        raise ValueError(f"unsupported dashboard graph projection: {projection}")
    graph = build_discourse_graph(list(annotations))
    data = project_graph(graph, projection).to_dict()
    node_ids = {node["id"] for node in data["nodes"]}
    # Relation claims preserve their evidence_id directly. A visualization must
    # never create an implicit node merely because an edge-reference exists.
    data["edges"] = [
        edge for edge in data["edges"]
        if edge["source"] in node_ids and edge["target"] in node_ids
    ]
    return data


def graph_projection_options(*, laclau: bool, palonen: bool, temporal: bool) -> list[str]:
    """Expose only projections whose analysis families are enabled."""
    options: list[str] = []
    if laclau:
        options.extend(["actor_signifier", "signifier_field", "formation_map", "evidence_claim"])
    if palonen:
        options.append("populism")
    if temporal:
        options.append("temporal")
    return [name for name in options if name in PROJECTIONS]
