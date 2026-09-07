# -*- coding: utf-8 -*-
"""Daily cron wrapper: run the autoscraper, then clean, then z4sync.

Installed as a Hermes cron job (see README section 'Automation') or a
plain crontab entry. Failures append to scraper.log; the study window
gate (7 Sep – 10 Oct) keeps it from running outside the collection
period.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

WINDOW = ("2026-09-07", "2026-10-10")
LOG = HERE / "scraper.log"


def log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    LOG.open("a", encoding="utf-8").write(f"[{stamp}] {msg}\n")


def in_window() -> bool:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return WINDOW[0] <= today <= WINDOW[1]


def run(cmd: list[str]) -> None:
    log("RUN " + " ".join(cmd))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        log(f"EXIT {r.returncode}")
        tail = (r.stdout or r.stderr).strip().splitlines()
        for line in tail[-10:]:
            log("  " + line)
    except Exception as exc:  # noqa: BLE001
        log(f"ERROR {exc}")


if __name__ == "__main__":
    if not in_window():
        log("outside study window — skipping")
        sys.exit(0)
    data_root = Path.home() / "laclaugpt-brasil-data"
    run(["python3", str(HERE / "autoscraper.py"),
         "--accounts", str(HERE / "accounts.yaml"),
         "--out", str(data_root / "captures")])
    run(["python3", str(HERE / "clean_captures.py"),
         str(data_root / "captures"), str(data_root / "clean")])
    # z4sync: pull finished 4CAT datasets into LaclauGPT CSV. Dataset keys
    # come from 4CAT's UI once Zeeschuimer pushes captures there; list them
    # one per line in z4sync_datasets.txt as: platform,country,language,dataset_key
    ds_file = HERE / "z4sync_datasets.txt"
    if ds_file.exists():
        for line in ds_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            platform, country, language, key = (line.split(",") + [""])[:4]
            if not (platform and key):
                log(f"bad z4sync line: {line}")
                continue
            run(["python3", str(HERE.parent / "z4sync" / "sync.py"),
                 "--fourcat", "http://localhost:4544",
                 "--dataset", key, "--platform", platform,
                 "--country", country, "--language", language,
                 "--out", str(data_root / "laclaugpt-csv" / f"{key}.csv")])
    else:
        log("no z4sync_datasets.txt — skipping 4CAT pull")
    log("daily cycle complete")