# Modular LaclauGPT architecture

Status: **architecture decision / maintained guidance**  
Related: #144, #145, #133, #82, #140, #35, #36

LaclauGPT is one research system with **four stable core capabilities** and **three optional laboratories**. The architecture is logical first: the same boundaries must work on one laptop, in sequential scripts, as separate processes, across multiple machines, and in HPC batch jobs.

## The seven capabilities

### CORE 1. LaclauGPT Data Collection

Owns source/platform adapters, browser-assisted capture where justified, RSS/web/social/document ingestion, checkpoint/resume, deduplication, raw provenance, media references, and normalization into stable source records.

Collection ends at the ingestion contract. It does not perform Laclaudian interpretation.

Current migration surfaces include `collector/` and `laclaugpt.collect`; maintained new APIs should converge under the canonical `laclaugpt` namespace as described in `PYTHON_ARCHITECTURE.md`.

### CORE 2. LaclauGPT Data Storage

Owns durable identifiers, raw/normalized records, analysis artifacts, run/provenance metadata, review state, object references, and storage adapters. Local files/JSONL/SQLite remain valid first-class backends. MongoDB, object storage, graph stores, vector indexes, and other services are optional implementations, not the definition of Storage.

Canonical data is distinguished from derived indexes and caches. A vector index or graph projection may be rebuilt from canonical artifacts.

### CORE 3. LaclauGPT Data Analysis

Owns the canonical discourse-analysis pipeline, optional multimodal preprocessing, codebook-driven interpretation, model routing, local Ollama/HPC execution, configured Context Memory, machine-readable annotations, researcher-readable rendering, and corpus synthesis.

`paper/PAPER.md` and `THEORY.md` remain authoritative for current research semantics. Experimental analyzers cannot silently replace the canonical pipeline.

### CORE 4. LaclauGPT Data Visualization

Owns researcher-facing inspection and review: document drill-down, intermediate-stage inspection, corpus synthesis, temporal/signifier/formation views, review tooling, and export.

Visualization consumes stored outputs. It must be possible to inspect an existing analysis artifact without starting a collector or an LLM runtime.

### OPTIONAL 5. LaclauGPT Research Assistant

Human-in-the-loop agent/tooling layer for monitoring jobs, diagnosing missing fields, preparing reports, suggesting reruns/settings, and invoking bounded operations through public interfaces.

It is a client of the core system. It does not own research semantics and may not bypass human review, private-data boundaries, or canonical configuration.

### EXPERIMENTAL 6. LaclauGPT Simulation Laboratory

Mesa, Concordia, and related social/agent simulation work. Simulation may consume empirical LaclauGPT outputs as parameters, but simulation outputs are synthetic and must never be represented as empirical observations.

Core workflows are unchanged when this laboratory is absent.

### EXPERIMENTAL 7. LaclauGPT Experimental Laboratory

Home for exploratory NLP baselines, lexical comparison, clustering, SNA/network work, graph/RAG alternatives, prototype pipelines, notebooks, and speculative visualizations.

Every experiment should state its purpose, maturity, inputs/outputs, dependencies, relation to the canonical pipeline, and promotion status. Promotion to core requires tests, documentation, stable contracts, provenance/error behavior, and evidence that the capability belongs in a maintained subsystem.

## Canonical flow

```text
Data Collection
      |
      v
Data Storage / durable contracts
      |
      v
Data Analysis
      |
      v
Data Visualization
```

Optional capabilities attach to public boundaries rather than reaching into internals:

```text
collectors -> storage/contracts -> analysis workers -> visualization
                    |
                    +--> Research Assistant
                    +--> Simulation Laboratory
                    +--> Experimental Laboratory
```

## Shared contracts

The lightweight public boundary types live in `laclaugpt.contracts`. The detailed evidence-bearing analysis interchange schema remains `laclaugpt_interchange.DocumentAnnotation` and is independently schema-versioned.

The shared contract layer currently defines:

- `SourceItem`: normalized source item at the Collection -> Storage boundary;
- `AnalysisJob`: backend-neutral analysis request;
- `JobEvent` and `JobState`: inspectable job lifecycle state;
- `VisualizationAggregate`: small read model for dashboards;
- `SourceSink`: Collection-facing write protocol;
- `AnalysisRepository`: Analysis-facing storage protocol;
- `AnalysisExecutor`: execution boundary for analysis workers;
- `VisualizationDataSource`: read-only Visualization boundary;
- `ArtifactStore`: durable file/object-artifact boundary.

These interfaces are intentionally small. Existing mature domain/interchange models should be reused rather than duplicated into a second schema family.

Contract changes are deliberate: bump versions when externally observable fields or semantics change; preserve old readers/upgraders when public artifacts need compatibility; never silently discard evidence/provenance/review state.

