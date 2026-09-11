#!/usr/bin/env python3
"""Reprocess Finnish and Polish EP24 samples through canonical LaclauGPT."""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

import ep24_asr
import ep24_fetch

REPO_ROOT = os.environ.get("LACLAUGPT_REPO_ROOT", str(Path(__file__).resolve().parents[1]))
DATA_ROOT = os.environ.get("LACLAUGPT_DATA_DIR", str(Path(REPO_ROOT) / "data"))
COUNTRIES = {
    "finland": {"label": "Finland", "arena": "ep24-finland"},
    "poland": {"label": "Poland", "arena": "ep24-poland"},
}
IDENTITY_FIELDS = (
    "new_id", "video_id", "old_id", "country", "author_username", "account_type",
    "source_type", "source_recording", "video_filename", "video_file",
    "recording_date", "recording_datetime", "corrected_date",
    "political_preference", "allas_filename",
)


def paths(country: str, data_root: str = DATA_ROOT) -> dict[str, Path]:
    base = Path(data_root)
    run_root = base / "ep24" / "reprocess" / country
    return {
        "run_root": run_root,
        "manifest": run_root / "manifest.csv",
        "roster": run_root / "source_roster.csv",
        "videos": base / "ep24" / "videos",
        "transcripts": run_root / "transcripts.jsonl",
        "input": run_root / "input.csv",
        "annotations": run_root / "annotations.jsonl",
        "runs": run_root / "runs.sqlite3",
    }


def _clean(value: object) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.casefold() in {"nan", "none"} else text


def _document_id(row: dict[str, str], row_number: int) -> str:
    for field in ("new_id", "video_id", "old_id"):
        if value := _clean(row.get(field)):
            return value
    return f"ep24-row-{row_number}"


def prepare_inputs(source_csv: str | Path, country: str, manifest: str | Path,
                   roster: str | Path, sample_size: int = 0) -> dict[str, int]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    source_fields: list[str] = []
    with Path(source_csv).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        source_fields = list(reader.fieldnames or ())
        missing = {"country", "allas_filename"} - set(source_fields)
        if missing:
            raise ValueError(f"source CSV missing required columns: {sorted(missing)}")
        for row_number, row in enumerate(reader, start=2):
            if _clean(row.get("country")) == COUNTRIES[country]["label"]:
                grouped[_document_id(row, row_number)].append(row)

    ids = sorted(grouped)
    if sample_size:
        ids = ids[:sample_size]
    selected = []
    skipped_no_url = 0
    for document_id in ids:
        rows = grouped[document_id]
        urls = sorted({_clean(row.get("allas_filename")) for row in rows
                       if _clean(row.get("allas_filename"))})
        if not urls:
            skipped_no_url += 1
            continue
        if len(urls) > 1:
            raise ValueError(f"{document_id} has conflicting Allas URLs")
        selected.append((document_id, urls[0], rows))

    manifest = Path(manifest)
    roster = Path(roster)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["document_id", "allas_url", "row_count"])
        for document_id, url, rows in selected:
            writer.writerow([document_id, url, len(rows)])

    fields = [field for field in IDENTITY_FIELDS if field in source_fields]
    if "new_id" not in fields:
        fields.insert(0, "new_id")
    with roster.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for document_id, _url, rows in selected:
            best = max(rows, key=lambda row: sum(bool(_clean(v)) for v in row.values()))
            record = {field: _clean(best.get(field)) for field in fields}
            record["new_id"] = document_id
            writer.writerow(record)
    return {"source_rows": sum(map(len, grouped.values())),
            "unique_documents": len(grouped), "selected_documents": len(selected),
            "skipped_no_url": skipped_no_url}


def canonical_analysis(country: str, p: dict[str, Path]) -> dict:
    from laclaugpt.canonical_pipeline import run_canonical_pipeline
    from laclaugpt.config import compose_config
    from laclaugpt.execution import EffectiveRunConfig, ExecutionCoordinator, RunStore

    effective = compose_config(
        "ep24", "roihu", "slurm",
        {"dataset": {"input": str(p["input"]), "output": str(p["annotations"])}},
        arena=COUNTRIES[country]["arena"],
    )
    config = EffectiveRunConfig.model_validate(effective)
    store = RunStore(p["runs"])
    try:
        run, result = ExecutionCoordinator(config, store, run_canonical_pipeline).execute()
        return {"run_id": run.run_id, **result}
    finally:
        store.connection.close()


def run_country(country: str, source_csv: str | Path, data_root: str = DATA_ROOT,
                sample_size: int = 0, dry_run: bool = False, model=None) -> dict:
    p = paths(country, data_root)
    status = {"country": country,
              "prepared": prepare_inputs(source_csv, country, p["manifest"],
                                         p["roster"], sample_size)}
    if dry_run:
        status["dry_run"] = True
        return status
    status["fetched"] = len(ep24_fetch.fetch_all(p["manifest"], p["videos"]))
    status["transcribed"] = ep24_asr.transcribe_manifest(
        p["manifest"], p["videos"], p["transcripts"], model=model)
    from ep24_pipeline import build_canonical_csv
    status["canonical_rows"] = build_canonical_csv(
        p["manifest"], p["transcripts"], p["roster"], p["input"])
    status["analysis"] = canonical_analysis(country, p)
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--country", required=True, choices=sorted(COUNTRIES))
    parser.add_argument("--source-csv", required=True)
    parser.add_argument("--data-root", default=DATA_ROOT)
    parser.add_argument("--sample-size", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.sample_size < 0:
        parser.error("--sample-size must be zero or positive")
    print(json.dumps(run_country(args.country, args.source_csv, args.data_root,
                                 args.sample_size, args.dry_run),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
