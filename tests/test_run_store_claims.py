from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from laclaugpt.execution.core import ClaimReason, EffectiveRunConfig, RunStore


def config() -> EffectiveRunConfig:
    return EffectiveRunConfig(
        project="test", machine="local", execution="cli", analysis={}, backends={}
    )


class RunStoreClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary_directory.name) / "runs.sqlite3"
        self.first = RunStore(self.database)
        self.second = RunStore(self.database)
        self.config = config()

    def tearDown(self) -> None:
        self.first.connection.close()
        self.second.connection.close()
        self.temporary_directory.cleanup()

    def test_live_claim_has_one_owner_across_connections(self) -> None:
        owner = self.first.claim(self.config, "run-a", "document")
        competitor = self.second.claim(self.config, "run-b", "document")

        self.assertTrue(owner)
        self.assertEqual(competitor.reason, ClaimReason.BUSY)
        row = self.second.connection.execute(
            "SELECT run_id, attempts FROM checkpoints"
        ).fetchone()
        self.assertEqual(row, ("run-a", 1))

    def test_simultaneous_claims_are_atomic(self) -> None:
        barrier = threading.Barrier(2)

        def claim(run_id: str):
            store = RunStore(self.database)
            try:
                barrier.wait()
                return store.claim(self.config, run_id, "simultaneous")
            finally:
                store.connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(claim, ("run-a", "run-b")))

        self.assertEqual(sum(bool(result) for result in results), 1)
        self.assertEqual(
            sorted(result.reason.value for result in results), ["acquired", "busy"]
        )

    def test_stale_claim_can_be_recovered_with_explicit_lease(self) -> None:
        old = self.first.claim(self.config, "run-a", "document")
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        self.first.connection.execute(
            "UPDATE checkpoints SET updated_at=?", (stale_time.isoformat(),)
        )
        self.first.connection.commit()

        replacement = self.second.claim(
            self.config, "run-b", "document", stale_after=timedelta(minutes=5)
        )

        self.assertTrue(old)
        self.assertTrue(replacement)
        self.assertNotEqual(old.token, replacement.token)

    def test_failed_item_requires_retry_policy(self) -> None:
        claim = self.first.claim(self.config, "run-a", "document")
        self.assertTrue(self.first.checkpoint(
            self.config, "run-a", "document", "failed", "boom",
            claim_token=claim.token,
        ))

        skipped = self.second.claim(self.config, "run-b", "document")
        retried = self.second.claim(
            self.config, "run-b", "document", retry_failed=True
        )

        self.assertEqual(skipped.reason, ClaimReason.FAILED)
        self.assertTrue(retried)

    def test_superseded_worker_cannot_checkpoint(self) -> None:
        old = self.first.claim(self.config, "run-a", "document")
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        self.first.connection.execute(
            "UPDATE checkpoints SET updated_at=?", (stale_time.isoformat(),)
        )
        self.first.connection.commit()
        replacement = self.second.claim(
            self.config, "run-b", "document", stale_after=timedelta(minutes=5)
        )

        updated = self.first.checkpoint(
            self.config, "run-a", "document", claim_token=old.token
        )

        self.assertFalse(updated)
        row = self.second.connection.execute(
            "SELECT run_id, status, claim_token FROM checkpoints"
        ).fetchone()
        self.assertEqual(row, ("run-b", "running", replacement.token))


if __name__ == "__main__":
    unittest.main()
