#!/usr/bin/env python3
"""Brasil26 media maintainer: TikTok recovery plus X/Instagram media pass.

The repository root and data root are runtime configuration. No concrete host,
network endpoint or deployment path is embedded in this public module.
"""
import glob
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("LACLAUGPT_ROOT", str(Path(__file__).resolve().parents[1]))).expanduser().resolve()
sys.path.insert(0, str(REPO))
from collector.store import Store  # noqa: E402
from collector.media import MediaDownloader  # noqa: E402

DATA_ROOT = os.path.expanduser(os.environ.get("BRAZIL26_DATA_ROOT", "~/laclaugpt-brasil-data"))
DB = os.path.join(DATA_ROOT, "state.sqlite3")
MEDIA_DIR = os.path.join(DATA_ROOT, "media", "tiktok_pyktok")
os.makedirs(MEDIA_DIR, exist_ok=True)


def media_pass():
    store = Store(DATA_ROOT)
    records = []
    for path in sorted(glob.glob(os.path.join(DATA_ROOT, "normalized", "*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            records.extend(json.loads(line) for line in fh if line.strip())
    dl = MediaDownloader(store, workers=6)
    jobs = dl.enqueue_from_records(records)
    if not jobs:
        print("media pass: nothing pending", flush=True)
        return
    results = dl.run_queue(jobs)
    from collections import Counter
    c = Counter(r.get("status") for r in results)
    print(f"media pass: {dict(c)}", flush=True)
    store.close()


def pyktok_recovery():
    os.chdir(MEDIA_DIR)
    import pyktok as pyk  # noqa: E402
    conn = sqlite3.connect(DB)
    failed_ids = {r[0] for r in conn.execute(
        "SELECT DISTINCT document_id FROM media_index WHERE platform='tiktok' AND status='failed'")}
    conn.close()
    page_urls = {}
    for f in glob.glob(os.path.join(DATA_ROOT, "normalized", "tiktok.jsonl")):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if r.get("document_id") in failed_ids and r.get("source_url", "").startswith("https://www.tiktok.com/"):
                page_urls[r["document_id"]] = r["source_url"]
    if not page_urls:
        print("pyktok recovery: no backlog", flush=True)
        return
    print(f"pyktok recovery: {len(page_urls)} docs", flush=True)
    ok = failed = 0
    for i, (doc_id, url) in enumerate(sorted(page_urls.items()), 1):
        try:
            before = set(os.listdir("."))
            pyk.save_tiktok(url, save_video=True,
                            metadata_fn="tiktok_pyktok_meta.csv")
            time.sleep(2)
            new = [f for f in os.listdir(".") if f not in before and f.endswith(".mp4")]
            if new:
                sha = hashlib.sha256(open(new[0], "rb").read()).hexdigest()
                size = os.path.getsize(new[0])
                conn = sqlite3.connect(DB)
                conn.execute(
                    """UPDATE media_index SET status='ok', local_path=?, sha256=?,
                       byte_size=?, mime_type='video/mp4',
                       downloaded_at=CURRENT_TIMESTAMP, failure_reason='',
                       http_status=200
                       WHERE document_id=? AND platform='tiktok' AND status='failed'""",
                    (new[0], sha, size, doc_id))
                conn.commit()
                conn.close()
                ok += 1
                print(f"[{i}/{len(page_urls)}] OK {doc_id}", flush=True)
            else:
                failed += 1
                print(f"[{i}/{len(page_urls)}] metadata-only {doc_id}", flush=True)
        except Exception as e:
            failed += 1
            print(f"[{i}/{len(page_urls)}] FAIL {doc_id}: {str(e)[:70]}", flush=True)
            time.sleep(3)
    print(f"pyktok recovery done: {ok} ok, {failed} failed", flush=True)


if __name__ == "__main__":
    media_pass()
    pyktok_recovery()
