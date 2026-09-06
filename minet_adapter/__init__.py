# -*- coding: utf-8 -*-
"""minet adapter — importer/exporter over the LaclauGPT interchange schema.

minet (medialab/minet, médialab Sciences Po) is the webmining CLI/library:
fetch, extract (trafilatura), scrape, resolve, url-* plus platform
collectors (Bluesky, Facebook, Mediacloud, Reddit, Telegram, TikTok,
Twitter/X, YouTube, Wikipedia...). It sits in LaclauGPT's DATA COLLECTION
tier — the same tier as Zeeschuimer/4CAT — but is CSV-centric and
low-tech: "raw CSV files should be sufficient".

minet's canonical outputs are CSVs:

  minet fetch url -i urls.csv > report.csv
      adds: resolved_url, http_status, datetime_utc, fetch_error, path,
            mimetype, encoding, body_size [, body with -c]
  minet extract -i report.csv -I downloaded > extracted.csv
      adds: canonical_url, title, description, content, comments, author,
            categories, tags, date, sitename, image, pagetype

Mappings (minet CSV <-> LaclauGPT):

  minet                              LaclauGPT pipeline row
  ---------------------------------  --------------------------------
  content (trafilatura main text)    content (SOURCE_TEXT_FIELDS hit;
                                       pipeline reads it natively)
  title                              title
  author                             author
  date                               created_at
  sitename                           source (site name)
  canonical_url / resolved_url / url url
  (constant)                         platform = "minet-<collector>"

Import (minet -> LaclauGPT):
  - ``import_minet_extract``: an extract CSV (or the fetch report piped
    through extract) -> analysis-ready rows. `content` is the source text;
    pipeline.py reads it natively (SOURCE_TEXT_FIELDS). Failed/empty
    extractions (fetch_error/extract_error, empty content) are skipped
    with counts.
  - ``import_minet_csv``: generic collector CSVs (twitter/youtube/...):
    text-ish columns are detected among the collector's known text
    columns, metadata rides along.

Export (LaclauGPT -> minet):
  - ``export_fetch_urls``: interchange JSONL -> urls.csv ready for
    ``minet fetch url -i urls.csv`` (re-fetch provenance, redirect checks)
  - ``export_report_urls``: a minet fetch/extract report -> a deduped
    urls.csv for further minet runs (resolve/scrape/crawl chaining)

No new dependencies: minet itself is NOT required for these converters —
they only read/write the CSVs minet produces (the adapter is usable on
machines without minet; run minet separately as the CLI it is).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from laclaugpt_interchange import from_jsonl

# minet extract output columns (trafilatura-backed) — the import target.
_MINET_EXTRACT_TEXT = "content"
_MINET_EXTRACT_FIELDS = {
    "title": "title",
    "author": "author",
    "date": "created_at",
    "sitename": "source",
}

# text-ish columns produced by minet's platform collectors (subset; the
# adapter probes these in order and uses the first non-empty one).
_COLLECTOR_TEXT_COLUMNS = (
    "text", "tweet", "full_text", "content", "title", "description",
    "selftext", "body", "message", "caption", "comment", "summary",
)


def _read_csv(path_or_path_column: str) -> list[dict]:
    if path_or_path_column in {"-", "/dev/stdin"}:
        return list(csv.DictReader(sys.stdin))
    with open(path_or_path_column, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# Import: minet -> LaclauGPT
# ---------------------------------------------------------------------------

def import_minet_extract(csv_path: str, text_column: str | None = None,
                         url_column: str | None = None,
                         author_column: str | None = None,
                         timestamp_column: str | None = None,
                         keep_unmapped: bool = True) -> tuple[list[dict], dict]:
    """minet extract CSV -> LaclauGPT analysis-ready rows (spec §12).

    Returns (rows, stats). Each row maps onto pipeline.py's conventions:
    id/text/title/author/created_at/source/url + source_platform. Rows
    with a fetch/extract error or empty content are skipped and counted,
    never analysed (empty-source rows fail fast in the pipeline).

    Column overrides follow the spec's CLI contract:
        --text-column --url-column --author-column --timestamp-column

    Per spec §12, all unmapped minet fields are preserved in
    row["external_metadata"]["minet"] (keep_unmapped=True by default).
    """
    rows_in = _read_csv(csv_path)
    rows: list[dict] = []
    skipped_errors = skipped_empty = 0
    mapped = set(_MINET_EXTRACT_FIELDS) | {
        _MINET_EXTRACT_TEXT, "fetch_error", "extract_error",
        "canonical_url", "resolved_url", "url", "extract_original_index",
    }
    if text_column:
        mapped.add(text_column)
    for i, item in enumerate(rows_in):
        text = (item.get(text_column or _MINET_EXTRACT_TEXT) or "").strip()
        fetch_err = (item.get("fetch_error") or "").strip()
        extract_err = (item.get("extract_error") or "").strip()
        if fetch_err:
            skipped_errors += 1
            continue
        if not text:
            # extract-level failure (no content) vs genuinely empty page —
            # both are unanalysable; count them distinctly for the report
            skipped_errors += 1 if extract_err else 0
            skipped_empty += 0 if extract_err else 1
            continue
        url = (item.get(url_column or "") or item.get("canonical_url")
               or item.get("resolved_url") or item.get("url") or "").strip()
        author = (item.get(author_column or "") or item.get("author")
                  or "").strip()
        created = (item.get(timestamp_column or "") or item.get("date")
                   or "").strip()
        row = {
            "id": str(item.get("extract_original_index") or i),
            "text": text,
            "url": url,
            # LaclauGPT-exported provenance stamp; pure minet reports as
            # "minet-extract".
            "source_platform": "minet-extract",
        }
        if author:
            row["author"] = author
        if created:
            row["created_at"] = created
        for src, dst in _MINET_EXTRACT_FIELDS.items():
            if dst in row or (src == "author" and author_column) \
                    or (src == "date" and timestamp_column):
                continue
            value = (item.get(src) or "").strip()
            if value:
                row[dst] = value
        if keep_unmapped:
            external = {k: v for k, v in item.items()
                        if k not in mapped and (v or "").strip()}
            if external:
                row["external_metadata"] = {"minet": external}
        rows.append(row)
    stats = {"input": len(rows_in), "imported": len(rows),
             "skipped_errors": skipped_errors, "skipped_empty": skipped_empty}
    return rows, stats


def import_minet_collector(csv_path: str, platform: str,
                           text_column: str | None = None) -> tuple[list[dict], dict]:
    """Generic minet collector CSV (twitter/youtube/telegram/...) -> rows.

    text_column forces one column; otherwise the adapter probes the known
    collector text columns in order per row. Rows whose detected text is
    empty are skipped and counted.
    """
    rows_in = _read_csv(csv_path)
    rows: list[dict] = []
    skipped_empty = 0
    probe = (text_column,) if text_column else _COLLECTOR_TEXT_COLUMNS
    for i, item in enumerate(rows_in):
        text = ""
        used = ""
        for col in probe:
            value = (item.get(col) or "").strip()
            if value:
                text, used = value, col
                break
        if not text:
            skipped_empty += 1
            continue
        doc_id = (item.get("id") or item.get("tweet_id") or item.get("video_id")
                  or item.get("data_id") or item.get("normalized_url")
                  or item.get("url") or str(i))
        row = {
            "id": str(item.get("id") or i),
            "text": text,
            "text_column": used,
            "platform": platform,
            "source_platform": f"minet-{platform}",
        }
        for src, dst in (("created_at", "created_at"), ("date", "created_at"),
                         ("time", "created_at"), ("user_screen_name", "author"),
                         ("username", "author"), ("channel", "author"),
                         ("url", "url"), ("link", "url")):
            value = (item.get(src) or "").strip()
            if value and dst not in row:
                row[dst] = value
        rows.append(row)
    stats = {"input": len(rows_in), "imported": len(rows),
             "skipped_empty": skipped_empty, "text_column": text_column or "auto"}
    return rows, stats


def write_analysis_csv(rows: list[dict], out_path: str) -> int:
    """Write imported rows as the pipeline's analysis input CSV.

    The pipeline reads source text via SOURCE_TEXT_FIELDS, which includes
    ``content`` — the column name minet's extract produces. Imported rows
    keep their ``text`` key internally; here it is also written as
    ``content`` so the CSV feeds the pipeline without renaming.
    """
    pipeline_rows = []
    for row in rows:
        out = dict(row)
        if "text" in out and "content" not in out:
            out["content"] = out["text"]
        pipeline_rows.append(out)
    rows = pipeline_rows
    if not rows:
        with open(out_path, "w", encoding="utf-8", newline="") as fh:
            fh.write("id,content\n")
        return 0
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames,
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Export: LaclauGPT -> minet
# ---------------------------------------------------------------------------

def export_fetch_urls(annotations_path: str, out_path: str,
                      url_field: str = "source_url") -> int:
    """Interchange JSONL -> minet fetch input CSV (urls.csv).

    One row per document carrying a URL, so annotations can be re-fetched,
    redirect-checked and re-extracted with minet:
        minet fetch url -i urls.csv -O downloaded > report.csv
        minet extract -i report.csv -I downloaded > refreshed.csv
    """
    count = 0
    seen: set[str] = set()
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["url", "document_id"])
        for ann in from_jsonl(annotations_path):
            url = (getattr(ann, url_field, "") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            writer.writerow([url, ann.document_id])
            count += 1
    return count


def export_report_urls(report_csv: str, out_path: str,
                       url_column: str = "resolved_url") -> int:
    """A minet fetch report -> deduped urls.csv for further minet runs.

    Keeps only successfully fetched, non-empty URLs (http_status 200 by
    default when the column exists), so downstream minet resolve/scrape
    runs don't retry dead links.
    """
    rows = _read_csv(report_csv)
    count = 0
    seen: set[str] = set()
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["url"])
        for item in rows:
            url = (item.get(url_column) or "").strip()
            status = (item.get("http_status") or "").strip()
            if not url or url in seen:
                continue
            if status and status != "200":
                continue
            seen.add(url)
            writer.writerow([url])
            count += 1
    return count
