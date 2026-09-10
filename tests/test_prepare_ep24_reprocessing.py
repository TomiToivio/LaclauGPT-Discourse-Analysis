from __future__ import annotations

import csv
from pathlib import Path

from scripts.prepare_ep24_reprocessing import prepare


def test_prepare_deduplicates_and_excludes_old_model_outputs(tmp_path: Path) -> None:
    source = tmp_path / "dashboard.csv"
    fields = [
        "country", "new_id", "whisper_transcript", "whisper_language", "ocr_1",
        "author_username", "source_type", "summary_analysis",
        "formula_of_populism_analysis",
    ]
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([
            {"country": "Finland", "new_id": "FI-1", "whisper_transcript": "lyhyt",
             "whisper_language": "fi", "summary_analysis": "OLD"},
            {"country": "Finland", "new_id": "FI-1",
             "whisper_transcript": "pidempi alkuperäinen puhe", "ocr_1": "ruututeksti",
             "whisper_language": "fi", "formula_of_populism_analysis": "OLD"},
            {"country": "Poland", "new_id": "PL-1", "whisper_transcript": "polski"},
            {"country": "Finland", "new_id": "FI-2", "whisper_transcript": ""},
        ])
    output = tmp_path / "finland.csv"
    report = prepare(source, output, "finland")
    rows = list(csv.DictReader(output.open(encoding="utf-8")))

    assert report["written_documents"] == 1
    assert report["empty_transcript_documents"] == 1
    assert report["conflicting_transcript_documents"] == 1
    assert rows[0]["document_id"] == "FI-1"
    assert rows[0]["transcript"] == "pidempi alkuperäinen puhe"
    assert rows[0]["ocr_text"] == "ruututeksti"
    assert "summary_analysis" not in rows[0]
    assert "formula_of_populism_analysis" not in rows[0]


def test_slurm_render_preserves_arena_and_output(tmp_path: Path) -> None:
    from laclaugpt.config import compose_config
    from laclaugpt.execution import EffectiveRunConfig, ExecutionCoordinator, RunStore
    from laclaugpt.execution.backends import SlurmExecutionBackend

    raw = compose_config(
        "ep24", "roihu", "slurm",
        {"dataset": {"input": "/scratch/input.csv", "output": "/scratch/output.jsonl"}},
        arena="ep24-finland",
    )
    config = EffectiveRunConfig.model_validate(raw)
    store = RunStore(tmp_path / "runs.sqlite3")
    try:
        coordinator = ExecutionCoordinator(config, store, lambda *_: None)
        rendered = SlurmExecutionBackend().render_script(coordinator)
    finally:
        store.connection.close()
    assert "--arena ep24-finland" in rendered
    assert "--dataset /scratch/input.csv" in rendered
    assert "--output /scratch/output.jsonl" in rendered