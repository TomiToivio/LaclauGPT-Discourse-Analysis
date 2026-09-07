"""4CAT and Zeeschuimer corpus interchange plus canonical 4CAT execution."""
from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable

from laclaugpt.identity import normalize_url, source_identity
from laclaugpt.model import SourceItem


_TEXT_FIELDS = ("text", "body", "content", "caption", "description", "transcript")


def _source(row: dict[str, Any], platform: str | None = None) -> SourceItem:
    url = row.get("url") or row.get("source_url") or row.get("link")
    native_id = str(row.get("id") or row.get("post_id") or row.get("videoId") or "") or None
    platform = platform or row.get("platform") or row.get("source_platform")
    return SourceItem(
        source_id=source_identity(url=url, platform=platform, native_id=native_id),
        source_url=url, normalized_source_url=normalize_url(url) if url else None,
        platform=platform, source_type=row.get("source_type") or "post",
        native_id=native_id, author_text=row.get("author") or row.get("username"),
        raw_text=row.get("text") or row.get("body") or row.get("caption") or row.get("description"),
        metadata={"external": {"4cat": row}},
    )


def import_fourcat(path: str | Path, platform: str | None = None) -> list[SourceItem]:
    path = Path(path)
    if path.suffix.casefold() in {".json", ".jsonl", ".ndjson"}:
        content = path.read_text(encoding="utf-8-sig")
        rows = json.loads(content) if path.suffix.casefold() == ".json" else [json.loads(x) for x in content.splitlines() if x.strip()]
    else:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    return [_source(row, platform) for row in rows]


def import_zeeschuimer_ndjson(path: str | Path) -> list[SourceItem]:
    return import_fourcat(path)


def import_zeeschuimer_csv(path: str | Path) -> list[SourceItem]:
    return import_fourcat(path)


def export_fourcat(items: Iterable[SourceItem], path: str | Path,
                   analysis: dict[str, dict[str, Any]] | None = None) -> int:
    analysis = analysis or {}
    fields = ["id", "url", "platform", "author", "text", "timestamp",
              "laclaugpt_topics", "laclaugpt_entities", "laclaugpt_sentiment",
              "laclaugpt_discourses", "laclaugpt_signifiers", "laclaugpt_us",
              "laclaugpt_frontier", "laclaugpt_affects"]
    rows = []
    for item in items:
        extra = analysis.get(item.source_id, {})
        row = {"id": item.native_id or item.source_id, "url": item.source_url,
               "platform": item.platform, "author": item.author_text,
               "text": item.raw_text,
               "timestamp": item.published_at.isoformat() if item.published_at else None}
        for field in fields[6:]:
            value = extra.get(field.removeprefix("laclaugpt_"), [])
            row[field] = json.dumps(value, ensure_ascii=False)
        rows.append(row)
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    return len(rows)


def normalize_fourcat_rows(rows: Iterable[dict[str, Any]], *,
                           default_platform: str = "",
                           default_language: str = "") -> list[dict[str, Any]]:
    """Normalize only the 4CAT boundary fields needed by the shared pipeline.

    Original row fields are preserved. Rows without analysable text are skipped,
    matching the historical processor's behaviour before canonical dispatch.
    """
    normalized: list[dict[str, Any]] = []
    for index, original in enumerate(rows, start=1):
        row = dict(original)
        body = next((str(row.get(field) or "").strip()
                     for field in _TEXT_FIELDS if str(row.get(field) or "").strip()), "")
        if not body:
            continue
        if not str(row.get("id") or row.get("document_id") or row.get("post_id") or "").strip():
            row["id"] = f"4cat-{index}"
        if not str(row.get("text") or "").strip():
            # Keep the original body/content field as well; ``text`` gives the
            # canonical CSV path one stable text-bearing column.
            row["text"] = body
        if default_platform and not str(row.get("platform") or row.get("source_platform") or "").strip():
            row["platform"] = default_platform
        if default_language and not str(row.get("language") or "").strip():
            row["language"] = default_language
        for key, value in list(row.items()):
            if isinstance(value, (dict, list, tuple)):
                row[key] = json.dumps(value, ensure_ascii=False, default=str)
        normalized.append(row)
    return normalized


def _safe_key(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-.")
    return value or "4cat"


def run_fourcat_rows(rows: Iterable[dict[str, Any]], *, output_path: str | Path,
                     dataset_key: str = "4cat", project: str = "ai26",
                     arena: str = "grassroots", machine: str = "roihu",
                     execution: str = "cli", model: str | None = None,
                     memory_dir: str | Path | None = None,
                     topic_key: str | None = None,
                     default_platform: str = "", default_language: str = "",
                     work_dir: str | Path | None = None) -> dict[str, Any]:
    """Run 4CAT rows through the exact canonical LaclauGPT execution path.

    This is the testable adapter boundary used by the 4CAT processor. It owns
    only row normalization and 4CAT filesystem conveniences; analysis, stage
    selection, Context Memory, provenance and interchange serialization are all
    delegated to ``EffectiveRunConfig`` + ``run_canonical_pipeline``.
    """
    from laclaugpt.canonical_pipeline import run_canonical_pipeline
    from laclaugpt.execution import EffectiveRunConfig, ExecutionCoordinator, RunStore

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_fourcat_rows(
        rows, default_platform=default_platform, default_language=default_language
    )
    if not normalized:
        output.write_text("", encoding="utf-8")
        return {
            "run": None,
            "result": {"processed": 0, "skipped": 0, "annotations": [], "output": str(output)},
            "config": None,
            "work_dir": None,
        }

    namespace = _safe_key(dataset_key)
    root = Path(work_dir) if work_dir is not None else output.parent / f".{namespace}.laclaugpt"
    root.mkdir(parents=True, exist_ok=True)
    input_snapshot = root / "fourcat-input.csv"

    import pandas as pd
    pd.DataFrame(normalized).to_csv(input_snapshot, index=False)

    dataset_overrides: dict[str, Any] = {
        "input": str(input_snapshot),
        "output": str(output),
        "storage": {"work_dir": str(root)},
    }
    if memory_dir:
        dataset_overrides["storage"]["memory_dir"] = str(memory_dir)
    if topic_key and topic_key != "generic":
        dataset_overrides["topic_key"] = topic_key
    if model and model != "auto":
        dataset_overrides["model"] = {"text": model, "vision": model}

    config = EffectiveRunConfig.compose(
        project, machine, execution,
        overrides={"dataset": dataset_overrides},
        arena=arena,
    )
    store = RunStore(root / "runs.sqlite3")
    try:
        coordinator = ExecutionCoordinator(config, store, run_canonical_pipeline)
        run_record, result = coordinator.execute()
    finally:
        store.connection.close()
        # 4CAT already owns the source dataset. Do not retain an unnecessary
        # second plaintext corpus copy after the canonical run finishes.
        input_snapshot.unlink(missing_ok=True)

    canonical_review = root / "logs" / "glossary_review.csv"
    if canonical_review.exists():
        shutil.copyfile(canonical_review, Path(str(output) + ".review.csv"))

    return {
        "run": run_record,
        "result": result,
        "config": config,
        "work_dir": root,
    }
