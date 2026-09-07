"""The one pipeline entry used by every execution backend."""
from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path

from laclaugpt.execution.core import EffectiveRunConfig, RunStore
from laclaugpt.model import Run


def _apply_analysis_switches(annotation, analysis: dict[str, bool]) -> None:
    """Make the effective module map authoritative over exported results.

    Some historical prompt stages return several related coding families in one
    model call.  Until those prompts are split further, disabled families are
    stripped before publication so an off switch can never leak a result into
    the canonical interchange.
    """
    if not analysis.get("laclau", False):
        annotation.signifiers = []
        annotation.signifier_roles = []
        annotation.articulations = []
        annotation.formation_candidates = []
        annotation.discourses = []
        annotation.hegemonic_evidence = []
        annotation.nodal_points = [
            item.element for item in annotation.populism_elements
            if item.nodal_candidate
        ]
    if not analysis.get("sociotechnical_imaginaries", False):
        annotation.imaginaries = []
    if not analysis.get("topics", False):
        annotation.topics = []
    if not analysis.get("entities", False):
        annotation.entities = []
    if not analysis.get("palonen", False):
        annotation.populist = None
        annotation.populism_analysis = ""
        annotation.non_populist_reason = ""
        annotation.us = []
        annotation.frontier = []
        annotation.populism_elements = []
        annotation.affects = []


def run_canonical_pipeline(config: EffectiveRunConfig, run: Run, store: RunStore):
    """Run the evidence-first pipeline from the composed effective config.

    There is deliberately no second arena YAML hand-off here. The project,
    arena, machine and execution profiles have already been composed into
    ``config``; the root pipeline receives only a compact adapter carrying the
    same execution ``run_id`` and stable arena/profile identity.
    """
    input_path = config.dataset.get("input")
    enabled_modules = [name for name, active in config.analysis.items() if active]
    analysis_profile = getattr(config, "analysis_profile", config.project)
    arena_id = getattr(config, "arena", "")
    if not input_path:
        return {
            "run_id": run.run_id,
            "analysis_profile": analysis_profile,
            "arena_id": arena_id,
            "state": "configured",
            "enabled_modules": enabled_modules,
        }
    if not arena_id:
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
            "analysis_profile": analysis_profile,
            "arena_id": arena_id,
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
    pipeline_run.output_path = output

    try:
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            filtered = Path(directory) / "unprocessed.csv"
            selected = frame.loc[keep].copy()
            # The multimodal project switch controls derived visual/OCR input.
            # Transcripts remain text representations and are not discarded.
            if not config.analysis.get("multimodal", False):
                for column in ("frame_analysis", "ocr", "ocr_text"):
                    if column in selected.columns:
                        selected[column] = ""
            selected.to_csv(filtered, index=False)
            annotations = run_pipeline(pipeline_run, str(filtered), False, str(output))

        for annotation in annotations:
            annotation.run_id = run.run_id
            _apply_analysis_switches(annotation, config.analysis)
            annotation.collection_provenance.update({
                "project": config.project,
                "analysis_profile": analysis_profile,
                "arena_id": arena_id,
                "enabled_analysis_modules": enabled_modules,
                "effective_config_fingerprint": config.fingerprint(),
            })
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
        "analysis_profile": analysis_profile,
        "arena_id": arena_id,
        "enabled_modules": enabled_modules,
        "processed": len(claimed),
        "skipped": len(frame) - len(claimed),
        "output": str(output),
        "annotations": annotations,
    }
