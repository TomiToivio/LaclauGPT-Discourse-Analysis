# -*- coding: utf-8 -*-
"""Legacy compatibility shim for pre-package memory imports.

Old code may still do::

    from memory import ContextMemory, resolve_candidates

New code MUST use the canonical facade instead::

    from laclaugpt.memory import Memory, MemoryRef, resolve_candidates

This shim is retained for the current paper-pipeline compatibility window. It
contains no independent memory implementation and may be removed after legacy
root-level callers have migrated.
"""
from __future__ import annotations

import warnings

warnings.warn(
    "root memory.py is a legacy compatibility shim; use laclaugpt.memory",
    FutureWarning,
    stacklevel=2,
)

from laclaugpt.memory import (  # noqa: E402,F401
    KIND_PREFIX,
    KINDS,
    STATES,
    Memory as ContextMemory,
    MemoryRef,
    resolve_candidates,
)

__deprecated_since__ = "2.0"
__replacement__ = "laclaugpt.memory"

__all__ = [
    "ContextMemory",
    "MemoryRef",
    "resolve_candidates",
    "KINDS",
    "STATES",
    "KIND_PREFIX",
]
