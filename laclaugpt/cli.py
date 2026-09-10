"""Minimal backend-independent command line entrypoint."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from laclaugpt.adapters import LegacyCSVAdapter
from laclaugpt.config import (
    arena_from_legacy_config,
    compose_config,
    list_arenas,
    list_executions,
    list_machines,
    list_projects,
)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="laclaugpt")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "profiles",
        help="list canonical project, arena, machine and execution profiles",
    )
    from laclaugpt.collect.cli import register as register_collect
    register_collect(sub)
    analyze = sub.add_parser("analyze", help="compose and validate an analysis run")
    analyze.add_argument("dataset", nargs="?")
    analyze.add_argument("--project", required=True, choices=list_projects())
    analyze.add_argument("--arena", choices=list_arenas())
    analyze.add_argument("--machine", required=True, choices=list_machines())
    analyze.add_argument("--execution", default="cli", choices=list_executions())
    analyze.add_argument("--parent-run-id")
    analyze.add_argument(
        "--pipeline-config",
        help="deprecated alias for one of the migrated run_configs/arena_*.yaml files",
    )
    analyze.add_argument("--show-config", action="store_true")
    run = sub.add_parser("run", help="execute or render a scheduled run")
    run.add_argument("--project", required=True, choices=list_projects())
    run.add_argument("--arena", choices=list_arenas())
    run.add_argument("--machine", required=True, choices=list_machines())
    run.add_argument("--execution", required=True, choices=list_executions())
    run.add_argument("--dataset")
    run.add_argument("--output", help="canonical JSONL output path for the run")
    run.add_argument("--parent-run-id")
    run.add_argument(
        "--pipeline-config",
        help="deprecated alias for one of the migrated run_configs/arena_*.yaml files",
    )
    run.add_argument("--inside-scheduler", action="store_true", help=argparse.SUPPRESS)
    dashboard = sub.add_parser(
        "dashboard",
        help="launch local/Pouta visualization for canonical JSONL output",
    )
    dashboard.add_argument("data")
    dashboard.add_argument("--project", required=True, choices=list_projects())
    dashboard.add_argument("--arena", required=True, choices=list_arenas())
    dashboard.add_argument("--review-db", default="")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8501)
    imp = sub.add_parser("import-legacy", help="convert legacy TikTok CSV to canonical JSONL")
    imp.add_argument("input")
    imp.add_argument("--output", "-o", required=True)
    return root


def _resolve_arena(args: argparse.Namespace) -> str:
    arena = getattr(args, "arena", None)
    legacy = getattr(args, "pipeline_config", None)
    if legacy:
        migrated = arena_from_legacy_config(legacy)
        if arena and arena != migrated:
            raise SystemExit(
                f"--arena {arena!r} conflicts with legacy --pipeline-config arena {migrated!r}"
            )
        arena = migrated
    if not arena:
        raise SystemExit(
            "analysis requires --arena; use `laclaugpt profiles` to list canonical arenas"
        )
    return arena


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "collect":
        from laclaugpt.collect.cli import run as run_collect
        return run_collect(args)
    if args.command == "profiles":
        print(json.dumps({
            "projects": list_projects(),
            "arenas": list_arenas(),
            "machines": list_machines(),
            "executions": list_executions(),
        }))
        return 0
    if args.command == "dashboard":
        from laclaugpt.visualization.launcher import launch

        return launch(
            args.data,
            project=args.project,
            arena=args.arena,
            review_db=args.review_db,
            host=args.host,
            port=args.port,
        )
    if args.command in {"analyze", "run"}:
        execution = args.execution
        arena = _resolve_arena(args)
        dataset = getattr(args, "dataset", None)
        dataset_overrides = {}
        if dataset:
            dataset_overrides["input"] = dataset
        run_output = getattr(args, "output", None)
        if run_output:
            dataset_overrides["output"] = run_output
        overrides = {"dataset": dataset_overrides} if dataset_overrides else None
        effective = compose_config(
            args.project,
            args.machine,
            execution,
            overrides,
            arena=arena,
        )
        if getattr(args, "show_config", False):
            print(json.dumps(effective, ensure_ascii=False, indent=2))
        from laclaugpt.execution import (
            EffectiveRunConfig,
            ExecutionCoordinator,
            RunStore,
            execution_backend,
        )
        from laclaugpt.canonical_pipeline import run_canonical_pipeline

        config = EffectiveRunConfig.model_validate(effective)
        run_root = Path(dataset).resolve().parent if dataset else Path.cwd() / "data"
        store = RunStore(run_root / "runs.sqlite3")
        coordinator = ExecutionCoordinator(
            config,
            store,
            run_canonical_pipeline,
            parent_run_id=args.parent_run_id,
        )
        backend = execution_backend(execution)
        if args.command == "run" and execution == "slurm" and not args.inside_scheduler:
            print(backend.run(coordinator), end="")
        else:
            outcome = (
                coordinator.execute()
                if getattr(args, "inside_scheduler", False)
                else backend.run(coordinator)
            )
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
                "annotations": [
                    x.model_dump(mode="json", by_alias=True) for x in bundle.annotations
                ],
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