## Execution modes

### 1. All-in-one local

One checkout and one machine may host all four core capabilities. This is a composition choice, not permission for implementation layers to import each other freely.

Typical shape:

```bash
pip install -e '.[collection,analysis,visualization]'
laclaugpt collect ...
laclaugpt analyze ...
laclaugpt-dashboard ...
```

Storage may simply be local JSONL/SQLite/filesystem artifacts.

### 2. Sequential single-machine

The durable artifact boundary is the hand-off:

```text
collect -> normalized artifacts -> analyze -> analysis JSONL -> visualize
```

Each stage may finish before the next starts. This is the preferred mental model for reproducibility and debugging.

### 3. Concurrent single-machine

Collector, worker, and dashboard may run as separate processes while sharing local durable storage. The architecture does not require an event bus. File/database state is sufficient until measured workloads justify more complexity.

### 4. Distributed multi-machine

Demonstrated reference topology:

```text
Laptop/workstation                    Shared durable boundary
------------------                    -----------------------
Collection -------------------------> JSONL/object/DB records
                                             |
                                             v
CSC/GPU/HPC host --------------------> Analysis artifacts
                                             |
                                             v
Pouta/web VM ------------------------> Visualization reads only
```

No process assumes a shared Python interpreter or imports another machine's implementation internals. Stable identifiers, manifests, schema versions, provenance, and durable paths/URIs are the integration surface.

A queue/event layer is optional. Introduce Redis Streams, NATS, RabbitMQ, Kafka/Redpanda, Zenoh, or similar only when files/database-backed job state no longer satisfies reliability/throughput requirements.

### 5. HPC / batch

`config/execution/slurm.yaml` is the reference batch profile. It already records resumability/checkpoint/retry semantics. HPC stages communicate through durable files/storage and therefore do not require persistent services. A batch job may terminate after writing its artifact; later jobs or visualization can consume it independently.

Required batch properties:

- deterministic document/run identifiers;
- atomic or otherwise unambiguous completed outputs;
- resumable/checkpointed processing;
- retry without duplicate canonical results;
- explicit model/prompt/codebook/config provenance;
- no hidden dependence on a dashboard, collector, Redis, MongoDB, or other always-on service.

## Progressive communication strategy

Use the least complicated mechanism that satisfies the workload.

**Level A: durable files/object storage**

JSON/JSONL/Parquet, manifests, artifact directories, object references. This is the default interoperability layer and the HPC-safe layer.

**Level B: database-backed job state**

Add queued/running/done/error state, claims/leases, retries, and inspectable worker ownership when concurrent processing makes filesystem conventions insufficient.

**Level C: explicit queue/event bus**

Adopt only with a concrete concurrency, latency, or reliability requirement. Infrastructure choice is deployment-specific and must not leak into theory/domain contracts.

## Configuration composition

LaclauGPT already composes project, arena, machine, and execution profiles rather than duplicating research logic into giant environment-specific configs. Existing execution profiles include `collector-only`, `dashboard-only`, `local-analysis`, `realtime-fullstack`, and `slurm`; machine/project/arena profiles supply the remaining dimensions.

This composition corresponds to the architectural examples in #144:

- minimal/local sequential: local machine + manual/CLI execution;
- local full stack: local machine + `realtime-fullstack`;
- collector-only: `collector-only`;
- dashboard-only: `dashboard-only`;
- CSC batch: CSC machine profile + `slurm`;
- distributed: different machine profiles consume the same durable contracts.

Do not encode research semantics differently merely because deployment changes.

## Reliability invariants

Core modules should preserve these system properties where practical:

- idempotent/restartable jobs;
- checkpoint/resume;
- explicit job/stage state;
- retries without duplicate canonical output;
- deterministic identifiers;
- schema/version provenance;
- model/prompt/codebook/config provenance;
- optional components fail closed or degrade gracefully;
- no machine-specific absolute paths used as domain identifiers;
- no secrets or live private collection configuration in the public repository.

## Maturity labels

Repository components may be labelled:

- `CORE`
- `OPTIONAL-INFRASTRUCTURE`
- `EXPERIMENTAL`
- `LATER-PAPER-CANDIDATE`
- `ARCHIVAL/COMPARISON-ONLY`

A component being present in Git does not place it inside the paper's current scope.

## Relationship to Python architecture

`PYTHON_ARCHITECTURE.md` defines package/import/dependency rules. This document defines system capabilities and execution topology. They are complementary:

- this file answers **what the seven parts are and how they communicate**;
- `PYTHON_ARCHITECTURE.md` answers **where maintained Python code belongs and what it may import**.

The architecture is intentionally modular without assuming microservices. One coherent LaclauGPT can be deployed as one process, several processes, batch jobs, or several machines while preserving the same contracts and research semantics.
