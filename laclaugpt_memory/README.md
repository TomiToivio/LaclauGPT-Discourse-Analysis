# `laclaugpt_memory`: persistent Context Memory implementation

This package contains the SQLite-backed stable-ID codebook and resolution loop
used by the paper pipeline. It remains a supported compatibility and
implementation package, but it is no longer the public import decision that new
code has to make.

For new code, use the single Context Memory facade:

```python
from laclaugpt.memory import Memory, MemoryRef, ContextBuilder
```

`laclaugpt.memory` re-exports the persistent `Memory`, `MemoryRef`, resolution
constants and helpers from this package and also exposes the repository-oriented
`ContextBuilder`/registry layer. This keeps persistence and orchestration
separate internally while presenting one public API.

## Persistent layer responsibilities

- **Stable IDs**: `E001` entities, `T001` topics, `S001` signifiers,
  `C001` sentiment/stance targets, `A001` actors and `F001` formations.
- **Open-world codebook**: canonical/provisional/merged/deprecated/rejected
  states with explicit provenance and human-review controls.
- **Resolution**: extract → retrieve candidates → resolve → update memory.
- **Raw wording preservation**: surface forms remain aliases with provenance.
- **Temporal drift**: period-stamped relations remain in the persistent memory.
- **Decision provenance**: creation, matching, merging and review actions are
  logged rather than silently rewriting analytical history.
- **Compact prompt context**: relevant codebook entries can be retrieved without
  injecting the whole database into an LLM prompt.

## Usage through the public facade

```python
import os
from laclaugpt.memory import Memory

memory = Memory(memory_dir=os.environ.get("LACLAUGPT_MEMORY_DIR"))

resolution = memory.resolve(
    "advanced AI",
    kind="target",
    stage="postprocess",
    video_key="user::video123",
    evidence="quote from transcript",
)

context = memory.context_prompt_block("AI will transform economic growth")
memory.record_analysis("user::video123", "postprocess", payload, evidence)
memory.close()
```

Direct imports such as `from laclaugpt_memory import Memory` continue to work
for the compatibility lifetime of the root paper pipeline and existing external
scripts. New integrations should not add new direct dependencies on this
implementation package.

## Repository-oriented context layer

`laclaugpt/memory/context.py` is not a second persistent memory database. It is
an orchestration layer over canonical `laclaugpt.model` objects and configured
repositories. It provides:

- `CanonicalRegistry` for in-memory/repository-oriented canonical records;
- `EntityResolver`, `TopicResolver` and `ConceptResolver`;
- `ContextBuilder` as a bounded gateway for source, vector and reviewed context;
- `MemoryTrustModel` so prior model proposals are not presented as accepted
  knowledge.

The public facade in `laclaugpt.memory` is the boundary joining these two layers.

## Embeddings

When available, local `sentence-transformers` provides similarity candidates.
Without it, the persistent resolver falls back to exact, alias and fuzzy string
matching. Embedding similarity proposes candidates; it does not turn uncertain
matches into human-approved canonical knowledge.

Environment variables:

- `LACLAUGPT_MEMORY_DIR`: persistent storage location;
- `LACLAUGPT_EMBED_MODEL`: optional embedding-model override.

## Persistent tables

The implementation currently stores `objects`, `aliases`, `alias_meta`,
`embeddings`, `decisions`, `temporal` and `runs` in SQLite.

## Compatibility policy

- **Canonical public import:** `laclaugpt.memory`
- **Persistent implementation package:** `laclaugpt_memory`
- **Legacy root shim:** `memory.py`, retained only for old root-level imports
- Existing SQLite memory databases remain readable; this consolidation changes
  import/API ownership, not the on-disk schema.
