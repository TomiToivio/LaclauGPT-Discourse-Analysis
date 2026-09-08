"""Interoperable exporters for canonical LaclauGPT discourse graphs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

import networkx as nx

from laclaugpt.graph import DiscourseGraph, build_discourse_graph, write_graph_json
from laclaugpt_interchange import DocumentAnnotation


def _scalar(value: Any) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def to_networkx(graph: DiscourseGraph) -> nx.MultiDiGraph:
    """Convert the canonical projection without inventing missing graph nodes."""
    result = nx.MultiDiGraph(
        schema_version="1.0",
        **{str(k): _scalar(v) for k, v in sorted(graph.metadata.items())},
    )
    for node in sorted(graph.nodes.values(), key=lambda item: item.node_id):
        attrs = {
            "node_type": node.node_type,
            "label": node.label,
            **{str(k): _scalar(v) for k, v in sorted(node.properties.items())},
        }
        result.add_node(node.node_id, **attrs)
    for edge in sorted(graph.edges.values(), key=lambda item: item.edge_id):
        # Evidence for articulation edges is also retained as evidence_id on
        # the edge. Older graph snapshots may contain an edge-reference
        # SUPPORTED_BY relation whose source is not a node; do not manufacture
        # a fake domain node during export.
        if edge.source not in result.nodes or edge.target not in result.nodes:
            continue
        attrs = {
            "edge_id": edge.edge_id,
            "relation": edge.relation,
            **{str(k): _scalar(v) for k, v in sorted(edge.properties.items())},
        }
        result.add_edge(edge.source, edge.target, key=edge.edge_id, **attrs)
    return result


def write_graphml(graph: DiscourseGraph, path: str | Path) -> Path:
    destination = Path(path)
    nx.write_graphml(to_networkx(graph), destination, encoding="utf-8", prettyprint=True)
    return destination


def write_gexf(graph: DiscourseGraph, path: str | Path) -> Path:
    destination = Path(path)
    nx.write_gexf(to_networkx(graph), destination, encoding="utf-8", prettyprint=True)
    return destination


def write_graph_bundle(
    annotations: Sequence[DocumentAnnotation], output_base: str | Path,
    *, project: str | None = None, arena: str | None = None,
) -> dict[str, str]:
    graph = build_discourse_graph(annotations, project=project, arena=arena)
    base = Path(output_base)
    stem = base.with_suffix("") if base.suffix else base
    paths = {
        "json": write_graph_json(graph, f"{stem}.graph.json"),
        "graphml": write_graphml(graph, f"{stem}.graph.graphml"),
        "gexf": write_gexf(graph, f"{stem}.graph.gexf"),
    }
    return {key: str(value) for key, value in paths.items()}
