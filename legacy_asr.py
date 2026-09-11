# -*- coding: utf-8 -*-
"""EP24 ASR stage: faster-whisper large-v3 transcripts for fetched videos.

Issue #73 phase 1.2. Re-derives transcripts from the videos fetched by
`legacy_fetch` (never the legacy `whisper_transcript` columns — those are
outputs of the old Puhti run and ride only as provenance metadata).

Model lessons baked in (recorded 2026-09-06/08 sessions):
- faster-whisper large-v3 supersedes the old Puhti whisper run
- vad_filter=True kills music hallucinations (intro/outro jingles in the
  HEPP24 corpus produced phantom transcripts in v1)
- per-document output JSONL keeps provenance: model, version, fetch time

Paths come from runtime configuration: videos stream to $TMPDIR via legacy_fetch;
transcripts land under the configured data root.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

DEFAULT_MODEL = "large-v3"
DEFAULT_DEVICE = "auto"
DEFAULT_COMPUTE = "auto"
TRANSCRIPT_VERSION = "ep24-asr-1.0"


def transcript_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def transcribe_video(video_path: str | Path, *, model_size: str = DEFAULT_MODEL,
                     device: str = DEFAULT_DEVICE, compute_type: str = DEFAULT_COMPUTE,
                     language: str | None = None, model=None):
    if model is None:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        str(video_path), vad_filter=True, language=language,
    )
    parts = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            parts.append(text)
    return {
        "transcript": " ".join(parts),
        "language": info.language,
        "language_probability": round(float(info.language_probability), 4),
        "duration": round(float(info.duration), 2),
    }


def transcribe_manifest(manifest_path: str | Path, videos_dir: str | Path,
                        out_path: str | Path, *, model_size: str = DEFAULT_MODEL,
                        device: str = DEFAULT_DEVICE, compute_type: str = DEFAULT_COMPUTE,
                        model=None) -> int:
    import legacy_fetch

    pairs = legacy_fetch.load_manifest(manifest_path)
    videos_dir = Path(videos_dir)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    done: set[str] = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    done.add(json.loads(line).get("document_id", ""))
    done.discard("")

    written = 0
    with open(out_path, "a", encoding="utf-8") as out:
        for doc_id, url in pairs:
            if doc_id in done:
                continue
            video = legacy_fetch._dest_for(Path(videos_dir), url)
            if not video.exists():
                raise FileNotFoundError(f"video for {doc_id} not fetched: expected {video}")
            result = transcribe_video(video, model_size=model_size,
                                      device=device, compute_type=compute_type,
                                      model=model)
            record = {
                "document_id": doc_id,
                "allas_url": url,
                "transcript_version": TRANSCRIPT_VERSION,
                "model": model_size if model is None else getattr(model, "model_size_or_path", model_size),
                "vad_filter": True,
                "fetched_from": "allas",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                **result,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    return written


def _slurm_header(job_name: str, time_limit: str, manifest: str,
                  country: str) -> str:
    return f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition=gpu
#SBATCH --time={time_limit}
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gpus=1
#SBATCH --output=legacy_asr_%j.out

set -euo pipefail
: "${{LACLAUGPT_REPO_ROOT:?set LACLAUGPT_REPO_ROOT to the checked-out repository}}"
: "${{LACLAUGPT_DATA_DIR:?set LACLAUGPT_DATA_DIR to the controlled research-data root}}"
REPO_ROOT=$LACLAUGPT_REPO_ROOT
DATA_ROOT=$LACLAUGPT_DATA_DIR
cd "$REPO_ROOT"

export LACLAUGPT_MEMORY_DIR=$DATA_ROOT/memory
export TMPDIR=${{TMPDIR:-/tmp}}
python legacy_fetch.py --manifest "$DATA_ROOT/ep24/csv/{manifest}" --workdir "$DATA_ROOT/ep24/videos"
python legacy_asr.py --manifest "$DATA_ROOT/ep24/csv/{manifest}" \\
    --videos-dir "$DATA_ROOT/ep24/videos" \\
    --out "$DATA_ROOT/ep24/annotations/{country}_transcripts.jsonl"
"""


def write_slurm_script(path: str | Path, country: str, *,
                       time_limit: str = "04:00:00") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = f"{country}_manifest.csv"
    path.write_text(_slurm_header(f"legacy_asr_{country}", time_limit, manifest, country),
                    encoding="utf-8")
    return path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--videos-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--device", default=DEFAULT_DEVICE)
    ap.add_argument("--compute-type", default=DEFAULT_COMPUTE)
    args = ap.parse_args()
    n = transcribe_manifest(args.manifest, args.videos_dir, args.out,
                            model_size=args.model, device=args.device,
                            compute_type=args.compute_type)
    print(f"transcribed {n} documents -> {args.out}")
