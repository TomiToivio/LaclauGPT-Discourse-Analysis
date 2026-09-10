#!/usr/bin/env python3
"""Prepare evidence-only Finland/Poland EP24 inputs for a fresh LaclauGPT run."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

COUNTRIES = {"finland": "Finland", "poland": "Poland"}
OCR_FIELDS = tuple(f"ocr_{index}" for index in range(1, 7))
OUTPUT_FIELDS = (
    "document_id", "transcript", "ocr_text", "country", "language", "platform",
    "author_username", "timestamp", "political_preference", "account_type",
    "source_type", "source_url", "video_file", "allas_filename", "source_row_count",
    "transcript_variant_count", "source_dataset",
)


def _clean(value: object) -> str:
    text = "" if value is None else str(value).strip()
    return "" if text.casefold() in {"nan", "none"} else text


def _document_id(row: dict[str, str], row_number: int) -> str:
    for field in ("new_id", "video_id", "old_id"):
        if value := _clean(row.get(field)):
            return value
    return f"ep24-row-{row_number}"


def _richness(row: dict[str, str]) -> tuple[int, int]:
    transcript = _clean(row.get("whisper_transcript"))
    populated = sum(bool(_clean(value)) for value in row.values())
    return len(transcript), populated


def prepare(source: Path, destination: Path, country_key: str,
            sample_size: int = 0) -> dict[str, int | str]:
    country = COUNTRIES[country_key]
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"country", "whisper_transcript"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"input CSV is missing required columns: {sorted(missing)}")
        for row_number, row in enumerate(reader, start=2):
            if _clean(row.get("country")) == country:
                grouped[_document_id(row, row_number)].append(row)

    records = []
    empty = 0
    conflicts = 0
    for document_id in sorted(grouped):
        rows = grouped[document_id]
        best = max(rows, key=_richness)
        transcripts = {
            _clean(row.get("whisper_transcript")) for row in rows
            if _clean(row.get("whisper_transcript"))
        }
        if not transcripts:
            empty += 1
            continue
        conflicts += int(len(transcripts) > 1)
        transcript = max(transcripts, key=lambda value: (len(value), value))
        ocr_values = []
        for row in rows:
            for field in OCR_FIELDS:
                value = _clean(row.get(field))
                if value and value not in ocr_values:
                    ocr_values.append(value)
        records.append({
            "document_id": document_id,
            "transcript": transcript,
            "ocr_text": "\n".join(ocr_values),
            "country": country,
            "language": _clean(best.get("whisper_language")),
            "platform": _clean(best.get("source_type")),
            "author_username": _clean(best.get("author_username")),
            "timestamp": (_clean(best.get("recording_datetime"))
                          or _clean(best.get("corrected_date"))
                          or _clean(best.get("recording_date"))),
            "political_preference": _clean(best.get("political_preference")),
            "account_type": _clean(best.get("account_type")),
            "source_type": _clean(best.get("source_type")),
            "source_url": _clean(best.get("source_recording")),
            "video_file": _clean(best.get("video_file")),
            "allas_filename": _clean(best.get("allas_filename")),
            "source_row_count": len(rows),
            "transcript_variant_count": len(transcripts),
            "source_dataset": source.name,
        })

    if sample_size:
        records = records[:sample_size]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    return {
        "country": country,
        "source_rows": sum(map(len, grouped.values())),
        "unique_documents": len(grouped),
        "written_documents": len(records),
        "empty_transcript_documents": empty,
        "conflicting_transcript_documents": conflicts,
        "output": str(destination),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--country", required=True, choices=sorted(COUNTRIES))
    parser.add_argument("--sample-size", type=int, default=0,
                        help="deterministic document limit; 0 means the full country subset")
    args = parser.parse_args()
    if args.sample_size < 0:
        parser.error("--sample-size must be zero or positive")
    print(json.dumps(prepare(args.source, args.destination, args.country,
                             args.sample_size), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
