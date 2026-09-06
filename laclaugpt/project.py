"""Project facade: one graph API regardless of persistence backend."""
from __future__ import annotations

from pathlib import Path

from laclaugpt.backends import Repositories, create_repositories
from laclaugpt.model import (Actor, AnalyticRelation, Articulation, Concept,
                             DiscursiveRelation, Entity, ImaginaryRelation,
                             SociotechnicalImaginary, SourceItem)


class Project:
    def __init__(self, repositories: Repositories, config=None):
        self.repositories = repositories
        self.config = config

    @classmethod
    def open(cls, project: str, machine: str, root: str | Path = ".",
             execution: str = "cli", overrides=None):
        from laclaugpt.config import compose_config
        config = compose_config(project, machine, execution, overrides)
        return cls(create_repositories(config, root), config)

    def add(self, item):
        if isinstance(item, SourceItem):
            return self.repositories.source.put_source(item)
        kind = type(item).__name__
        result = self.repositories.analysis.put(kind, item)
        if isinstance(item, Actor):
            self.repositories.graph.add_node(item.actor_id, label=item.canonical_name, kind="actor")
        elif isinstance(item, Concept):
            self.repositories.graph.add_node(item.concept_id, label=item.canonical_label, kind="concept")
        elif isinstance(item, Entity):
            self.repositories.graph.add_node(item.entity_id, label=item.canonical_name, kind="entity")
        elif isinstance(item, SociotechnicalImaginary):
            self.repositories.graph.add_node(item.imaginary_id, label=item.label,
                kind="sociotechnical_imaginary", evidence_ids=item.evidence_ids,
                review_status=item.review_status)
        elif isinstance(item, ImaginaryRelation):
            self.repositories.graph.add_edge(item.source_id, item.imaginary_id,
                relation_type=item.relation_type, theoretical=True,
                evidence_ids=item.evidence_ids, review_status=item.review_status)
        elif isinstance(item, Articulation):
            self.repositories.graph.add_edge(item.source_concept_id, item.target_concept_id,
                relation_type=item.relation_type, theoretical=True,
                evidence_ids=item.evidence_ids, review_status=item.review_status)
        elif isinstance(item, DiscursiveRelation):
            self.repositories.graph.add_edge(item.source_concept_id, item.target_concept_id,
                relation_type=item.relation_type, theoretical=True,
                evidence_ids=item.evidence_ids, review_status=item.review_status)
        elif isinstance(item, AnalyticRelation):
            self.repositories.graph.add_edge(item.source_id, item.target_id,
                relation_type=item.relation_type, theoretical=False, score=item.score)
        return result

    def get_graph(self, **filters):
        return self.repositories.graph.graph(**filters)

    def context_builder(self, registry, max_items: int = 20):
        from laclaugpt.memory import ContextBuilder
        analysis = (self.config or {}).get("analysis", {})
        enabled = {name for name, active in analysis.items() if active}
        return ContextBuilder(self.repositories, registry, max_items=max_items,
                              project_id=(self.config or {}).get("project"),
                              enabled_modules=enabled)
