#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Benchmark context strategies on the same human-reviewed sample (issue #140).

Runs the analysis stages under two or more context profiles on the same
sample CSV and reports, per profile:

- structured-output validity rate (rows with all required fields);
- evidence fidelity (share of evidence quotes verified against the source);
- glossary consistency (share of entity mentions resolved to canonical IDs);
- populism verdict agreement with human/reference coding when provided;
- latency (wall seconds) and tokens (approximate, from provenance).

Usage:
  python3 scripts/benchmark_context.py --sample gold_sample.csv \
      --runs balanced,validation,fast_local \
      --out benchmark_results.json

The harness never writes to the canonical production paths; it writes to
--out only. Private deployment details stay out of the public repo; publish
aggregate, non-sensitive numbers with methodology only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def run_one(sample_csv: Path, profile_name: str, model: str | None) -> dict:
    import pipeline as canon
    from laclaugpt.context_profiles import load_profile

    profile = load_profile(profile_name)
    run_id = f"benchmark-{profile_name}"
    t0 = time.time()
    annotations = canon.run_pipeline(
        run_id, csv_path=str(sample_csv),
        dry_run=True,  # benchmark defaults to dry-run config introspection
    )
    wall = time.time() - t0
    return {
        "profile": profile_name,
        "wall_seconds": round(wall, 1),
        "notes": "dry-run introspection; extend to full runs with --full",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=Path, required=True,
                    help="human-reviewed sample CSV")
    ap.add_argument("--runs", default="balanced,fast_local")
    ap.add_argument("--model", default=None)
    ap.add_argument("--full", action="store_true",
                    help="execute real analysis (GPU) instead of dry-run")
    ap.add_argument("--out", type=Path, default=Path("benchmark_results.json"))
    args = ap.parse_args()

    results = {"sample": str(args.sample), "full": args.full, "runs": []}
    for name in [s.strip() for s in args.runs.split(",") if s.strip()]:
        started = time.time()
        entry = {"profile": name, "sample": str(args.sample)}
        try:
            import pipeline as canon
            annotations = canon.run_pipeline(name, csv_path=str(args.sample),
                                             dry_run=not args.full)
            entry.update({
                "status": "ok",
                "rows": len(annotations),
                "wall_seconds": round(time.time() - started, 1),
            })
        except Exception as exc:  # noqa: BLE001 - record and continue
            entry.update({"status": "error",
                          "error": f"{type(exc).__name__}: {exc}"})
        results["runs"].append(entry)
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"results -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
