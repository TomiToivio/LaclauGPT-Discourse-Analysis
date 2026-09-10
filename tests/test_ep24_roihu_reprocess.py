from __future__ import annotations

import csv
from pathlib import Path

from scripts.ep24_roihu_reprocess import prepare_inputs


def test_prepare_inputs_deduplicates_and_excludes_model_outputs(tmp_path: Path) -> None:
    source = tmp_path / "dashboard.csv"
    fields = ["country", "new_id", "allas_filename", "author_username",
              "summary_analysis", "formula_of_populism_analysis"]
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([
            {"country": "Finland", "new_id": "FI-1", "allas_filename": "https://x/1.mp4",
             "summary_analysis": "OLD"},
            {"country": "Finland", "new_id": "FI-1", "allas_filename": "https://x/1.mp4",
             "author_username": "actor", "formula_of_populism_analysis": "OLD"},
            {"country": "Poland", "new_id": "PL-1", "allas_filename": "https://x/2.mp4"},
        ])
    manifest = tmp_path / "manifest.csv"
    roster = tmp_path / "roster.csv"
    report = prepare_inputs(source, "finland", manifest, roster)
    manifests = list(csv.DictReader(manifest.open(encoding="utf-8")))
    roster_rows = list(csv.DictReader(roster.open(encoding="utf-8")))

    assert report == {"source_rows": 2, "unique_documents": 1,
                      "selected_documents": 1, "skipped_no_url": 0}
    assert manifests == [{"document_id": "FI-1", "allas_url": "https://x/1.mp4",
                          "row_count": "2"}]
    assert roster_rows[0]["author_username"] == "actor"
    assert "summary_analysis" not in roster_rows[0]
    assert "formula_of_populism_analysis" not in roster_rows[0]


def test_sample_size_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "dashboard.csv"
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["country", "new_id", "allas_filename"])
        writer.writeheader()
        writer.writerow({"country": "Finland", "new_id": "B", "allas_filename": "https://x/b"})
        writer.writerow({"country": "Finland", "new_id": "A", "allas_filename": "https://x/a"})
    manifest = tmp_path / "manifest.csv"
    prepare_inputs(source, "finland", manifest, tmp_path / "roster.csv", sample_size=1)
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    assert [row["document_id"] for row in rows] == ["A"]
