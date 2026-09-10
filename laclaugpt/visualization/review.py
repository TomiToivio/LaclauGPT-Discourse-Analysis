"""Attributable, append-only researcher assessments for dashboard use.

Human assessments intentionally do not mutate canonical analysis JSONL. They live
in a local SQLite sidecar and are keyed to the project/corpus, source document,
analysis run/artifact, reviewer, and reviewed code or claim. This keeps model
output immutable while preserving independent coding, disagreement, revision and
adjudication history (INV_HUMAN_REVIEW).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

UNKNOWN = "unknown"
_RECORD_TYPES = {"assessment", "revision", "adjudication", "legacy"}
_TARGET_TYPES = {"document", "code", "claim"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _known(value: Any) -> str:
    text = str(value or "").strip()
    return text or UNKNOWN


def artifact_fingerprint(annotation: Any) -> str:
    """Return a stable fingerprint for the exact canonical annotation artifact."""
    if hasattr(annotation, "model_dump"):
        payload = annotation.model_dump(mode="json")
    elif isinstance(annotation, dict):
        payload = annotation
    else:
        payload = vars(annotation) if hasattr(annotation, "__dict__") else repr(annotation)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def assessment_context(
    annotation: Any,
    *,
    project_id: str = "",
    corpus_id: str = "",
) -> dict[str, str]:
    """Build run-safe assessment provenance from a canonical annotation."""
    provenance = getattr(annotation, "collection_provenance", {}) or {}
    return {
        "project_id": _known(project_id or provenance.get("project")),
        "corpus_id": _known(
            corpus_id
            or provenance.get("corpus_id")
            or provenance.get("analysis_profile")
            or provenance.get("arena_id")
        ),
        "run_id": _known(getattr(annotation, "run_id", "")),
        "artifact_fingerprint": artifact_fingerprint(annotation),
    }


def canonical_review_targets(annotation: Any) -> list[dict[str, str]]:
    """Return document/code/claim targets using canonical IDs wherever available."""
    targets: list[dict[str, str]] = [
        {"target_type": "document", "target_id": "", "label": "Document-level assessment"}
    ]
    seen: set[tuple[str, str]] = {("document", "")}

    def add(target_type: str, target_id: str, label: str) -> None:
        key = (target_type, target_id)
        if target_id and key not in seen:
            seen.add(key)
            targets.append({"target_type": target_type, "target_id": target_id, "label": label})

    for family, items in (
        ("entity", getattr(annotation, "entities", []) or []),
        ("topic", getattr(annotation, "topics", []) or []),
        ("signifier", getattr(annotation, "signifiers", []) or []),
        ("nodal candidate", getattr(annotation, "nodal_points", []) or []),
    ):
        for item in items:
            obj_id = str(getattr(item, "obj_id", "") or "").strip()
            label = str(getattr(item, "label", "") or obj_id)
            add("code", obj_id, f"{family}: {obj_id} · {label}")

    for item in getattr(annotation, "articulations", []) or []:
        source = str(getattr(getattr(item, "signifier", None), "obj_id", "") or "").strip()
        related = sorted(
            str(getattr(ref, "obj_id", "") or "").strip()
            for ref in (getattr(item, "related_to", []) or [])
            if str(getattr(ref, "obj_id", "") or "").strip()
        )
        relation = str(getattr(item, "relation", "") or "articulates").strip()
        claim_id = f"articulation:{source}:{relation}:{','.join(related)}"
        add("claim", claim_id, claim_id)

    for item in getattr(annotation, "populism_elements", []) or []:
        ref = getattr(item, "element", None)
        obj_id = str(getattr(ref, "obj_id", "") or "").strip()
        side = str(getattr(item, "side", "") or "").strip()
        add("claim", f"populism:{side}:{obj_id}", f"Palonen {side}: {obj_id}")

    for item in getattr(annotation, "affects", []) or []:
        ref = getattr(item, "target", None)
        obj_id = str(getattr(ref, "obj_id", "") or "").strip()
        affect = str(getattr(item, "affect", "") or "").strip()
        add("claim", f"affect:{obj_id}:{affect}", f"Affective investment: {obj_id} · {affect}")

    return targets


class ReviewStore:
    """SQLite-backed append-only assessment history.

    ``save`` remains compatible with the original document-note API when no
    provenance arguments are provided. New dashboard/research code should pass
    explicit project/corpus/run/fingerprint/reviewer provenance.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        self._migrate_legacy()

    def _create_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS review_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_uuid TEXT NOT NULL UNIQUE,
                project_id TEXT NOT NULL,
                corpus_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                artifact_fingerprint TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL DEFAULT '',
                review_status TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                record_type TEXT NOT NULL DEFAULT 'assessment',
                supersedes_id INTEGER,
                linked_assessment_ids TEXT NOT NULL DEFAULT '[]',
                blind_initial INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                legacy_key TEXT UNIQUE,
                FOREIGN KEY(supersedes_id) REFERENCES review_assessments(id)
            )
            """
        )
        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS review_assessments_context_idx
            ON review_assessments(
                project_id, corpus_id, document_id, run_id,
                artifact_fingerprint, reviewer_id, target_type, target_id, id
            )
            """
        )
        self.connection.commit()

    def _migrate_legacy(self) -> None:
        """Copy v1 dashboard rows into immutable records without inventing metadata."""
        exists = self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dashboard_reviews'"
        ).fetchone()
        if not exists:
            return
        rows = self.connection.execute(
            "SELECT document_id, review_status, note, tags, updated_at FROM dashboard_reviews"
        ).fetchall()
        for row in rows:
            legacy_key = f"dashboard_reviews:{row['document_id']}:{row['updated_at']}"
            digest = hashlib.sha256(legacy_key.encode("utf-8")).hexdigest()
            self.connection.execute(
                """
                INSERT OR IGNORE INTO review_assessments(
                    assessment_uuid, project_id, corpus_id, document_id, run_id,
                    artifact_fingerprint, reviewer_id, target_type, target_id,
                    review_status, note, tags, record_type, supersedes_id,
                    linked_assessment_ids, blind_initial, created_at, legacy_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'document', '', ?, ?, ?, 'legacy', NULL, '[]', 0, ?, ?)
                """,
                (
                    f"legacy-{digest}", UNKNOWN, UNKNOWN, str(row["document_id"]), UNKNOWN,
                    UNKNOWN, UNKNOWN, str(row["review_status"] or ""), str(row["note"] or ""),
                    str(row["tags"] or ""), str(row["updated_at"] or _now()), legacy_key,
                ),
            )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _tags(tags: Iterable[str]) -> str:
        return ",".join(sorted({str(tag).strip() for tag in tags if str(tag).strip()}))

    @staticmethod
    def _linked(ids: Iterable[int]) -> list[int]:
        return sorted({int(value) for value in ids})

    @staticmethod
    def _row(row: sqlite3.Row | None, *, document_id: str = "") -> dict[str, Any]:
        if row is None:
            return {
                "id": None,
                "assessment_uuid": "",
                "project_id": UNKNOWN,
                "corpus_id": UNKNOWN,
                "document_id": document_id,
                "run_id": UNKNOWN,
                "artifact_fingerprint": UNKNOWN,
                "reviewer_id": UNKNOWN,
                "target_type": "document",
                "target_id": "",
                "review_status": "",
                "note": "",
                "tags": [],
                "record_type": "",
                "supersedes_id": None,
                "linked_assessment_ids": [],
                "blind_initial": False,
                "created_at": "",
                "updated_at": "",
            }
        data = dict(row)
        data["tags"] = [tag.strip() for tag in str(data.get("tags") or "").split(",") if tag.strip()]
        try:
            data["linked_assessment_ids"] = [int(value) for value in json.loads(data.get("linked_assessment_ids") or "[]")]
        except (TypeError, ValueError, json.JSONDecodeError):
            data["linked_assessment_ids"] = []
        data["blind_initial"] = bool(data.get("blind_initial"))
        # Backward-compatible key used by the original dashboard/tests.
        data["updated_at"] = data.get("created_at", "")
        return data

    def _context_params(
        self,
        document_id: str,
        *,
        project_id: str,
        corpus_id: str,
        run_id: str,
        artifact_fingerprint: str,
        reviewer_id: str,
        target_type: str,
        target_id: str,
    ) -> tuple[str, ...]:
        return (
            _known(project_id), _known(corpus_id), str(document_id), _known(run_id),
            _known(artifact_fingerprint), _known(reviewer_id), str(target_type), str(target_id),
        )

    def get(
        self,
        document_id: str,
        *,
        project_id: str = UNKNOWN,
        corpus_id: str = UNKNOWN,
        run_id: str = UNKNOWN,
        artifact_fingerprint: str = UNKNOWN,
        reviewer_id: str = UNKNOWN,
        target_type: str = "document",
        target_id: str = "",
    ) -> dict[str, Any]:
        """Return the latest record for one exact provenance context.

        Exact run and fingerprint matching is deliberate: a review from another
        run is never silently applied to the current artifact.
        """
        params = self._context_params(
            document_id,
            project_id=project_id,
            corpus_id=corpus_id,
            run_id=run_id,
            artifact_fingerprint=artifact_fingerprint,
            reviewer_id=reviewer_id,
            target_type=target_type,
            target_id=target_id,
        )
        row = self.connection.execute(
            """
            SELECT * FROM review_assessments
            WHERE project_id=? AND corpus_id=? AND document_id=? AND run_id=?
              AND artifact_fingerprint=? AND reviewer_id=? AND target_type=? AND target_id=?
            ORDER BY id DESC LIMIT 1
            """,
            params,
        ).fetchone()
        return self._row(row, document_id=document_id)

    def _fetch_id(self, assessment_id: int) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM review_assessments WHERE id=?", (int(assessment_id),)
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown assessment id: {assessment_id}")
        return row

    @staticmethod
    def _same_target(left: sqlite3.Row, context: tuple[str, ...]) -> bool:
        keys = (
            "project_id", "corpus_id", "document_id", "run_id",
            "artifact_fingerprint", "reviewer_id", "target_type", "target_id",
        )
        return all(str(left[key]) == str(value) for key, value in zip(keys, context))

    def save(
        self,
        document_id: str,
        *,
        review_status: str = "",
        note: str = "",
        tags: list[str] | tuple[str, ...] = (),
        project_id: str = UNKNOWN,
        corpus_id: str = UNKNOWN,
        run_id: str = UNKNOWN,
        artifact_fingerprint: str = UNKNOWN,
        reviewer_id: str = UNKNOWN,
        target_type: str = "document",
        target_id: str = "",
        record_type: str = "assessment",
        supersedes_id: int | None = None,
        linked_assessment_ids: Iterable[int] = (),
        blind_initial: bool = False,
    ) -> dict[str, Any]:
        """Append one immutable assessment/revision/adjudication record."""
        if target_type not in _TARGET_TYPES:
            raise ValueError(f"Unsupported target_type: {target_type}")
        if record_type not in _RECORD_TYPES - {"legacy"}:
            raise ValueError(f"Unsupported record_type: {record_type}")

        context = self._context_params(
            document_id,
            project_id=project_id,
            corpus_id=corpus_id,
            run_id=run_id,
            artifact_fingerprint=artifact_fingerprint,
            reviewer_id=reviewer_id,
            target_type=target_type,
            target_id=target_id,
        )
        # New attributable research records must name a reviewer. The all-unknown
        # compatibility path remains available for old dashboard callers/tests.
        research_context_known = any(value != UNKNOWN for value in context[:2] + context[3:5])
        if research_context_known and context[5] == UNKNOWN:
            raise ValueError("reviewer_id is required for attributable assessment records")

        linked = self._linked(linked_assessment_ids)
        if record_type == "revision":
            if supersedes_id is None:
                raise ValueError("revision requires supersedes_id")
            previous = self._fetch_id(supersedes_id)
            if not self._same_target(previous, context):
                raise ValueError("revision must supersede the same reviewer/context/target")
        elif supersedes_id is not None:
            raise ValueError("supersedes_id is only valid for revision records")

        if record_type == "adjudication":
            if not linked:
                raise ValueError("adjudication requires linked_assessment_ids")
            # Adjudication may link different reviewers but must concern the exact
            # same project/corpus/document/run/artifact/target.
            target_context = context[:5] + context[6:]
            for assessment_id in linked:
                prior = self._fetch_id(assessment_id)
                prior_context = tuple(str(prior[key]) for key in (
                    "project_id", "corpus_id", "document_id", "run_id",
                    "artifact_fingerprint", "target_type", "target_id",
                ))
                if prior_context != target_context:
                    raise ValueError("adjudication links must share the same run/artifact/target")
        elif linked:
            raise ValueError("linked_assessment_ids are only valid for adjudication records")

        assessment_uuid = str(uuid.uuid4())
        created_at = _now()
        cursor = self.connection.execute(
            """
            INSERT INTO review_assessments(
                assessment_uuid, project_id, corpus_id, document_id, run_id,
                artifact_fingerprint, reviewer_id, target_type, target_id,
                review_status, note, tags, record_type, supersedes_id,
                linked_assessment_ids, blind_initial, created_at, legacy_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                assessment_uuid, *context[:6], context[6], context[7], str(review_status or ""),
                str(note or ""), self._tags(tags), record_type, supersedes_id,
                json.dumps(linked), int(bool(blind_initial)), created_at,
            ),
        )
        self.connection.commit()
        return self._row(self._fetch_id(int(cursor.lastrowid)), document_id=document_id)

    def history(
        self,
        document_id: str,
        *,
        project_id: str | None = None,
        corpus_id: str | None = None,
        run_id: str | None = None,
        artifact_fingerprint: str | None = None,
        reviewer_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        viewer_reviewer_id: str | None = None,
        blind: bool = False,
    ) -> list[dict[str, Any]]:
        """Return immutable history, optionally hiding peer decisions in blind mode."""
        clauses = ["document_id=?"]
        params: list[Any] = [str(document_id)]
        for column, value in (
            ("project_id", project_id),
            ("corpus_id", corpus_id),
            ("run_id", run_id),
            ("artifact_fingerprint", artifact_fingerprint),
            ("reviewer_id", reviewer_id),
            ("target_type", target_type),
            ("target_id", target_id),
        ):
            if value is not None:
                clauses.append(f"{column}=?")
                params.append(_known(value) if column not in {"target_type", "target_id"} else str(value))
        if blind:
            if not viewer_reviewer_id:
                return []
            clauses.append("reviewer_id=?")
            params.append(_known(viewer_reviewer_id))
        rows = self.connection.execute(
            f"SELECT * FROM review_assessments WHERE {' AND '.join(clauses)} ORDER BY id ASC",
            params,
        ).fetchall()
        return [self._row(row) for row in rows]

    def dataframe_rows(
        self,
        *,
        viewer_reviewer_id: str | None = None,
        blind: bool = False,
    ) -> list[dict[str, Any]]:
        """Export-ready rows with complete assessment provenance."""
        if blind:
            if not viewer_reviewer_id:
                return []
            rows = self.connection.execute(
                "SELECT * FROM review_assessments WHERE reviewer_id=? ORDER BY id DESC",
                (_known(viewer_reviewer_id),),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM review_assessments ORDER BY id DESC"
            ).fetchall()
        return [self._row(row) for row in rows]

    def export_rows(self) -> list[dict[str, Any]]:
        """Explicit export alias; exports never hide provenance columns."""
        return self.dataframe_rows(blind=False)
