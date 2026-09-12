"""Lazy capability detection for optional computational-social-science integrations."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType


class OptionalDependencyError(ImportError):
    """Raised when an explicitly requested experimental backend is unavailable."""


@dataclass(frozen=True)
class IntegrationSpec:
    key: str
    distribution: str
    module: str
    purpose: str
    epistemic_limit: str
    python_note: str = ""


INTEGRATIONS: dict[str, IntegrationSpec] = {
    "pycorpdiff": IntegrationSpec(
        key="pycorpdiff",
        distribution="pycorpdiff",
        module="pycorpdiff",
        purpose="comparative corpora, keyness, semantic shift and temporal drift",
        epistemic_limit="semantic or temporal drift is evidence for investigation, not a floating-signifier verdict",
    ),
    "scattertext": IntegrationSpec(
        key="scattertext",
        distribution="scattertext",
        module="scattertext",
        purpose="comparative term/signifier-space visualisation",
        epistemic_limit="term association or distinctiveness is not Laclaudian articulation",
    ),
    "convokit": IntegrationSpec(
        key="convokit",
        distribution="convokit",
        module="convokit",
        purpose="conversation- and thread-level analysis",
        epistemic_limit="conversational structure is descriptive evidence, not a theory-level political claim",
        python_note="The project extra currently installs ConvoKit only on Python <3.13.",
    ),
    "hypothesaes": IntegrationSpec(
        key="hypothesaes",
        distribution="hypothesaes",
        module="hypothesaes",
        purpose="exploratory latent concept and hypothesis discovery",
        epistemic_limit="latent SAE concepts are candidate patterns, not ideological formations",
    ),
    "textnets": IntegrationSpec(
        key="textnets",
        distribution="textnets",
        module="textnets",
        purpose="document-term and semantic network exploration",
        epistemic_limit="network centrality is not a nodal-point, hegemonic, or signifier-role judgement",
        python_note="textnets is GPL-3.0-only and is never a base dependency.",
    ),
    "edsl": IntegrationSpec(
        key="edsl",
        distribution="edsl",
        module="edsl",
        purpose="reproducible multi-model questions and annotation experiments",
        epistemic_limit="model agreement is a robustness signal, not validation or ground truth",
    ),
}


def integration_spec(name: str) -> IntegrationSpec:
    """Return metadata for a known experimental integration."""
    try:
        return INTEGRATIONS[name]
    except KeyError as exc:
        known = ", ".join(sorted(INTEGRATIONS))
        raise KeyError(f"Unknown experimental integration {name!r}; expected one of: {known}") from exc


def is_available(name: str) -> bool:
    """Return whether an optional backend can be imported without importing it."""
    spec = integration_spec(name)
    try:
        return find_spec(spec.module) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def available_integrations() -> dict[str, bool]:
    """Return capability flags without importing optional third-party packages."""
    return {name: is_available(name) for name in INTEGRATIONS}


def require(name: str) -> ModuleType:
    """Import an optional backend only when an experimental function is called."""
    spec = integration_spec(name)
    if not is_available(name):
        message = (
            f"Experimental integration {name!r} requires optional package "
            f"{spec.distribution!r}. Install the project extra with "
            "`pip install -e '.[research-experimental]'` or install the package "
            "directly in an isolated research environment."
        )
        if spec.python_note:
            message += f" {spec.python_note}"
        raise OptionalDependencyError(message)
    return import_module(spec.module)
