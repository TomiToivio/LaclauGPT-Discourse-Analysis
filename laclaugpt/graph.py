"""Canonical discourse-graph projections over LaclauGPT interchange output.

The graph is a projection layer over existing canonical/interchange objects, not
an alternative ontology. Nodes retain canonical stable IDs whenever the source
annotation supplies them. Interpretive edges retain evidence, confidence,
provenance and review metadata so graph views remain auditable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.etree.ElementTree import Element, SubElement, tostring

from laclaugpt_interchange import DocumentAnnotation


GRAPH_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source: str
    target: str
    relation: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscourseGraph:
    """Deterministic, storage-neutral graph projection."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: dict[str, GraphEdge] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: GraphNode) -> None:
        existing = self.nodes.get(node.node_id)
        if existing is None:
            self.nodes[node.node_id] = node
            return
        if existing.node_type != node.node_type or existing.label != node.label:
            raise ValueError(f"conflicting graph node identity: {node.node_id}")
        merged = {**existing.properties, **node.properties}
        self.nodes[node.node_id] = GraphNode(
            existing.node_id, existing.node_type, existing.label, merged
        )

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges[edge.edge_id] = edge

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "metadata": _jsonable(self.metadata),
            "nodes": [
                {
                    "id": node.node_id,
                    "type": node.node_type,
                    "label": node.label,
                    **_jsonable(node.properties),
                }
                for node in sorted(self.nodes.values(), key=lambda item: item.node_id)
            ],
            "edges": [
                {
                    "id": edge.edge_id,
                    "source": edge.source,
                    "target": edge.target,
                    "relation": edge.relation,
                    **_jsonable(edge.properties),
                }
                for edge in sorted(self.edges.values(), key=lambda item: item.edge_id)
            ],
        }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _slug_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


def _edge_id(source: str, relation: str, target: str, *context: str) -> str:
    return _slug_id("edge", source, relation, target, *context)


def _annotation_context(annotation: DocumentAnnotation) -> dict[str, Any]:
    provenance = annotation.collection_provenance or {}
    return {
        "document_id": annotation.document_id,
        "project": provenance.get("project", ""),
        "arena": provenance.get("arena_id", ""),
        "analysis_profile": provenance.get("analysis_profile", ""),
        "run_id": annotation.run_id,
        "timestamp": annotation.source_timestamp or annotation.created_at,
        "review_status": annotation.review_status,
        "model": annotation.model,
        "model_digest": annotation.model_digest,
        "prompt_versions": annotation.prompt_versions,
    }


def _evidence_node(graph: DiscourseGraph, annotation: DocumentAnnotation,
                   text: str, source: str = "") -> str | None:
    quote = (text or "").strip()
    if not quote:
        return None
    node_id = _slug_id("evidence", annotation.document_id, source, quote)
    graph.add_node(GraphNode(
        node_id=node_id,
        node_type="evidence",
        label=quote[:160],
        properties={
            **_annotation_context(annotation),
            "exact_text": quote,
            "evidence_source": source,
        },
    ))
    return node_id


def _ref_node(graph: DiscourseGraph, ref, *, default_type: str = "signifier") -> str:
    node_id = str(ref.obj_id or _slug_id(default_type, ref.kind, ref.label, ref.raw))
    graph.add_node(GraphNode(
        node_id=node_id,
        node_type=str(ref.kind or default_type),
        label=str(ref.label or ref.raw or node_id),
        properties={"raw": str(ref.raw or "")},
    ))
    return node_id


def _author_node(graph: DiscourseGraph, annotation: DocumentAnnotation) -> str | None:
    author = (annotation.source_author or "").strip()
    if not author:
        return None
    node_id = _slug_id("actor", author)
    graph.add_node(GraphNode(node_id, "actor", author, {}))
    return node_id


