"""The one pipeline entry used by every execution backend."""
from __future__ import annotations

import tempfile
from pathlib import Path

from laclaugpt.execution.core import EffectiveRunConfig, RunStore
from laclaugpt.model import Run

_LEGACY_RUN: dict[str, str] = {}


def run_canonical_pipeline(config: EffectiveRunConfig, run: Run, store: RunStore):
    """Run the existing evidence-first pipeline with durable item checkpoints.

    With no input, return a run plan (useful for scheduler generation). For an
    input CSV, only uncompleted documents are passed to the existing pipeline.
    """
    input_path = config.dataset.get("input")
    if not input_path:
        return {"run_id": run.run_id, "state": "configured",
                "enabled_modules": [name for name, active in config.analysis.items() if active]}
    pipeline_config = config.dataset.get("run_config") or _LEGACY_RUN.get(config.project)
    if not pipeline_config:
        raise ValueError(
            f"project {config.project!r} has multiple analysis arenas; supply --pipeline-config")

    import pandas as pd
    from laclaugpt_interchange import to_jsonl
    from pipeline import document_key, run_pipeline

    frame = pd.read_csv(input_path)
    policy = config.orchestration.get("runtime", {})
    claimed: list[str] = []
    keep = []
    for index, row in frame.iterrows():
        source_id = document_key(row.to_dict())
        accepted = store.claim(config, run.run_id, source_id,
            retry_failed=policy.get("retry_failed_items", False),
            skip_completed=policy.get("skip_already_processed", True))
        keep.append(accepted)
        if accepted:
            claimed.append(source_id)
    if not claimed:
        return {"run_id": run.run_id, "processed": 0, "skipped": len(frame),
                "annotations": []}

    output = Path(config.dataset.get("output") or
                  Path(input_path).with_suffix(f".{run.run_id}.annotations.jsonl"))
    temporary_directory = config.runtime.get("temporary_directory")
    temp_root = Path(temporary_directory) if temporary_directory and "$" not in temporary_directory else None
    try:
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            filtered = Path(directory) / "unprocessed.csv"
            frame.loc[keep].to_csv(filtered, index=False)
            annotations = run_pipeline(str(pipeline_config), str(filtered), False, str(output))
        for annotation in annotations:
            annotation.run_id = run.run_id
        to_jsonl(annotations, str(output))
        for source_id in claimed:
            store.checkpoint(config, run.run_id, source_id)
    except Exception as exc:
        for source_id in claimed:
            store.checkpoint(config, run.run_id, source_id, "failed", str(exc))
        raise
    return {"run_id": run.run_id, "processed": len(claimed),
            "skipped": len(frame) - len(claimed), "output": str(output),
            "annotations": annotations}

