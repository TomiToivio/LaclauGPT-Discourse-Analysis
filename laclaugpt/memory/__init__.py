"""Canonical public Context Memory API.

New code should import memory and entity-resolution primitives from this module::

    from laclaugpt.memory import Memory, MemoryRef, ContextBuilder

The persistent SQLite codebook/resolution implementation currently lives in the
compatibility package :mod:`laclaugpt_memory`.  Repository-aware context
orchestration lives in :mod:`laclaugpt.memory.context`.  This facade is the
stable public boundary between those layers so callers do not need to choose an
implementation generation.
"""
from __future__ import annotations

# Persistent codebook / entity resolution.  Keep this import one-way:
# laclaugpt_memory does not import laclaugpt.memory, which avoids a cycle while
# allowing old callers to continue importing the implementation package.
from laclaugpt_memory import (
    KIND_PREFIX,
    KINDS,
    NER_TYPES,
    STATES,
    Candidate,
    Memory,
    MemoryRef,
    Resolution as MemoryResolution,
    default_memory_dir,
    resolve_candidates,
)

# Repository/context orchestration for the canonical package model.
from .context import (
    CanonicalRegistry,
    ConceptResolver,
    ContextBuilder,
    ContextBundle,
    EntityResolver,
    MemoryTrustModel,
    Resolution as ContextResolution,
    TopicResolver,
)

# ``Resolution`` historically meant the repository-oriented resolver result in
# this namespace. Preserve that name while giving both resolution types explicit
# names for new code.
Resolution = ContextResolution
PersistentMemory = Memory

__all__ = [
    "Memory",
    "PersistentMemory",
    "MemoryRef",
    "Candidate",
    "MemoryResolution",
    "resolve_candidates",
    "default_memory_dir",
    "KINDS",
    "STATES",
    "KIND_PREFIX",
    "NER_TYPES",
    "CanonicalRegistry",
    "ContextBuilder",
    "ContextBundle",
    "Resolution",
    "ContextResolution",
    "EntityResolver",
    "TopicResolver",
    "ConceptResolver",
    "MemoryTrustModel",
]
