# LaclauGPT Python architecture

Status: **accepted incremental target architecture**  
Issue: #145  
Scope: maintained public Python code

## Decision

LaclauGPT will converge on **one canonical Python namespace: `laclaugpt`**.

We are **not** doing a flag-day move to `src/` now. The repository already contains a substantial maintained `laclaugpt/` package alongside compatibility modules, collectors, adapters, runtime scripts, and historical entry points. Moving all files at once would mix package cleanup with behavioral change and make regressions difficult to attribute.

A future `src/laclaugpt/` move remains reasonable after imports have converged. Until then, the package root is `laclaugpt/`, `pyproject.toml` is authoritative, and new maintained Python code belongs under that namespace.

## Seven subsystem map

A contributor should map code to these concepts before adding a new module.

| Concept | Canonical target | Status |
|---|---|---|
| LaclauGPT Data Collection | `laclaugpt.collection` | CORE |
| LaclauGPT Data Storage | `laclaugpt.storage` | CORE |
| LaclauGPT Data Analysis | `laclaugpt.analysis` | CORE |
| LaclauGPT Data Visualization | `laclaugpt.visualization` | CORE |
| LaclauGPT Research Assistant | `laclaugpt.assistant` | OPTIONAL |
| LaclauGPT Simulation Laboratory | `laclaugpt.simulation` | OPTIONAL / EXPERIMENTAL |
| LaclauGPT Experimental Laboratory | `laclaugpt.experimental` | EXPERIMENTAL |

Some of these target packages are migration destinations rather than claims that every directory exists today. Existing code must move incrementally and with compatibility shims where external users or artifacts require them.

## Shared foundations

Cross-subsystem definitions belong in small foundation modules, not in a feature subsystem merely because that subsystem used them first.

Preferred responsibilities:

- `laclaugpt.contracts`: serializable, versioned interchange/domain contracts and Protocols;
- `laclaugpt.config`: typed configuration and composition;
- `laclaugpt.cli`: thin command orchestration;
- shared domain objects: no database, browser, Streamlit, Ollama, network, or machine-specific behavior.

A domain object such as an annotation or source record must not know how it is stored, rendered, collected, or modeled.

## Dependency direction

The stable direction is:

```text
contracts / domain / config
        ^
        |
collection   storage   analysis   visualization
        ^        ^        ^           ^
        |        |        |           |
        +---- assistant / simulation / experimental ----+
```

The diagram means foundations are depended on by subsystems. It does **not** mean core subsystems should freely depend on one another's private modules.

Rules:

1. Core code MUST NOT import optional labs (`assistant`, `simulation`, `experimental`).
2. Collection MUST NOT import visualization.
3. Storage MUST NOT import visualization, Streamlit, browser capture, or model runtime internals.
4. Analysis MUST NOT import collector/private collection implementation modules. It consumes source/interchange contracts.
5. Visualization consumes public storage/analysis contracts or serialized artifacts, not pipeline internals.
6. Optional labs may depend on public core APIs.
7. No core subsystem may require an optional lab merely to import.
8. Cross-subsystem calls should use public functions/classes/Protocols, not another subsystem's `_private` implementation.

`tests/architecture/test_dependency_boundaries.py` is the first executable regression guard for these rules. Extend it as migration makes boundaries more precise.

## Canonical public API direction

The following boundaries should remain small and typed. Concrete names may evolve, but responsibilities should not blur.

### Collection

Input: source configuration / researcher action.  
Output: a versioned source/interchange record.

Collection performs acquisition and source-specific parsing. It does not perform Laclaudian analysis or UI rendering.

### Storage

Input/output: domain/interchange records and artifact references.

Storage owns persistence implementations. Contracts do not know which persistence engine is used.

### Analysis

Input: versioned source/interchange records plus explicit configuration/context.  
Output: versioned evidence-linked analysis artifacts.

Analysis owns research transformations and model orchestration, but should isolate pure transformations from I/O and model calls.

### Visualization

Input: public analysis/storage artifacts or typed read interfaces.  
Output: researcher-facing views and exports.

Importing visualization code should not initialize models or collectors.

### Research Assistant

Researcher-directed tools only. Human-in-the-loop boundaries must be explicit. Assistant code is a consumer of core APIs, never a prerequisite of them.

### Simulation Laboratory

Mesa/Concordia or related simulations consume explicit inputs and emit explicit artifacts. Simulation assumptions do not silently become canonical empirical-analysis semantics.

### Experimental Laboratory

Baselines, graph/SNA/RAG trials, notebooks, speculative visualizations, and prototypes live here until promoted.

## Experiment promotion gate

An experimental component graduates only when it has:

1. a clear research/engineering purpose;
2. a defined input/output contract;
3. targeted tests using synthetic/public-safe fixtures;
4. documentation;
5. an acceptable dependency footprint;
6. explicit provenance and failure behavior;
7. a justified destination in Collection, Storage, Analysis, or Visualization.

Promotion means moving or extracting the maintained implementation. Core must not import back into `experimental`.

