# -*- coding: utf-8 -*-
"""Compatibility shim: v0 pipeline imports delegate to laclaugpt_memory.

    from memory import ContextMemory, resolve_candidates

New code should use:
    from laclaugpt_memory import Memory, resolve_candidates
"""
from laclaugpt_memory import (Memory as ContextMemory,   # noqa: F401
                              resolve_candidates,        # noqa: F401
                              KINDS, STATES, KIND_PREFIX)  # noqa: F401
