# -*- coding: utf-8 -*-
"""EP24 full-country reprocessing pipeline (Finland + Poland).

Issue #73 follow-up: reprocess the full Finnish and Polish EP24 samples with
the canonical LaclauGPT pipeline. Repository and research-data roots are supplied
through runtime configuration rather than embedded machine/user paths.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import legacy_asr
import legacy_fetch

REPO_ROOT = os.environ.get("LACLAUGPT_REPO_ROOT", str(Path(__file__).resolve().parent))
DATA_ROOT = os.environ.get("LACLAUGPT_DATA_DIR", str(Path(__file__).resolve().parent / "data"))

COUNTRIES = {
    "finland": {"manifest": "finland_manifest.csv", "legacy": "ep24_finland.csv",
                "language": "fi"},
    "poland": {"manifest": "poland_manifest.csv", "legacy": "ep24_poland.csv",
               "language": "pl"},
}


def paths(country: str, *, data_root: str = DATA_ROOT,
          repo_root: str = REPO_ROOT) -> dict[str, Path]:
    base = Path(data_root)
    cfg = COUNTRIES[country]
    return {
        "repo_root": Path(repo_root),
        "manifest": base / "ep24" / "csv" / cfg["manifest"],
        "legacy_csv": base / "ep24" / "csv" / cfg["legacy"],
        "videos": base / "ep24" / "videos",
        "transcripts": base / "ep24" / "annotations" / f"{country}_full_transcripts.jsonl",
        "canonical_csv": base / "ep24" / "csv" / f"ep24_{country}_full_canonical.csv",
        "annotations": base / "ep24" / "annotations" / f"{country}_full_annotations.jsonl",
    }


def run_country(country: str, *, data_root: str = DATA_ROOT,
                repo_root: str = REPO_ROOT, run_config: str | None = None,
                model_size: str = legacy_asr.DEFAULT_MODEL, model=None,
                dry_run: bool = False) -> dict:
    p = paths(country, data_root=data_root, repo_root=repo_root)
    status: dict = {"country": country}
    fetched = legacy_fetch.fetch_all(p["manifest"], p["videos"])
    status["fetched"] = len(fetched)
    if dry_run:
        status["dry_run"] = True
        return status

    n = legacy_asr.transcribe_manifest(p["manifest"], p["videos"],
                                     p["transcripts"], model_size=model_size,
                                     model=model)
    status["transcribed"] = n

    from legacy_pipeline import build_canonical_csv
    written = build_canonical_csv(p["manifest"], p["transcripts"],
                                  p["legacy_csv"], p["canonical_csv"])
    status["canonical_rows"] = written

    if not run_config:
        run_config = str(Path(repo_root) / "run_configs" /
                         "arena_ep24_roihu_sample.yaml")
    import pipeline as canon
    annotations = canon.run_pipeline(
        run_config,
        csv_path=str(p["canonical_csv"]),
        output_path=str(p["annotations"]),
    )
    status["annotated"] = len(annotations)
    return status


def _slurm_script(country: str, *, time_limit: str = "48:00:00",
                  partition: str = "gpumedium") -> str:
    return f"""#!/bin/bash
#SBATCH --job-name=ep24_full_{country}
#SBATCH --partition={partition}
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

module load python-pytorch/2.10
module load ffmpeg

export LACLAUGPT_MEMORY_DIR=$DATA_ROOT/memory
export LACLAUGPT_DATA_DIR=$DATA_ROOT
export TMPDIR=${{TMPDIR:-/tmp}}

python ep24_full_pipeline.py --country {country} \\
    --data-root "$DATA_ROOT" --repo-root "$REPO_ROOT"
"""


def write_slurm_scripts(directory: str | Path, *,
                        time_limit: str = "48:00:00",
                        partition: str = "gpumedium") -> list[Path]:
    out = []
    for country in COUNTRIES:
        path = Path(directory) / f"ep24_full_{country}.sh"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_slurm_script(country, time_limit=time_limit,
                                      partition=partition), encoding="utf-8")
        out.append(path)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--country", required=True, choices=sorted(COUNTRIES))
    ap.add_argument("--data-root", default=DATA_ROOT)
    ap.add_argument("--repo-root", default=REPO_ROOT)
    ap.add_argument("--run-config", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch counts only, skip ASR + LLM stages")
    args = ap.parse_args()
    status = run_country(args.country, data_root=args.data_root,
                         repo_root=args.repo_root,
                         run_config=args.run_config, dry_run=args.dry_run)
    print(json.dumps(status, ensure_ascii=False, indent=2))


if os.environ.get("EP24_OFFLINE_TEST") == "1":  # pragma: no cover
    pass