def build_discourse_graph(
    annotations: Sequence[DocumentAnnotation] | Iterable[DocumentAnnotation],
    *,
    project: str | None = None,
    arena: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> DiscourseGraph:
    """Build the canonical graph projection from reviewed interchange records.

    Filters are applied before graph construction. They do not mutate source
    annotations. The resulting graph intentionally stores evidence-bearing
    interpretive claims alongside descriptive document/actor links.
    """
    graph = DiscourseGraph(metadata={
        "projection": "canonical",
        "project": project or "",
        "arena": arena or "",
        "start": start or "",
        "end": end or "",
    })
    for annotation in annotations:
        context = _annotation_context(annotation)
        if project and context["project"] != project:
            continue
        if arena and context["arena"] != arena:
            continue
        timestamp = str(context.get("timestamp") or "")
        if start and timestamp and timestamp < start:
            continue
        if end and timestamp and timestamp > end:
            continue
        _add_annotation(graph, annotation)
    return graph


def _add_annotation(graph: DiscourseGraph, annotation: DocumentAnnotation) -> None:
    context = _annotation_context(annotation)
    doc_id = f"document:{annotation.document_id}"
    graph.add_node(GraphNode(
        node_id=doc_id,
        node_type="document",
        label=annotation.document_id,
        properties={
            **context,
            "platform": annotation.source_platform,
            "country": annotation.source_country,
            "language": annotation.language,
            "source_url": annotation.source_url,
            "summary": annotation.summary,
            "discourse_applicable": annotation.discourse_applicable,
            "relevance": annotation.relevance,
        },
    ))

    actor_id = _author_node(graph, annotation)
    if actor_id:
        graph.add_edge(GraphEdge(
            _edge_id(actor_id, "AUTHORS", doc_id, annotation.document_id),
            actor_id, doc_id, "AUTHORS", context,
        ))

    for ref in annotation.signifiers:
        signifier_id = _ref_node(graph, ref)
        graph.add_edge(GraphEdge(
            _edge_id(doc_id, "MENTIONS_SIGNIFIER", signifier_id),
            doc_id, signifier_id, "MENTIONS_SIGNIFIER", context,
        ))
        if actor_id:
            graph.add_edge(GraphEdge(
                _edge_id(actor_id, "ARTICULATES", signifier_id, annotation.document_id),
                actor_id, signifier_id, "ARTICULATES", context,
            ))

    for articulation in annotation.articulations:
        source_id = _ref_node(graph, articulation.signifier)
        evidence_id = _evidence_node(
            graph, annotation, articulation.evidence, articulation.evidence_source
        )
        targets = articulation.related_to or []
        for target in targets:
            target_id = _ref_node(graph, target)
            relation = _normalize_relation(articulation.relation)
            props = {
                **context,
                "confidence": articulation.confidence,
                "claim_status": articulation.claim_status,
                "rationale": articulation.rationale,
                "evidence_verified": articulation.evidence_verified,
                "evidence_id": evidence_id or "",
            }
            edge = GraphEdge(
                _edge_id(source_id, relation, target_id, annotation.document_id,
                         articulation.evidence),
                source_id, target_id, relation, props,
            )
            graph.add_edge(edge)
            if evidence_id:
                graph.add_edge(GraphEdge(
                    _edge_id(edge.edge_id, "SUPPORTED_BY", evidence_id),
                    edge.edge_id, evidence_id, "SUPPORTED_BY",
                    {**context, "edge_reference": True},
                ))

    for index, role in enumerate(annotation.signifier_roles):
        signifier_id = _ref_node(graph, role.signifier)
        role_id = _slug_id(
            "role", annotation.document_id, signifier_id, role.role,
            str(index), role.evidence,
        )
        evidence_id = _evidence_node(graph, annotation, role.evidence, role.evidence_source)
        graph.add_node(GraphNode(
            role_id, "discursive_role_assignment", role.role,
            {
                **context,
                "role": role.role,
                "confidence": role.confidence,
                "needs_corpus_validation": role.needs_corpus_validation,
                "evidence_verified": role.evidence_verified,
                "rationale": role.rationale,
                "evidence_id": evidence_id or "",
            },
        ))
        graph.add_edge(GraphEdge(
            _edge_id(signifier_id, "HAS_DISCURSIVE_ROLE", role_id),
            signifier_id, role_id, "HAS_DISCURSIVE_ROLE", context,
        ))
        if evidence_id:
            graph.add_edge(GraphEdge(
                _edge_id(role_id, "SUPPORTED_BY", evidence_id),
                role_id, evidence_id, "SUPPORTED_BY", context,
            ))

    for index, discourse in enumerate(annotation.discourses):
        if not discourse.label:
            continue
        discourse_id = _slug_id("discourse", discourse.label)
        graph.add_node(GraphNode(
            discourse_id, "discourse", discourse.label,
            {**context, "confidence": discourse.confidence},
        ))
        graph.add_edge(GraphEdge(
            _edge_id(doc_id, "CANDIDATE_IN", discourse_id, str(index)),
            doc_id, discourse_id, "CANDIDATE_IN", context,
        ))
        evidence_id = _evidence_node(graph, annotation, discourse.evidence, "discourse")
        if evidence_id:
            graph.add_edge(GraphEdge(
                _edge_id(discourse_id, "SUPPORTED_BY", evidence_id, annotation.document_id),
                discourse_id, evidence_id, "SUPPORTED_BY", context,
            ))
        for ref in discourse.elements:
            element_id = _ref_node(graph, ref)
            graph.add_edge(GraphEdge(
                _edge_id(discourse_id, "ORGANIZES", element_id, annotation.document_id),
                discourse_id, element_id, "ORGANIZES", context,
            ))

    for index, assessment in enumerate(annotation.formation_candidates):
        formation_id = _ref_node(graph, assessment.formation, default_type="formation")
        evidence_id = _evidence_node(
            graph, annotation, assessment.evidence, assessment.evidence_source
        )
        props = {
            **context,
            "confidence": assessment.confidence,
            "supporting_features": assessment.supporting_features,
            "counter_evidence": assessment.counter_evidence,
            "evidence_verified": assessment.evidence_verified,
            "evidence_id": evidence_id or "",
        }
        graph.add_edge(GraphEdge(
            _edge_id(doc_id, "CANDIDATE_FORMATION", formation_id, str(index)),
            doc_id, formation_id, "CANDIDATE_FORMATION", props,
        ))
        if evidence_id:
            graph.add_edge(GraphEdge(
                _edge_id(formation_id, "SUPPORTED_BY", evidence_id, annotation.document_id),
                formation_id, evidence_id, "SUPPORTED_BY", context,
            ))

    _add_populism(graph, annotation, doc_id)


def _add_populism(graph: DiscourseGraph, annotation: DocumentAnnotation, doc_id: str) -> None:
    context = _annotation_context(annotation)
    if not (annotation.us or annotation.frontier or annotation.populism_elements):
        return
    us_id = _slug_id("collective_subject", annotation.document_id, "us")
    frontier_id = _slug_id("frontier", annotation.document_id)
    graph.add_node(GraphNode(
        us_id, "collective_subject", "Us",
        {**context, "populist": annotation.populist},
    ))
    graph.add_node(GraphNode(
        frontier_id, "frontier", "Frontier",
        {**context, "populist": annotation.populist,
         "non_populist_reason": annotation.non_populist_reason},
    ))
    graph.add_edge(GraphEdge(
        _edge_id(doc_id, "CONSTRUCTS", us_id), doc_id, us_id, "CONSTRUCTS", context
    ))
    graph.add_edge(GraphEdge(
        _edge_id(doc_id, "CONSTRUCTS", frontier_id),
        doc_id, frontier_id, "CONSTRUCTS", context
    ))
    graph.add_edge(GraphEdge(
        _edge_id(us_id, "ANTAGONISTIC_FRONTIER", frontier_id),
        us_id, frontier_id, "ANTAGONISTIC_FRONTIER", context,
    ))

    for ref in annotation.us:
        ref_id = _ref_node(graph, ref)
        graph.add_edge(GraphEdge(
            _edge_id(ref_id, "MEMBER_OF_US", us_id, annotation.document_id),
            ref_id, us_id, "MEMBER_OF_US", context,
        ))
    for ref in annotation.frontier:
        ref_id = _ref_node(graph, ref)
        graph.add_edge(GraphEdge(
            _edge_id(frontier_id, "FRONTIER_AGAINST", ref_id, annotation.document_id),
            frontier_id, ref_id, "FRONTIER_AGAINST", context,
        ))

    for index, element in enumerate(annotation.populism_elements):
        ref_id = _ref_node(graph, element.element)
        target = us_id if element.side == "us" else frontier_id
        relation = "MEMBER_OF_US" if element.side == "us" else "FRONTIER_AGAINST"
        evidence_id = _evidence_node(
            graph, annotation, element.evidence, element.evidence_source
        )
        graph.add_edge(GraphEdge(
            _edge_id(ref_id if element.side == "us" else target, relation,
                     target if element.side == "us" else ref_id,
                     annotation.document_id, str(index)),
            ref_id if element.side == "us" else target,
            target if element.side == "us" else ref_id,
            relation,
            {
                **context,
                "confidence": element.confidence,
                "claim_status": element.claim_status,
                "affect": element.affect,
                "evidence_verified": element.evidence_verified,
                "evidence_id": evidence_id or "",
                "nodal_candidate": element.nodal_candidate,
                "empty_candidate": element.empty_candidate,
            },
        ))

    for index, affect in enumerate(annotation.affects):
        target_id = _ref_node(graph, affect.target)
        affect_id = _slug_id(
            "affect", annotation.document_id, affect.affect, target_id, str(index)
        )
        evidence_id = _evidence_node(graph, annotation, affect.evidence, affect.evidence_source)
        graph.add_node(GraphNode(
            affect_id, "affect", affect.affect,
            {**context, "side": affect.side, "polarity": affect.polarity,
             "confidence": affect.confidence, "evidence_id": evidence_id or ""},
        ))
        graph.add_edge(GraphEdge(
            _edge_id(target_id, "INVESTED_BY", affect_id),
            target_id, affect_id, "INVESTED_BY", context,
        ))
        if evidence_id:
            graph.add_edge(GraphEdge(
                _edge_id(affect_id, "SUPPORTED_BY", evidence_id),
                affect_id, evidence_id, "SUPPORTED_BY", context,
            ))


def _normalize_relation(relation: str) -> str:
    value = (relation or "articulates").strip().lower()
    aliases = {
        "articulates": "ARTICULATES",
        "articulation": "ARTICULATES",
        "equivalence": "EQUIVALENT_TO",
        "equivalent_to": "EQUIVALENT_TO",
        "difference": "DIFFERENTIATED_FROM",
        "differentiated_from": "DIFFERENTIATED_FROM",
        "antagonism": "ANTAGONISTIC_TO",
        "antagonistic_to": "ANTAGONISTIC_TO",
        "frontier_of": "ANTAGONISTIC_TO",
        "supports": "SUPPORTS",
        "opposes": "OPPOSES",
    }
    return aliases.get(value, value.upper().replace(" ", "_"))


PROJECTIONS = {
    "canonical",
    "actor_signifier",
    "signifier_field",
    "formation_map",
    "populism",
    "temporal",
    "evidence_claim",
}


def project_graph(graph: DiscourseGraph, projection: str) -> DiscourseGraph:
    """Return a deterministic named projection over the canonical graph."""
    if projection not in PROJECTIONS:
        raise ValueError(f"unknown discourse graph projection: {projection}")
    if projection in {"canonical", "temporal"}:
        result = _copy_graph(graph)
        result.metadata["projection"] = projection
        return result

    allowed_nodes: set[str] = set()
    allowed_relations: set[str]
    if projection == "actor_signifier":
        allowed_types = {"actor", "signifier", "concept", "target"}
        allowed_relations = {"ARTICULATES"}
    elif projection == "signifier_field":
        allowed_types = {
            "signifier", "concept", "target", "discursive_role_assignment",
            "discourse", "evidence",
        }
        allowed_relations = {
            "ARTICULATES", "EQUIVALENT_TO", "DIFFERENTIATED_FROM",
            "ANTAGONISTIC_TO", "HAS_DISCURSIVE_ROLE", "SUPPORTED_BY", "ORGANIZES",
        }
    elif projection == "formation_map":
        allowed_types = {"formation", "document", "discourse", "signifier", "concept", "evidence"}
        allowed_relations = {"CANDIDATE_FORMATION", "CANDIDATE_IN", "ORGANIZES", "SUPPORTED_BY"}
    elif projection == "populism":
        allowed_types = {"collective_subject", "frontier", "signifier", "target", "concept", "affect", "evidence"}
        allowed_relations = {
            "MEMBER_OF_US", "FRONTIER_AGAINST", "ANTAGONISTIC_FRONTIER",
            "INVESTED_BY", "SUPPORTED_BY",
        }
    else:  # evidence_claim
        allowed_types = {
            "document", "evidence", "discursive_role_assignment", "discourse",
            "formation", "signifier", "concept", "target", "affect",
        }
        allowed_relations = {"SUPPORTED_BY", "HAS_DISCURSIVE_ROLE", "CANDIDATE_FORMATION", "CANDIDATE_IN"}

    for node_id, node in graph.nodes.items():
        if node.node_type in allowed_types:
            allowed_nodes.add(node_id)
    result = DiscourseGraph(metadata={**graph.metadata, "projection": projection})
    for node_id in sorted(allowed_nodes):
        result.add_node(graph.nodes[node_id])
    for edge in graph.edges.values():
        if edge.relation not in allowed_relations:
            continue
        # SUPPORTED_BY can originate from an edge-reference pseudo source.
        source_ok = edge.source in allowed_nodes or bool(edge.properties.get("edge_reference"))
        if source_ok and edge.target in allowed_nodes:
            result.add_edge(edge)
    return result


def _copy_graph(graph: DiscourseGraph) -> DiscourseGraph:
    return DiscourseGraph(
        nodes=dict(graph.nodes), edges=dict(graph.edges), metadata=dict(graph.metadata)
    )


def write_graph_json(graph: DiscourseGraph, path: str | Path) -> Path:
    destination = Path(path)
    destination.write_text(
        json.dumps(graph.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


def write_graphml(graph: DiscourseGraph, path: str | Path) -> Path:
    """Write a deterministic GraphML subset readable by NetworkX/Gephi/visone."""
    destination = Path(path)
    root = Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
    xml_graph = SubElement(root, "graph", id="LaclauGPT", edgedefault="directed")
    for node in sorted(graph.nodes.values(), key=lambda item: item.node_id):
        xml_node = SubElement(xml_graph, "node", id=node.node_id)
        _xml_data(xml_node, "type", node.node_type)
        _xml_data(xml_node, "label", node.label)
        for key, value in sorted(node.properties.items()):
            _xml_data(xml_node, key, value)
    for edge in sorted(graph.edges.values(), key=lambda item: item.edge_id):
        xml_edge = SubElement(
            xml_graph, "edge", id=edge.edge_id, source=edge.source, target=edge.target
        )
        _xml_data(xml_edge, "relation", edge.relation)
        for key, value in sorted(edge.properties.items()):
            _xml_data(xml_edge, key, value)
    destination.write_text(
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
        + tostring(root, encoding="unicode") + "\n",
        encoding="utf-8",
    )
    return destination


def write_gexf(graph: DiscourseGraph, path: str | Path) -> Path:
    """Write deterministic GEXF for Gephi/Cytoscape-style workflows."""
    destination = Path(path)
    root = Element("gexf", xmlns="http://gexf.net/1.3", version="1.3")
    xml_graph = SubElement(root, "graph", mode="static", defaultedgetype="directed")
    nodes = SubElement(xml_graph, "nodes")
    for node in sorted(graph.nodes.values(), key=lambda item: item.node_id):
        SubElement(nodes, "node", id=node.node_id, label=node.label)
    edges = SubElement(xml_graph, "edges")
    for index, edge in enumerate(sorted(graph.edges.values(), key=lambda item: item.edge_id)):
        SubElement(
            edges, "edge", id=str(index), source=edge.source, target=edge.target,
            label=edge.relation,
        )
    destination.write_text(
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
        + tostring(root, encoding="unicode") + "\n",
        encoding="utf-8",
    )
    return destination


def _xml_data(parent: Element, key: str, value: Any) -> None:
    item = SubElement(parent, "data", key=str(key))
    if isinstance(value, (dict, list, tuple, set)):
        item.text = json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True)
    elif value is None:
        item.text = ""
    else:
        item.text = str(_jsonable(value))


def write_graph_bundle(
    annotations: Sequence[DocumentAnnotation], output_base: str | Path,
    *, project: str | None = None, arena: str | None = None,
) -> dict[str, str]:
    """Write canonical JSON, GraphML and GEXF sidecars for one analysis run."""
    graph = build_discourse_graph(annotations, project=project, arena=arena)
    base = Path(output_base)
    stem = base.with_suffix("") if base.suffix else base
    paths = {
        "json": write_graph_json(graph, f"{stem}.graph.json"),
        "graphml": write_graphml(graph, f"{stem}.graph.graphml"),
        "gexf": write_gexf(graph, f"{stem}.graph.gexf"),
    }
    return {key: str(value) for key, value in paths.items()}
