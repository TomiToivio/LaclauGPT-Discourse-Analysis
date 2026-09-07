"""The one pipeline entry used by every execution backend."""
from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path

from laclaugpt.execution.core import EffectiveRunConfig, RunStore
from laclaugpt.model import Run


def run_canonical_pipeline(config: EffectiveRunConfig, run: Run, store: RunStore):
    """Run the evidence-first pipeline from the composed effective config.

    There is deliberately no second arena YAML hand-off here.  The project,
    arena, machine and execution profiles have already been composed into
    ``config``; the root pipeline receives only a compact adapter carrying the
    same execution ``run_id`` and stable arena/profile identity.
    """
    input_path = config.dataset.get("input")
    enabled_modules = [name for name, active in config.analysis.items() if active]
    if not input_path:
        return {
            "run_id": run.run_id,
            "analysis_profile": getattr(config, "analysis_profile", config.project),
            "arena_id": getattr(config, "arena", ""),
            "state": "configured",
            "enabled_modules": enabled_modules,
        }
    if not getattr(config, "arena", ""):
        raise ValueError("analysis execution requires an explicit canonical arena")

    import pandas as pd
    from laclaugpt_interchange import to_jsonl
    from pipeline import document_key, run_pipeline
    from run_config import run_config_from_effective

    frame = pd.read_csv(input_path)
    languages = tuple(str(value) for value in config.dataset.get("languages", []) if value)
    if languages and "language" in frame.columns:
        frame = frame[frame["language"].isin(languages)]
    if frame.empty:
        raise ValueError("no input rows remain after effective-config language filtering")

    policy = config.orchestration.get("runtime", {})
    claimed: dict[str, str] = {}
    keep = []
    for _, row in frame.iterrows():
        source_id = document_key(row.to_dict())
        accepted = store.claim(
            config, run.run_id, source_id,
            retry_failed=policy.get("retry_failed_items", False),
            skip_completed=policy.get("skip_already_processed", True),
            stale_after=(
                timedelta(seconds=policy["claim_lease_seconds"])
                if policy.get("claim_lease_seconds") is not None else None
            ),
        )
        keep.append(bool(accepted))
        if accepted:
            claimed[source_id] = accepted.token
    if not claimed:
        return {
            "run_id": run.run_id,
            "analysis_profile": getattr(config, "analysis_profile", config.project),
            "arena_id": getattr(config, "arena", ""),
            "processed": 0,
            "skipped": len(frame),
            "annotations": [],
        }

    output = Path(
        config.dataset.get("output")
        or Path(input_path).with_suffix(f".{run.run_id}.annotations.jsonl")
    )
    temporary_directory = config.runtime.get("temporary_directory")
    temp_root = (
        Path(temporary_directory)
        if temporary_directory and "$" not in temporary_directory else None
    )
    pipeline_run = run_config_from_effective(
        config,
        run.run_id,
        repository_root=Path(__file__).resolve().parents[1],
    )
    # The canonical output path is execution-instance data and therefore wins
    # over the stable arena work-directory default.
    pipeline_run.output_path = output

    try:
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            filtered = Path(directory) / "unprocessed.csv"
            frame.loc[keep].to_csv(filtered, index=False)
            annotations = run_pipeline(pipeline_run, str(filtered), False, str(output))
        # Defensive invariant: the pipeline adapter already uses this run_id,
        # but never allow a compatibility object to escape with another one.
        for annotation in annotations:
            annotation.run_id = run.run_id
        to_jsonl(annotations, str(output))
        for source_id, claim_token in claimed.items():
            store.checkpoint(
                config, run.run_id, source_id, claim_token=claim_token
            )
    except Exception as exc:
        for source_id, claim_token in claimed.items():
            store.checkpoint(
                config, run.run_id, source_id, "failed", str(exc),
                claim_token=claim_token,
            )
        raise
    return {
        "run_id": run.run_id,
        "analysis_profile": getattr(config, "analysis_profile", config.project),
        "arena_id": getattr(config, "arena", ""),
        "enabled_modules": enabled_modules,
        "processed": len(claimed),
        "skipped": len(frame) - len(claimed),
        "output": str(output),
        "annotations": annotations,
    }
