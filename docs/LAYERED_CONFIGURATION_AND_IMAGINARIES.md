# LaclauGPT 2.0 addendum

## Optional Sociotechnical Imaginaries

Sociotechnical imaginaries are an optional theoretical module alongside,
not inside, the Laclaudian model. `SociotechnicalImaginary`,
`ImaginaryElement`, and `ImaginaryRelation` use evidence IDs, provenance,
confidence, and the normal human-review lifecycle. Creating an imaginary
requires an explicit assertion that collective articulation is supported;
a prediction or topic mention is insufficient.

Supported graph relations are `ARTICULATES_IMAGINARY` (Discourse),
`PROMOTES` (Actor), and `PART_OF_IMAGINARY` (Concept). Their endpoints remain
separate canonical object types.

## Layered run configuration

Configuration is composed from four inputs and three independent profile layers:

```text
config/projects/<project>.yaml
        +
config/machines/<machine>.yaml
        +
config/execution/<execution>.yaml
        +
optional per-run overrides
        =
effective configuration
```

Project profiles (`ai26`) select analytical
modules independently. Machine profiles (`laskin`, `roihu`, `pouta`,
`laptop`) select only repositories, services, and runtime paths. Execution
profiles (`slurm`, `cron`, `cli`, `agent`, `manual`) select orchestration only.
Machine profiles must never contain an `analysis` section and execution
profiles must contain neither analysis nor backends. Context Memory filters
retrieved records by both active project and enabled module.

Examples:

```bash
laclaugpt analyze --project ai26 --machine roihu --show-config
laclaugpt analyze --project ai26 --machine roihu --show-config
laclaugpt run --project ai26 --machine roihu --execution slurm
```

All execution adapters dispatch the same `ExecutionCoordinator`. A SQLite run
journal records the full configuration snapshot, host, scheduler job ID,
parent run, pipeline version, and per-source checkpoints. The configuration
fingerprint plus source ID is the idempotency key across resume, Cron reruns,
Slurm restarts, and agent retries.
