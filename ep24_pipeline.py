# -*- coding: utf-8 -*-
"""EP24 full pipeline: fetch -> ASR -> screen metadata -> canonical analysis.

Issue #73 (revised): the whole chain as SLURM jobs for Finland and Poland.
Stage flow per country:

1. fetch      — Allas videos -> videos dir (dedup by URL, resume-safe)
2. asr        — faster-whisper large-v3 + vad_filter -> transcripts JSONL
3. screenmeta — OCR keyframes -> poster identity metadata (digital ethnography)
4. canon      — build the canonical CSV (transcript = source text) and run
                `pipeline.run_pipeline` with the ep24 arena config
                (summary/discourse/populism/postprocess) -> annotations.jsonl

Repository and data roots are supplied by CLI/environment at runtime. Transient
videos prefer $TMPDIR. Legacy CSV columns ride only as identity/metadata, never
as text source.

Everything here is offline-testable: LLM and whisper are injected mocks in
tests/test_ep24_pipeline.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import ep24_asr
import ep24_fetch
import ep24_screen_metadata

REPO_ROOT = os.environ.get("LACLAUGPT_REPO_ROOT", str(Path(__file__).resolve().parent))
DATA_ROOT = os.environ.get("LACLAUGPT_DATA_DIR", str(Path(__file__).resolve().parent / "data"))

COUNTRIES = {
    "finland": {"manifest": "finland_manifest.csv", "codebook": "ep24_finland",
                "topic_key": "ep24-finland", "language": "fi", "country_code": "FI"},
    "poland": {"manifest": "poland_manifest.csv", "codebook": "ep24_poland",
               "topic_key": "ep24-poland", "language": "pl", "country_code": "PL"},
}


def country_paths(country: str, *, data_root: str = DATA_ROOT,
                  repo_root: str = REPO_ROOT) -> dict[str, Path]:
    """Standard runtime layout for one country's run."""
    cfg = COUNTRIES[country]
    base = Path(data_root)
    return {
        "repo_root": Path(repo_root),
        "csv": base / "ep24" / "csv" / cfg["manifest"],
        "videos": base / "ep24" / "videos",
        "transcripts": base / "ep24" / "annotations" / f"{country}_transcripts.jsonl",
        "canonical_csv": base / "ep24" / "csv" / f"ep24_{country}_canonical.csv",
        "annotations": base / "ep24" / "annotations" / f"{country}_annotations.jsonl",
    }


def build_canonical_csv(manifest_path: str | Path, transcripts_path: str | Path,
                        legacy_csv: str | Path, out_path: str | Path,
                        *, legacy_sample_csv: str | Path | None = None) -> int:
    """Join transcripts (+ screen metadata) with legacy identity metadata."""
    import ep24_screen_metadata

    legacy: dict[str, dict] = {}
    with open(legacy_csv, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            nid = row.get("new_id", "").strip()
            if nid and nid not in legacy:
                legacy[nid] = {
                    "country": row.get("country", ""),
                    "political_preference": row.get("political_preference", ""),
                    "corrected_date": row.get("corrected_date", ""),
                    "account_type": row.get("account_type", ""),
                    "source_type": row.get("source_type", ""),
                }

    transcripts: dict[str, dict] = {}
    with open(transcripts_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            transcripts[rec["document_id"]] = rec

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with open(out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "document_id", "transcript", "country", "language",
            "political_preference", "corrected_date", "account_type",
            "source_type", "screen_handle", "screen_platform",
            "screen_metadata_json",
        ])
        with open(manifest_path, encoding="utf-8", newline="") as mf:
            for row in csv.DictReader(mf):
                doc_id = row["document_id"].strip()
                rec = transcripts.get(doc_id)
                if not rec or not rec.get("transcript"):
                    continue
                meta = ep24_screen_metadata.extract_screen_metadata(
                    rec.get("screen_ocr", "") or "")
                ident = legacy.get(doc_id, {})
                writer.writerow([
                    doc_id, rec["transcript"], ident.get("country", ""),
                    rec.get("language", ""), ident.get("political_preference", ""),
                    ident.get("corrected_date", ""), ident.get("account_type", ""),
                    ident.get("source_type", ""), meta.handle, meta.platform,
                    json.dumps(ep24_screen_metadata.screen_metadata_record(meta),
                               ensure_ascii=False),
                ])
                written += 1
    return written


def run_country(country: str, *, data_root: str = DATA_ROOT,
                repo_root: str = REPO_ROOT, run_config: str | None = None,
                dry_run: bool = False, model=None) -> dict:
    paths = country_paths(country, data_root=data_root, repo_root=repo_root)
    status: dict = {"country": country}

    fetched = ep24_fetch.fetch_all(paths["csv"], paths["videos"])
    status["fetched"] = len(fetched)

    n = ep24_asr.transcribe_manifest(paths["csv"], paths["videos"],
                                     paths["transcripts"],
                                     model_size=ep24_asr.DEFAULT_MODEL,
                                     model=model)
    status["transcribed"] = n

    written = build_canonical_csv(paths["csv"], paths["transcripts"],
                                  paths["csv"].parent / f"ep24_{country}.csv",
                                  paths["canonical_csv"])
    status["canonical_rows"] = written

    run_id = f"ep24-mm-{country}"
    if dry_run:
        status["dry_run"] = True
        return status
    import pipeline as canon
    annotations = canon.run_pipeline(
        run_id=run_id,
        csv_path=str(paths["canonical_csv"]),
        output_path=str(paths["annotations"]),
    )
    status["annotated"] = len(annotations)
    return status


def _slurm_script(country: str, *, time_limit: str = "08:00:00") -> str:
    return f"""#!/bin/bash
#SBATCH --job-name=ep24_full_{country}
#SBATCH --partition=gpu
#SBATCH --time={time_limit}
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gpus=1
#SBATCH --output=ep24_full_{country}_%j.out

set -euo pipefail
: "${{LACLAUGPT_REPO_ROOT:?set LACLAUGPT_REPO_ROOT to the checked-out repository}}"
: "${{LACLAUGPT_DATA_DIR:?set LACLAUGPT_DATA_DIR to the controlled research-data root}}"
REPO_ROOT=$LACLAUGPT_REPO_ROOT
DATA_ROOT=$LACLAUGPT_DATA_DIR
cd "$REPO_ROOT"

export LACLAUGPT_MEMORY_DIR=$DATA_ROOT/memory
export LACLAUGPT_DATA_DIR=$DATA_ROOT
export TMPDIR=${{TMPDIR:-/tmp}}

python ep24_pipeline.py --country {country} --data-root "$DATA_ROOT" --repo-root "$REPO_ROOT"
"""


def write_slurm_scripts(directory: str | Path, *,
                        time_limit: str = "08:00:00") -> list[Path]:
    out = []
    for country in COUNTRIES:
        path = Path(directory) / f"ep24_full_{country}.sh"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_slurm_script(country, time_limit=time_limit), encoding="utf-8")
        out.append(path)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--country", required=True, choices=sorted(COUNTRIES))
    ap.add_argument("--data-root", default=DATA_ROOT)
    ap.add_argument("--repo-root", default=REPO_ROOT)
    ap.add_argument("--run-config", default="run_configs/arena_ep24.yaml")
    ap.add_argument("--dry-run", action="store_true", help="fetch+ASR counts only, skip LLM stages")
    args = ap.parse_args()
    status = run_country(args.country, data_root=args.data_root,
                         repo_root=args.repo_root,
                         run_config=args.run_config, dry_run=args.dry_run)
    print(json.dumps(status, ensure_ascii=False, indent=2))
