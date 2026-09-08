# -*- coding: utf-8 -*-
"""EP24 multimodal fetch stage: stream HEPP24 videos from CSC Allas.

Issue #73 phase 1.1. Fetches the unique Allas URLs from the country
manifests into $TMPDIR (or a caller-provided workdir), deduplicating by
URL: one download per video, results fanned back out to every document_id
that references the same URL downstream. Videos are never persisted to the
scratch root — use_tmpdir semantics per config/execution/slurm.yaml.

Source of truth: data/manifests/{finland,poland}_manifest.csv
(document_id, allas_url, row_count). URLs are public Swift objects
(sample verified: HTTP 200, video/mp4, no credentials required).
"""
from __future__ import annotations

import csv
import hashlib
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

ALLAS_URL_COLUMN = "allas_url"
ID_COLUMN = "document_id"

DEFAULT_CHUNK = 1 << 20  # 1 MiB


def load_manifest(manifest_path: str | Path) -> list[tuple[str, str]]:
    """Return (document_id, allas_url) pairs, one row per document."""
    pairs: list[tuple[str, str]] = []
    with open(manifest_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pairs.append((row[ID_COLUMN].strip(), row[ALLAS_URL_COLUMN].strip()))
    return pairs


def unique_urls(pairs: list[tuple[str, str]]) -> list[str]:
    """Dedup: one fetch per unique URL, order-stable."""
    seen: dict[str, None] = {}
    for _, url in pairs:
        seen.setdefault(url, None)
    return list(seen)


def _dest_for(workdir: Path, url: str) -> Path:
    # Deterministic local name: sha1 of the URL keeps fan-out mapping trivial
    # and avoids filename collisions/quoting issues from Swift keys.
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    suffix = Path(url.split("?")[0]).suffix or ".mp4"
    return workdir / f"{digest}{suffix}"


def fetch_video(url: str, workdir: Path, *, chunk: int = DEFAULT_CHUNK,
                timeout: float = 60.0, max_retries: int = 3) -> Path:
    """Stream one video into workdir; skip if already fetched (resume-safe).

    Transient network failures are retried up to `max_retries` times; only
    then does the failure surface (issue #73 phase 1.1).
    """
    dest = _dest_for(workdir, url)
    if dest.exists() and dest.stat().st_size > 0:
        return dest  # idempotent: supports job resume after preemption
    workdir.mkdir(parents=True, exist_ok=True)
    attempt = 0
    while True:
        try:
            request = urllib.request.Request(url, method="GET",
                                             headers={"User-Agent": "LaclauGPT-ep24/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response, open(dest, "wb") as fh:
                if response.status != 200:
                    raise RuntimeError(f"unexpected status {response.status} for {url}")
                while True:
                    block = response.read(chunk)
                    if not block:
                        break
                    fh.write(block)
            if dest.stat().st_size == 0:
                dest.unlink(missing_ok=True)
                raise RuntimeError(f"empty download for {url}")
            return dest
        except (urllib.error.URLError, TimeoutError) as exc:
            attempt += 1
            if dest.exists() and dest.stat().st_size == 0:
                dest.unlink(missing_ok=True)
            if attempt > max_retries:
                raise RuntimeError(
                    f"fetch failed after {max_retries} retries: {url}") from exc


def fetch_all(manifest_path: str | Path, workdir: Path, *,
              max_retries: int = 3) -> dict[str, str]:
    """Fetch every unique URL in the manifest.

    Returns {url -> local_path}. Fan-out (which document_ids share which
    URL) is already recorded in the manifest; callers use `load_manifest`
    to map results back to documents without re-reading the videos.
    """
    pairs = load_manifest(manifest_path)
    urls = unique_urls(pairs)
    fetched: dict[str, str] = {}
    for url in urls:
        dest = _dest_for(workdir, url)
        attempt = 0
        while True:
            try:
                fetch_video(url, workdir)
                fetched[url] = str(dest)
                break
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                attempt += 1
                if attempt > max_retries:
                    raise RuntimeError(
                        f"fetch failed after {max_retries} retries: {url}") from exc
                os.environ.setdefault("EP24_FETCH_RETRIES", str(max_retries))
    return fetched


def _tmpdir() -> Path:
    # use_tmpdir semantics: $TMPDIR on Slurm, ./tmp_ep24 locally.
    return Path(os.environ.get("TMPDIR", "./tmp_ep24"))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True, help="country manifest CSV")
    ap.add_argument("--workdir", default=None, help="fetch dir (default $TMPDIR)")
    args = ap.parse_args()
    workdir = Path(args.workdir) if args.workdir else _tmpdir()
    pairs = load_manifest(args.manifest)
    urls = unique_urls(pairs)
    print(f"{len(pairs)} documents -> {len(urls)} unique videos -> {workdir}")
    results = fetch_all(args.manifest, workdir)
    print(f"fetched {len(results)} videos (resume-safe, dedup by URL)")