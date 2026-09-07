"""LaclauGPT 2.0 public API.

The package is deliberately backend-independent. Domain objects live in
``laclaugpt.model``. Context Memory is exposed through ``laclaugpt.memory`` and
persistence is selected through runtime profiles.
"""
from __future__ import annotations

from .model import *  # noqa: F401,F403

__version__ = "2.0.0"


def __getattr__(name: str):
    """Lazy-load higher-level helpers without burdening model/memory imports.

    Importing ``laclaugpt.memory`` must not implicitly import optional backend
    dependencies such as NetworkX. ``from laclaugpt import Project`` remains
    compatible and loads the orchestration layer only when requested.
    """
    if name == "Project":
        from .project import Project
        return Project
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
