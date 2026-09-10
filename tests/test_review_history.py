from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from laclaugpt.visualization.review import ReviewStore, UNKNOWN, artifact_fingerprint


def _context(*, run_id: str = "run-1", fingerprint: str = "sha256:artifact-1") -> dict[str, str]:
    return {
        "project_id": "ai26",
        "corpus_id": "ai26:elites",
        "run_id": run_id,
        "artifact_fingerprint": fingerprint,
    }


def test_two_reviewers_do_not_overwrite_each_other() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore(Path(tmp) / "reviews.sqlite3")
        try:
            left = store.save(
                "doc-1", reviewer_id="reviewer-a", review_status="accepted", **_context()
            )
            right = store.save(
                "doc-1", reviewer_id="reviewer-b", review_status="rejected", **_context()
            )

            assert left["id"] != right["id"]
            assert store.get("doc-1", reviewer_id="reviewer-a", **_context())["review_status"] == "accepted"
            assert store.get("doc-1", reviewer_id="reviewer-b", **_context())["review_status"] == "rejected"
        finally:
            store.close()


def test_same_document_in_two_runs_never_reuses_assessment() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore(Path(tmp) / "reviews.sqlite3")
        try:
            store.save(
                "doc-1", reviewer_id="reviewer-a", review_status="accepted", **_context()
            )
            missing = store.get(
                "doc-1",
                reviewer_id="reviewer-a",
                **_context(run_id="run-2", fingerprint="sha256:artifact-2"),
            )
            assert missing["id"] is None
            assert missing["review_status"] == ""

            second = store.save(
                "doc-1",
                reviewer_id="reviewer-a",
                review_status="needs_revision",
                **_context(run_id="run-2", fingerprint="sha256:artifact-2"),
            )
            assert second["run_id"] == "run-2"
            assert len(store.history("doc-1")) == 2
        finally:
            store.close()


def test_code_level_rejection_preserves_document_level_assessment() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore(Path(tmp) / "reviews.sqlite3")
        try:
            document = store.save(
                "doc-1", reviewer_id="reviewer-a", review_status="accepted", **_context()
            )
            code = store.save(
                "doc-1",
                reviewer_id="reviewer-a",
                target_type="code",
                target_id="S001",
                review_status="rejected",
                note="The evidence does not support this candidate signifier role.",
                **_context(),
            )

            assert document["target_type"] == "document"
            assert code["target_type"] == "code"
            assert code["target_id"] == "S001"
            assert store.get("doc-1", reviewer_id="reviewer-a", **_context())["review_status"] == "accepted"
            assert store.get(
                "doc-1", reviewer_id="reviewer-a", target_type="code", target_id="S001", **_context()
            )["review_status"] == "rejected"
        finally:
            store.close()


def test_revision_and_adjudication_are_new_linked_records() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore(Path(tmp) / "reviews.sqlite3")
        try:
            first = store.save(
                "doc-1", reviewer_id="reviewer-a", review_status="accepted", **_context()
            )
            peer = store.save(
                "doc-1", reviewer_id="reviewer-b", review_status="rejected", **_context()
            )
            revision = store.save(
                "doc-1",
                reviewer_id="reviewer-a",
                review_status="needs_revision",
                note="Reconsidered after checking the source passage.",
                record_type="revision",
                supersedes_id=first["id"],
                **_context(),
            )
            adjudication = store.save(
                "doc-1",
                reviewer_id="adjudicator",
                review_status="needs_revision",
                note="Disagreement retained; code remains provisional.",
                record_type="adjudication",
                linked_assessment_ids=[first["id"], peer["id"], revision["id"]],
                **_context(),
            )

            history = store.history("doc-1", **_context())
            assert [row["record_type"] for row in history] == [
                "assessment", "assessment", "revision", "adjudication"
            ]
            assert revision["supersedes_id"] == first["id"]
            assert adjudication["linked_assessment_ids"] == sorted(
                [first["id"], peer["id"], revision["id"]]
            )
            assert history[0]["review_status"] == "accepted"
            assert history[1]["review_status"] == "rejected"
        finally:
            store.close()


def test_blind_history_hides_peer_decisions_until_revealed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = ReviewStore(Path(tmp) / "reviews.sqlite3")
        try:
            store.save(
                "doc-1", reviewer_id="reviewer-a", review_status="accepted", blind_initial=True, **_context()
            )
            store.save(
                "doc-1", reviewer_id="reviewer-b", review_status="rejected", blind_initial=True, **_context()
            )

            blind = store.history(
                "doc-1", viewer_reviewer_id="reviewer-a", blind=True, **_context()
            )
            revealed = store.history("doc-1", blind=False, **_context())
            assert [row["reviewer_id"] for row in blind] == ["reviewer-a"]
            assert {row["reviewer_id"] for row in revealed} == {"reviewer-a", "reviewer-b"}
        finally:
            store.close()


def test_legacy_sidecar_migrates_once_with_unknown_provenance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "reviews.sqlite3"
        connection = sqlite3.connect(path)
        connection.execute(
            """
            CREATE TABLE dashboard_reviews (
                document_id TEXT PRIMARY KEY,
                review_status TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO dashboard_reviews VALUES (?, ?, ?, ?, ?)",
            ("legacy-doc", "accepted", "Legacy note", "paper,checked", "2026-09-08T09:00:00Z"),
        )
        connection.commit()
        connection.close()

        store = ReviewStore(path)
        try:
            rows = store.export_rows()
            assert len(rows) == 1
            migrated = rows[0]
            assert migrated["document_id"] == "legacy-doc"
            assert migrated["project_id"] == UNKNOWN
            assert migrated["corpus_id"] == UNKNOWN
            assert migrated["run_id"] == UNKNOWN
            assert migrated["artifact_fingerprint"] == UNKNOWN
            assert migrated["reviewer_id"] == UNKNOWN
            assert migrated["record_type"] == "legacy"
            assert migrated["created_at"] == "2026-09-08T09:00:00Z"
            assert migrated["note"] == "Legacy note"
        finally:
            store.close()

        reopened = ReviewStore(path)
        try:
            assert len(reopened.export_rows()) == 1
        finally:
            reopened.close()


def test_artifact_fingerprint_changes_when_model_output_changes() -> None:
    first = {"document_id": "doc-1", "run_id": "run-1", "summary": "first"}
    second = {"document_id": "doc-1", "run_id": "run-1", "summary": "changed"}
    assert artifact_fingerprint(first) != artifact_fingerprint(second)