## Current architecture inventory and migration map

The repository currently contains three generations of Python structure:

### Canonical / maintained direction

- `laclaugpt/`: canonical namespace;
- `laclaugpt/analysis/`: current analysis package;
- `laclaugpt/visualization/`: visualization package and launcher;
- `laclaugpt/config.py`: current typed/configuration convergence point;
- `laclaugpt/cli.py`: canonical command entry point;
- other `laclaugpt/*` packages: retained where they expose maintained behavior.

### Compatibility / migration sources

- root `pipeline.py`, `llm.py`, `run_config.py`, `projects.py`, `memory.py`, `seed_codebook.py`, `laclaugpt_processor.py`;
- top-level `collector/`;
- top-level `*_adapter/` packages;
- root/runtime operational scripts such as `ai26_runtime/`.

These are **not templates for new namespaces**. Existing imports may remain until migrated safely, but new reusable code should be implemented under `laclaugpt` and compatibility modules should delegate inward rather than acquire new business logic.

### Historical / project-operational material

Private project configuration, datasets, machine paths, credentials, collection targets, and generated artifacts stay outside generic package code. See `docs/LEGACY_CURATION.md` for legacy-recovery rules.

## Namespace migration sequence

1. Keep current public behavior stable.
2. Add/strengthen public contracts under `laclaugpt`.
3. For one subsystem at a time, move reusable implementation behind the canonical API.
4. Convert old module imports into thin compatibility shims where compatibility is required.
5. Mark compatibility modules deprecated in documentation before deletion.
6. Update tests/imports incrementally.
7. Remove a legacy namespace only after repository consumers no longer depend on it.
8. Evaluate `src/` layout after namespace convergence, not before.

No migration may silently change research semantics or versioned artifact fields.

## Configuration rules

Configuration is data, not ambient state.

- `pyproject.toml` is authoritative for packaging and dependency declarations.
- Secrets and machine-specific values come from environment/runtime configuration.
- Generic modules must not hard-code CSC/local absolute paths.
- Importing a module must not create directories, connect to services, probe Ollama, read private configuration, or start network activity.
- Machine/profile detection must not silently alter research semantics.
- Factories and explicit entry points are preferred for expensive infrastructure.

## Optional dependency plan

Dependency groups should converge on the seven subsystem boundaries. Existing groups may remain as compatibility names during migration.

Target user-facing groups:

- `collection`: browser/feed/source acquisition dependencies;
- `storage`: optional database/object-store implementations;
- `analysis`: model/NLP analysis dependencies;
- `visualization`: Streamlit/Plotly and rendering dependencies;
- `assistant`: researcher-agent tooling;
- `simulation`: Mesa/Concordia-related tooling;
- `experiments`: research baselines/prototypes;
- `all`: union for development/full installations.

Do not move a package into base dependencies merely because one optional subsystem uses it. Conversely, do not remove an existing base dependency until import and packaging tests demonstrate compatibility.

## CLI rule

`laclaugpt` entry points are adapters. CLI functions parse arguments, construct configuration/dependencies, call package APIs, render status/errors, and exit. Research algorithms, storage implementation, scraping logic, and model prompting do not belong in argument handlers.

## Filesystem and identifiers

- Prefer `pathlib.Path` for local filesystem boundaries.
- A local path, S3 key, URL, document ID, source ID, and research entity ID are distinct types/concepts.
- Machine-specific absolute paths are runtime configuration, never canonical research identifiers.

## Typing and errors

Prioritize type hints on contracts, configuration, storage APIs, pipeline stage boundaries, CLI-facing functions, and optional plug-in interfaces.

Subsystem boundaries should expose meaningful exceptions where callers can respond differently, e.g. configuration, collection/source, storage, schema/validation, model/runtime, optional dependency, and recoverable per-document analysis errors.

Do not catch broad `Exception` merely to make a pipeline appear successful. Per-document recovery is allowed when the failure is recorded with provenance and processing continues intentionally.

## Test architecture

Use these conceptual layers:

- `tests/unit/`: pure transformations/domain behavior;
- `tests/contracts/`: schema and adapter contracts;
- `tests/integration/`: synthetic end-to-end composition;
- `tests/architecture/`: import/dependency rules and package invariants;
- CLI smoke tests;
- existing subsystem-specific suites during migration.

Default CI must not require real scraping, private data, credentials, GPUs, MongoDB, cloud services, or a running Ollama server.

## Public data contracts

Versioned artifacts must change deliberately:

- bump schema/version intentionally;
- preserve provenance;
- provide compatibility readers/upgraders where necessary;
- test representative old public artifacts;
- never silently discard fields while translating between generations.

## Contributor placement rule

Before adding code, answer: **Which of the seven subsystems owns this responsibility?**

If none does, it is probably a shared contract/config concern or an experiment. If several do, define the contract at the boundary rather than creating a new cross-cutting implementation namespace.

The desired end state is intentionally ordinary: one package, explicit contracts, thin adapters, boring dependency direction, and a fenced playground where experiments can be strange without making core imports strange.
