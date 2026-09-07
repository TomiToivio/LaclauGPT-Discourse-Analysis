# `laclaugpt.memory`: canonical Context Memory API

New code should import Context Memory and entity-resolution functionality from
this package:

```python
from laclaugpt.memory import Memory, MemoryRef, ContextBuilder
```

The facade combines two deliberately separate internal layers:

1. `laclaugpt_memory/` provides the persistent SQLite codebook, stable IDs,
   aliases, temporal relations, provenance and resolution loop used by the paper
   pipeline.
2. `laclaugpt/memory/context.py` provides repository-aware context assembly,
   trust presentation and in-memory canonical registry helpers over
   `laclaugpt.model` objects.

They are not competing memory databases. Persistence answers “what canonical
object did this mention resolve to and why?” Context orchestration answers “what
bounded, trustworthy context should this analysis call see?”

## Public names

The facade exports `Memory`, `MemoryRef`, `MemoryResolution`, `resolve_candidates`,
`NER_TYPES`, `CanonicalRegistry`, `EntityResolver`, `TopicResolver`,
`ConceptResolver`, `ContextBuilder`, `ContextBundle` and `MemoryTrustModel`.

`Resolution` remains an alias for the repository-oriented `ContextResolution`
for compatibility with the original `laclaugpt.memory` API; persistent resolver
results are explicitly named `MemoryResolution` at this facade.

## Compatibility

Direct `laclaugpt_memory` imports continue to work while the root paper pipeline
and external scripts migrate. Root `memory.py` is a legacy shim and points here.
No new feature should require callers to choose between these paths.
