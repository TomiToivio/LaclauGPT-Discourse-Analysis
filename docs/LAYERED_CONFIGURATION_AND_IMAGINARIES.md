# LaclauGPT 2.0 addendum

> **Configuration note:** the configuration description in this addendum is subordinate to [`CANONICAL_CONFIGURATION.md`](CANONICAL_CONFIGURATION.md), which is the current runtime contract. The older pre-arena four-input description has been retired.

## Optional Sociotechnical Imaginaries

Sociotechnical imaginaries are an optional theoretical module alongside,
not inside, the Laclaudian model. `SociotechnicalImaginary`,
`ImaginaryElement`, and `ImaginaryRelation` use evidence IDs, provenance,
confidence, and the normal human-review lifecycle. Creating an imaginary
requires an explicit assertion that collective articulation is supported;
a prediction or topic mention is insufficient.

Document-level model output should therefore be read as a **sociotechnical-imaginary candidate**, not a corpus-level finding. Candidate frequency is descriptive only and does not establish theoretical importance.

Supported graph relations are `ARTICULATES_IMAGINARY` (Discourse),
`PROMOTES` (Actor), and `PART_OF_IMAGINARY` (Concept). Their endpoints remain
separate canonical object types.

## Canonical layered run configuration

The current configuration chain is:

```text
config/projects/<project>.yaml
        +
config/arenas/<arena>.yaml
        +
config/machines/<machine>.yaml
        +
config/execution/<execution>.yaml
        +
optional supported per-run overrides
        =
effective configuration
```

The ownership boundary is important:

- **project** profiles select analytical modules and project-wide defaults;
- **arena** profiles own corpus/dataset selection, source metadata and arena-specific data-boundary policy;
- **machine** profiles own infrastructure, paths and machine/runtime capabilities;
- **execution** profiles own orchestration such as CLI, Slurm, Cron or agent execution;
- supported per-run overrides may narrow a run but must not bypass project/arena policy or LLM routing/data boundaries.

Machine profiles must never contain an `analysis` section. Execution profiles must not redefine analytical modules or infrastructure policy. Agents must use the same composed configuration as human CLI runs rather than creating an alternate hidden configuration path.

Examples:

```bash
laclaugpt analyze --project ai26 --arena elites --machine roihu --show-config
laclaugpt run --project ai26 --arena elites --machine roihu --execution slurm
laclaugpt run --project ai26 --arena grassroots --machine roihu --execution agent
```

All execution adapters dispatch the same `ExecutionCoordinator`. A SQLite run
journal records the full configuration snapshot, host, scheduler job ID,
parent run, pipeline version, and per-source checkpoints. The effective configuration fingerprint plus source identity is used for reproducible/resumable execution.

For exact field ownership, validation rules and module-switch semantics, use [`CANONICAL_CONFIGURATION.md`](CANONICAL_CONFIGURATION.md) as the authoritative documentation.