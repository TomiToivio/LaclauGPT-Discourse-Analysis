# Deployment profiles

LaclauGPT is one codebase deployed in several runtime topologies. Research semantics stay in the project/arena layers; infrastructure and orchestration change by machine/execution profile.

Canonical chain:

`project -> arena/dataset -> machine -> execution -> effective run config -> run`

The deployment profiles below are deliberately modular. Collection, analysis, LLM access, Context Memory, visualization and Slurm execution are not assumed to live on the same host.

## Supported profiles

| Environment | Machine profile | Execution profile | Collector | Analysis | LLM | Dashboard | Slurm |
|---|---|---|---:|---:|---|---:|---:|
| Laptop collector | `laptop-collector` | `collector-only` | yes | no | none | no | no |
| Laptop local analysis | `laptop-ollama` | `local-analysis` | no by default | yes | local Ollama `gemma4:e2b` | no by default | no |
| Laptop cloud analysis | `laptop-cloud` | `cloud-analysis` | no by default | yes | `gemma4:31b-cloud` | no by default | no |
| Linux dashboard | `linux-dashboard` | `dashboard-only` | no | no | none | yes | no |
| Linux GPU realtime | `linux-gpu-realtime` | `realtime-fullstack` | yes | yes | local Ollama `gemma4:26b` | yes | no |
| CSC Roihu | `roihu` | `slurm` | no | yes | local Ollama `gemma4:26b` | no | yes |

Model names are profile defaults, not research semantics. They can be replaced by machine-local configuration without changing the project or arena definition.

## 1. Laptop: browser collector only

Use a laptop for researcher-driven browser collection without installing or starting Ollama, the analysis pipeline or the dashboard.

```bash
laclaugpt profiles
# collector is launched through collector/ using the laptop-collector infrastructure profile
```

The collector writes to configured research storage. Collection can later be consumed by analysis on another machine through the canonical source/interchange conventions.

## 2. Laptop: local or cloud-assisted analysis

For a low-resource local run:

```bash
laclaugpt analyze my_corpus.csv \
  --project ai26 --arena elites \
  --machine laptop-ollama --execution local-analysis
```

The default local model is `gemma4:e2b` through Ollama.

For cloud-assisted analysis:

```bash
laclaugpt analyze my_corpus.csv \
  --project ai26 --arena elites \
  --machine laptop-cloud --execution cloud-analysis
```

The default cloud profile names `gemma4:31b-cloud`. Credentials and endpoints must come from runtime/environment configuration and must not be committed.

## 3. Linux web server: dashboard only

Use `linux-dashboard` + `dashboard-only` when the host only serves visualization and researcher review.

```bash
laclaugpt dashboard data/annotations.jsonl --project ai26 --arena elites
```

This profile must not require Ollama or collector dependencies. Production HTTP binding, TLS, authentication and reverse proxy configuration stay outside research semantics.

## 4. Linux GPU server: realtime full stack

Use `linux-gpu-realtime` + `realtime-fullstack` for a persistent operational installation where collector, analysis and dashboard all run on one GPU host.

The profile enables:

- collection;
- local Ollama analysis with `gemma4:26b`;
- incremental processing;
- dashboard visualization;
- persistent Context Memory.

Even on one host these remain separate services. They should communicate through canonical files, APIs, databases or queues rather than hidden in-process coupling. Process supervision is intentionally external so systemd, containers or another supervisor can restart components independently.

## 5. CSC Roihu / Slurm: analysis only

Use `roihu` + `slurm` for GPU batch analysis.

```bash
laclaugpt run \
  --project ai26 --arena elites \
  --machine roihu --execution slurm \
  --dataset my_corpus.csv
```

The Slurm execution profile owns scheduler resources, checkpoint/retry behaviour and batch mode. The Roihu machine profile owns service/backend/runtime infrastructure. It explicitly disables collector and dashboard services and selects local Ollama `gemma4:26b`.

No persistent web service should be started from a Slurm job.

## Service boundaries

The following invariants apply across all deployments:

1. Collector-only must work without analysis, Ollama or dashboard dependencies.
2. Analysis-only must work without collection or visualization.
3. Dashboard-only must consume existing canonical outputs without loading an LLM.
4. Slurm execution must never launch a browser collector or dashboard.
5. Full-stack deployment may colocate all modules, but they remain independently restartable services.
6. Canonical interchange/output must remain portable between environments.
7. Project and arena profiles must not be duplicated merely because hardware or execution topology changes.

## Configuration ownership

Machine profiles own:

- storage/backend selection;
- service availability;
- LLM transport/model defaults;
- GPU/runtime characteristics;
- host-local service parameters.

Execution profiles own:

- manual/service/batch/realtime mode;
- scheduler type;
- recurrence;
- retry/resume/checkpoint behaviour;
- Slurm resource requests.

Project and arena profiles continue to own theory, analytical modules, dataset semantics and research-specific model hints.

## Validation

`tests/test_deployment_profiles.py` composes every required profile offline and checks that:

- required services are enabled/disabled correctly;
- dashboard-only and collector-only have no accidental LLM dependency;
- laptop local/cloud profiles select the intended model route;
- GPU realtime enables all three major services;
- Roihu is analysis-only under Slurm;
- changing machine/execution topology does not change project/arena research semantics.

The tests do not launch real models, browsers, dashboards or Slurm jobs.

## Design principle

**One LaclauGPT, many environments.**

The runtime topology is replaceable infrastructure. The discourse-analysis semantics are not.

## DEPLOYMENT_HOST AI26 realtime deployment (operational)

The concrete `linux-gpu-realtime` + `realtime-fullstack` installation runs on
`laskin01` (3x V100-32GB). Its machine-local, uncommitted configuration and
the implementation status of every service (collection timers, incremental
analysis with stage-aware local gemma4 routing, dashboard, minet batch chain,
MongoDB roles, backups) are documented in
[DEPLOYMENT_LASKIN_AI26.md](DEPLOYMENT_LASKIN_AI26.md).