"""LaclauGPT 2.0 public API.

The package is deliberately backend-independent.  Domain objects live in
``laclaugpt.model`` and persistence is selected through runtime profiles.
"""

from .model import *  # noqa: F401,F403
from .project import Project

__version__ = "2.0.0"

