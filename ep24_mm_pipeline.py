# -*- coding: utf-8 -*-
"""EP24 Roihu SAMPLE multimodal pipeline — one command, whole chain.

Issue #73 phase-1 pilot: 20+20 Finnish/Polish videos through
  fetch (Allas -> scratch videos/) ->
  ASR (faster-whisper large-v3, vad_filter on GPU) ->
  screen-metadata OCR (poster @handle etc. from keyframes) ->
  canonical CSV join (transcript = source text; legacy columns only as
  identity metadata) ->
  LLM stages (summary/discourse/populism/postprocess via Ollama Cloud) ->
  dual-format exports (annotations.jsonl + .csv + .report.md).

Runs INSIDE a SLURM GPU job (see sbatch scripts). The OCR model (paddle/
tesseract-class) is lazy-imported so CPU-only test runs can mock it.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import ep24_asr
import ep24_fetch
import ep24_screen_metadata

REPO_ROOT = "/users/totoivio/LaclauGPT-Discourse-Analysis"
DATA_ROOT = "/scratch/project_2009497/laclaugpt2"

COUNTRIES = {
    "finland": {"manifest": "finland_sample20.csv", "codebook": "ep24_finland",
                "topic_key": "ep24-finland", "country_code": "FI"},
    "poland": {"manifest": "poland_sample20.csv", "codebook": "ep24_poland",
               "topic_key": "ep24-poland", "country_code": "PL"},
}


def paths(country: str, *, data_root: str = DATA_ROOT,
          repo_root: str = REPO_ROOT) -> dict[str, Path]:
    base = Path(data_root)
    cfg = COUNTRIES[country]
    return {
        "repo_root": Path(repo_root),
        "manifest": base / "ep24" / "csv" / cfg["manifest"],
        "legacy_csv": base / "ep24" / "csv" / f"ep24_{country}.csv",
        "videos": base / "ep24" / "videos",
        "transcripts": base / "ep24" / "annotations" / f"{country}_sample20_transcripts.jsonl",
        "canonical_csv": base / "ep24" / "csv" / f"ep24_{country}_sample20_canonical.csv",
        "annotations": base / "ep24" / "annotations" / f"{country}_sample20_annotations.jsonl",
    }


def ocr_video_frames(video_path: Path, *, max_frames: int = 3) -> str:
    """OCR a few keyframes of one video for screen-metadata lifting.

    Uses the keyframes module convention (duration/6, >=10 s gap — here
    capped to max_frames for the sample run). Lazy import: OCR backends
    (paddleocr / pytesseract) are Roihu module installs; CPU tests mock
    this function.
    """
    import ep24_keyframes  # noqa: F401  (module expected on Roihu)
    frames = ep24_keyframes.extract_keyframes(str(video_path), max_frames=max_frames)
    texts = []
    for frame in frames:
        try:
            import ep24_ocr  # OCR backend wrapper on Roihu
            texts.append(ep24_ocr.ocr_image(frame))
        except ImportError:  # OCR module unavailable -> skip frame
            continue
    return "\n".join(t for t in texts if t)


def run_country(country: str, *, data_root: str = DATA_ROOT,
                repo_root: str = REPO_ROOT, run_config: str | None = None,
                model_size: str = ep24_asr.DEFAULT_MODEL, model=None,
                ocr_fn=ocr_video_frames) -> dict:
    """Whole chain for one country inside the SLURM job."""
    p = paths(country, data_root=data_root, repo_root=repo_root)
    status: dict = {"country": country}

    # 1. fetch (resume-safe)
    fetched = ep24_fetch.fetch_all(p["manifest"], p["videos"])
    status["fetched"] = len(fetched)

    # 2. ASR (resume-safe JSONL, GPU)
    n = ep24_asr.transcribe_manifest(p["manifest"], p["videos"],
                                     p["transcripts"], model_size=model_size,
                                     model=model)
    status["transcribed"] = n

    # 3. screen-metadata OCR pass: enrich transcripts with UI identity
    enriched = 0
    transcripts = _load_jsonl(p["transcripts"])
    for rec in transcripts:
        if rec.get("screen_ocr"):
            continue  # resume-safe
        video = ep24_fetch._dest_for(Path(p["videos"]), rec["allas_url"])
        if not video.exists():
            continue
        rec["screen_ocr"] = ocr_fn(video)
        enriched += 1
    _write_jsonl(p["transcripts"], transcripts)
    status["ocr_enriched"] = enriched

    # 4. canonical CSV join (identity from legacy roster, text from ASR)
    from ep24_pipeline import build_canonical_csv
    written = build_canonical_csv(p["manifest"], p["transcripts"],
                                  p["legacy_csv"], p["canonical_csv"])
    status["canonical_rows"] = written

    # 5. LLM stages via Ollama Cloud
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


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _slurm_script(country: str, *, time_limit: str = "08:00:00") -> str:
    return f"""#!/bin/bash
#SBATCH --job-name=ep24_mm_{country}
#SBATCH --partition=gpu
#SBATCH --time={time_limit}
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gpus=1
#SBATCH --output=ep24_mm_{country}_%j.out

set -euo pipefail
REPO_ROOT={REPO_ROOT}
DATA_ROOT={DATA_ROOT}
cd "$REPO_ROOT"

# Scratch layout (issue #73): csv/, videos/, annotations/, memory/
export LACLAUGPT_MEMORY_DIR=$DATA_ROOT/memory
export LACLAUGPT_DATA_DIR=$DATA_ROOT
export TMPDIR=${{TMPDIR:-/tmp}}

# faster-whisper + OCR deps live in the Roihu module/venv; the LLM stages
# talk to Ollama Cloud (gemma4:31b-cloud) — no local model server needed.
python ep24_mm_pipeline.py --country {country} \\
    --data-root "$DATA_ROOT" --repo-root "$REPO_ROOT"
"""


def write_slurm_scripts(directory: str | Path, *,
                        time_limit: str = "08:00:00") -> list[Path]:
    out = []
    for country in COUNTRIES:
        path = Path(directory) / f"ep24_mm_{country}.sh"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_slurm_script(country, time_limit=time_limit),
                        encoding="utf-8")
        out.append(path)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--country", required=True, choices=sorted(COUNTRIES))
    ap.add_argument("--data-root", default=DATA_ROOT)
    ap.add_argument("--repo-root", default=REPO_ROOT)
    ap.add_argument("--run-config", default=None)
    ap.add_argument("--model", default=ep24_asr.DEFAULT_MODEL)
    args = ap.parse_args()
    t0 = time.time()
    status = run_country(args.country, data_root=args.data_root,
                         repo_root=args.repo_root, run_config=args.run_config,
                         model_size=args.model)
    status["wall_seconds"] = round(time.time() - t0, 1)
    print(json.dumps(status, ensure_ascii=False, indent=2))