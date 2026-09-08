from __future__ import annotations

from pathlib import Path

import networkx as nx

from laclaugpt.graph import build_discourse_graph, project_graph
from laclaugpt.graph_export import to_networkx, write_gexf, write_graphml
from laclaugpt.visualization.graph import graph_projection_data, graph_projection_options
from laclaugpt_interchange import (
    Affect,
    Articulation,
    DocumentAnnotation,
    FormationAssessment,
    MemoryRef,
    PopulismElementAssessment,
    SignifierRole,
)


def ref(obj_id: str, label: str, kind: str = "signifier") -> MemoryRef:
    return MemoryRef(obj_id=obj_id, label=label, kind=kind, raw=label)


def synthetic_annotation() -> DocumentAnnotation:
    ai = ref("S001", "AI")
    abundance = ref("S002", "abundance")
    workers = ref("S003", "workers")
    elite = ref("S004", "AI corporations")
    formation = ref("F001", "techno-optimism", "formation")
    return DocumentAnnotation(
        document_id="synthetic::1",
        source_author="Synthetic Research Actor",
        source_timestamp="2026-09-01T12:00:00Z",
        source_platform="synthetic",
        collection_provenance={
            "project": "ai26",
            "arena_id": "elites",
            "analysis_profile": "ai26:elites",
        },
        signifiers=[ai, abundance, workers, elite],
        articulations=[
            Articulation(
                signifier=ai,
                related_to=[abundance],
                relation="equivalence",
                evidence="AI will create abundance.",
                evidence_source="synthetic_text",
                evidence_verified=True,
                claim_status="asserted",
                confidence=0.91,
            )
        ],
        signifier_roles=[
            SignifierRole(
                signifier=ai,
                role="nodal_point",
                evidence="AI organizes the proposed future.",
                evidence_source="synthetic_text",
                evidence_verified=True,
                confidence=0.8,
            )
        ],
        formation_candidates=[
            FormationAssessment(
                formation=formation,
                supporting_features=["AI linked to abundance"],
                counter_evidence=["ownership left unspecified"],
                evidence="AI will create abundance.",
                evidence_source="synthetic_text",
                evidence_verified=True,
                confidence=0.7,
            )
        ],
        us=[workers],
        frontier=[elite],
        populist=True,
        populism_elements=[
            PopulismElementAssessment(
                element=workers,
                side="us",
                affect="hope",
                evidence="Workers can share the gains.",
                evidence_source="synthetic_text",
                evidence_verified=True,
                confidence=0.8,
                claim_status="asserted",
            ),
            PopulismElementAssessment(
                element=elite,
                side="frontier",
                affect="resentment",
                evidence="AI corporations monopolize the gains.",
                evidence_source="synthetic_text",
                evidence_verified=True,
                confidence=0.83,
                claim_status="asserted",
            ),
        ],
        affects=[
            Affect(
                target=workers,
                affect="hope",
                side="us",
                evidence="Workers can share the gains.",
                evidence_source="synthetic_text",
                evidence_verified=True,
                confidence=0.8,
            )
        ],
    )


def test_canonical_graph_preserves_stable_ids_and_relations() -> None:
    graph = build_discourse_graph([synthetic_annotation()])
    assert "S001" in graph.nodes
    assert "S002" in graph.nodes
    relations = {edge.relation for edge in graph.edges.values()}
    assert "EQUIVALENT_TO" in relations
    assert "HAS_DISCURSIVE_ROLE" in relations
    assert "ANTAGONISTIC_FRONTIER" in relations
    assert "INVESTED_BY" in relations
    role_nodes = [node for node in graph.nodes.values()
                  if node.node_type == "discursive_role_assignment"]
    assert len(role_nodes) == 1
    assert role_nodes[0].properties["evidence_id"]


def test_named_projections_are_distinct_views_of_same_graph() -> None:
    graph = build_discourse_graph([synthetic_annotation()])
    actor = project_graph(graph, "actor_signifier")
    field = project_graph(graph, "signifier_field")
    populism = project_graph(graph, "populism")
    assert any(node.node_type == "actor" for node in actor.nodes.values())
    assert any(edge.relation == "EQUIVALENT_TO" for edge in field.edges.values())
    assert any(node.node_type == "collective_subject" for node in populism.nodes.values())
    assert any(node.node_type == "frontier" for node in populism.nodes.values())


def test_project_arena_and_time_filters() -> None:
    ann = synthetic_annotation()
    assert build_discourse_graph([ann], project="ai26", arena="elites").nodes
    assert not build_discourse_graph([ann], project="other").nodes
    assert build_discourse_graph([ann], start="2026-08-01", end="2026-09-30").nodes
    assert not build_discourse_graph([ann], start="2026-10-01").nodes


def test_populism_projection_abstains_when_components_absent() -> None:
    ann = DocumentAnnotation(
        document_id="synthetic::abstain",
        collection_provenance={"project": "ai26", "arena_id": "elites"},
        populist=False,
        non_populist_reason="No evidenced collective subject and frontier.",
    )
    graph = project_graph(build_discourse_graph([ann]), "populism")
    assert not any(node.node_type == "collective_subject" for node in graph.nodes.values())
    assert not any(edge.relation == "ANTAGONISTIC_FRONTIER" for edge in graph.edges.values())


def test_networkx_export_reifies_edge_level_evidence() -> None:
    graph = build_discourse_graph([synthetic_annotation()])
    exported = to_networkx(graph)
    assertion_nodes = [
        node_id for node_id, attrs in exported.nodes(data=True)
        if attrs.get("node_type") == "relation_assertion"
    ]
    assert assertion_nodes, "articulation evidence must survive graph export"
    assertion = assertion_nodes[0]
    relations = {
        attrs.get("relation") for _, _, attrs in exported.edges(data=True)
    }
    assert "ASSERTION_SOURCE" in relations
    assert "ASSERTION_TARGET" in relations
    assert "SUPPORTED_BY" in relations
    assert any(target.startswith("evidence:")
               for _, target, attrs in exported.out_edges(assertion, data=True)
               if attrs.get("relation") == "SUPPORTED_BY")


def test_graphml_and_gexf_exports_are_readable(tmp_path: Path) -> None:
    graph = build_discourse_graph([synthetic_annotation()])
    graphml = write_graphml(graph, tmp_path / "graph.graphml")
    gexf = write_gexf(graph, tmp_path / "graph.gexf")
    loaded_graphml = nx.read_graphml(graphml)
    loaded_gexf = nx.read_gexf(gexf)
    assert "S001" in loaded_graphml.nodes
    assert "S001" in loaded_gexf.nodes
    assert any(attrs.get("node_type") == "relation_assertion"
               for _, attrs in loaded_graphml.nodes(data=True))
    assert any(attrs.get("node_type") == "relation_assertion"
               for _, attrs in loaded_gexf.nodes(data=True))
    first = graphml.read_text(encoding="utf-8")
    write_graphml(graph, graphml)
    assert graphml.read_text(encoding="utf-8") == first


def test_dashboard_consumes_canonical_projection_data() -> None:
    data = graph_projection_data([synthetic_annotation()], "signifier_field")
    assert data["metadata"]["projection"] == "signifier_field"
    assert any(node["id"] == "S001" for node in data["nodes"])
    options = graph_projection_options(laclau=True, palonen=True, temporal=True)
    assert "signifier_field" in options
    assert "populism" in options
    assert "temporal" in options
