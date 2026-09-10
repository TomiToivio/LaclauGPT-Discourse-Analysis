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


def _attrs(values: dict[str, Any]) -> dict[str, str | int | float | bool]:
    return {str(k): _scalar(v) for k, v in sorted(values.items())}


def _assertion_node_id(edge_id: str) -> str:
    return f"assertion:{edge_id}"


def _reify_edge_reference(result: nx.MultiDiGraph, graph: DiscourseGraph,
                           edge) -> str | None:
    """Turn an edge-level evidence reference into an explicit assertion node.

    Canonical JSON can reference an evidence node from a semantic edge ID. Plain
    GraphML/GEXF require edge endpoints to be nodes, so exports reify that
    relation as a portable assertion node instead of dropping the evidence link.
    """
    referenced = graph.edges.get(edge.source)
    if referenced is None:
        return None
    assertion_id = _assertion_node_id(referenced.edge_id)
    if assertion_id not in result:
        result.add_node(
            assertion_id,
            node_type="relation_assertion",
            label=referenced.relation,
            asserted_relation_id=referenced.edge_id,
            asserted_relation=referenced.relation,
            **_attrs(referenced.properties),
        )
        if referenced.source in result:
            result.add_edge(
                referenced.source, assertion_id,
                key=f"{referenced.edge_id}:assertion-source",
                edge_id=f"{referenced.edge_id}:assertion-source",
                relation="ASSERTION_SOURCE",
            )
        if referenced.target in result:
            result.add_edge(
                assertion_id, referenced.target,
                key=f"{referenced.edge_id}:assertion-target",
                edge_id=f"{referenced.edge_id}:assertion-target",
                relation="ASSERTION_TARGET",
            )
    return assertion_id


def to_networkx(graph: DiscourseGraph) -> nx.MultiDiGraph:
    """Convert the canonical graph while preserving edge-level evidence.

    GraphML/GEXF cannot use an edge ID as the source endpoint of another edge.
    When canonical JSON contains such a `SUPPORTED_BY` relation, this exporter
    creates a `relation_assertion` node linked to the original relation's source,
    target and evidence. No evidence-bearing relation is silently discarded.
    """
    result = nx.MultiDiGraph(
        schema_version="1.0",
        **{str(k): _scalar(v) for k, v in sorted(graph.metadata.items())},
    )
    for node in sorted(graph.nodes.values(), key=lambda item: item.node_id):
        attrs = {
            "node_type": node.node_type,
            "label": node.label,
            **_attrs(node.properties),
        }
        result.add_node(node.node_id, **attrs)

    for edge in sorted(graph.edges.values(), key=lambda item: item.edge_id):
        source = edge.source
        target = edge.target
        if source not in result and edge.properties.get("edge_reference"):
            source = _reify_edge_reference(result, graph, edge) or source
        if source not in result or target not in result:
            continue
        attrs = {
            "edge_id": edge.edge_id,
            "relation": edge.relation,
            **_attrs(edge.properties),
        }
        result.add_edge(source, target, key=edge.edge_id, **attrs)
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
