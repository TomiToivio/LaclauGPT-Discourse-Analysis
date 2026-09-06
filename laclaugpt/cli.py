"""Minimal backend-independent command line entrypoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from laclaugpt.adapters import LegacyCSVAdapter
from laclaugpt.config import (compose_config, list_executions, list_machines,
                              list_projects)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="laclaugpt")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("profiles", help="list separate project, machine and execution profiles")
    analyze = sub.add_parser("analyze", help="compose and validate an analysis run")
    analyze.add_argument("dataset", nargs="?")
    analyze.add_argument("--project", required=True, choices=list_projects())
    analyze.add_argument("--machine", required=True, choices=list_machines())
    analyze.add_argument("--execution", default="cli", choices=list_executions())
    analyze.add_argument("--parent-run-id")
    analyze.add_argument("--pipeline-config")
    analyze.add_argument("--show-config", action="store_true")
    run = sub.add_parser("run", help="execute or render a scheduled run")
    run.add_argument("--project", required=True, choices=list_projects())
    run.add_argument("--machine", required=True, choices=list_machines())
    run.add_argument("--execution", required=True, choices=list_executions())
    run.add_argument("--dataset")
    run.add_argument("--parent-run-id")
    run.add_argument("--pipeline-config")
    run.add_argument("--inside-scheduler", action="store_true", help=argparse.SUPPRESS)
    imp = sub.add_parser("import-legacy", help="convert legacy TikTok CSV to canonical JSONL")
    imp.add_argument("input")
    imp.add_argument("--output", "-o", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "profiles":
        print(json.dumps({"projects": list_projects(), "machines": list_machines(),
                          "executions": list_executions()}))
        return 0
    if args.command in {"analyze", "run"}:
        execution = args.execution
        dataset = getattr(args, "dataset", None)
        dataset_overrides = {}
        if dataset:
            dataset_overrides["input"] = dataset
        if args.pipeline_config:
            dataset_overrides["run_config"] = args.pipeline_config
        overrides = {"dataset": dataset_overrides} if dataset_overrides else None
        effective = compose_config(args.project, args.machine, execution, overrides)
        # The effective configuration is the stable hand-off to analysis
        # stages/job launchers. No project module leaks into another project.
        if getattr(args, "show_config", False):
            print(json.dumps(effective, ensure_ascii=False, indent=2))
        from laclaugpt.execution import (EffectiveRunConfig, ExecutionCoordinator,
                                         RunStore, execution_backend)
        from laclaugpt.canonical_pipeline import run_canonical_pipeline
        config = EffectiveRunConfig.model_validate(effective)
        run_root = Path(dataset).resolve().parent if dataset else Path.cwd() / "data"
        store = RunStore(run_root / "runs.sqlite3")
        coordinator = ExecutionCoordinator(config, store, run_canonical_pipeline,
            parent_run_id=args.parent_run_id)
        backend = execution_backend(execution)
        if args.command == "run" and execution == "slurm" and not args.inside_scheduler:
            # Outside an allocation the slurm backend returns the generated
            # SBATCH script (submission is an explicit orchestration action).
            print(backend.run(coordinator), end="")
        else:
            outcome = (coordinator.execute() if getattr(args, "inside_scheduler", False)
                       else backend.run(coordinator))
            if isinstance(outcome, tuple) and len(outcome) == 2:
                run_record, result = outcome
            else:
                run_record, result = None, outcome
            payload = {"result": result}
            if run_record is not None:
                payload["run"] = run_record.model_dump(mode="json")
            print(json.dumps(payload, ensure_ascii=False, default=str))
        return 0
    bundles = LegacyCSVAdapter().import_documents(args.input)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for bundle in bundles:
            payload = {
                "source": bundle.source.model_dump(mode="json"),
                "ingestion": bundle.ingestion.model_dump(mode="json"),
                "provenance": bundle.provenance.model_dump(mode="json"),
                "actors": [x.model_dump(mode="json") for x in bundle.actors],
                "media": [x.model_dump(mode="json") for x in bundle.media],
                "representations": [x.model_dump(mode="json") for x in bundle.representations],
                "annotations": [x.model_dump(mode="json", by_alias=True) for x in bundle.annotations],
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
