"""Opt-in experimental computational-social-science utilities.

Nothing in this package is imported by the canonical pipeline, collectors,
AI26 runtime, dashboard, project profiles, or schedulers. Importing this package
itself does not import any optional third-party backend.
"""

from ._optional import (
    INTEGRATIONS,
    OptionalDependencyError,
    available_integrations,
    integration_spec,
    is_available,
)
from .conversation import build_conversation_corpus
from .corpus import compare_keyness, semantic_shift, track_signifier
from .hypotheses import discover_latent_concepts
from .models import prepare_model_comparison
from .networks import build_text_network
from .signifiers import build_scattertext_corpus, signifier_space_html

__all__ = [
    "INTEGRATIONS",
    "OptionalDependencyError",
    "available_integrations",
    "integration_spec",
    "is_available",
    "compare_keyness",
    "semantic_shift",
    "track_signifier",
    "build_scattertext_corpus",
    "signifier_space_html",
    "build_conversation_corpus",
    "discover_latent_concepts",
    "build_text_network",
    "prepare_model_comparison",
]
