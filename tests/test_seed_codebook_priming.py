"""Regression tests for issue #61 seed-codebook priming."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from laclaugpt_memory import Memory
from seed_codebook import (
    AFFECT_MUST_BE_DEMONSTRATED,
    LEGACY_PRIMING_DEFINITIONS,
    ROLE_MUST_BE_DEMONSTRATED,
    SEEDS,
    _refresh_legacy_definition,
)


class SeedCodebookPrimingTests(unittest.TestCase):
    def test_signifier_seeds_do_not_preassign_roles(self) -> None:
        signifiers = [(label, definition) for kind, label, definition in SEEDS
                      if kind == "signifier"]
        self.assertTrue(signifiers)
        for label, definition in signifiers:
            self.assertEqual(
                definition,
                ROLE_MUST_BE_DEMONSTRATED,
                f"{label!r} must not receive a pre-assigned Laclaudian role",
            )

    def test_affect_vocabulary_does_not_preassign_us_or_frontier_side(self) -> None:
        affect_labels = {
            "hope", "pride", "ambition", "confidence",
            "resentment", "anger", "fear", "contempt",
        }
        affect_rows = [(label, definition) for kind, label, definition in SEEDS
                       if kind == "target" and label in affect_labels]
        self.assertEqual({label for label, _ in affect_rows}, affect_labels)
        for label, definition in affect_rows:
            self.assertEqual(definition, AFFECT_MUST_BE_DEMONSTRATED)
            folded = definition.casefold()
            self.assertNotIn("us-side", folded)
            self.assertNotIn("frontier-side", folded)

    def test_exact_legacy_definition_is_neutralized_on_reseed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory = Memory(memory_dir=str(Path(tmp) / "memory"),
                            embedding_backend="none")
            legacy = next(iter(LEGACY_PRIMING_DEFINITIONS["innovation"]))
            resolved = memory.resolve(
                "innovation", kind="signifier", definition=legacy,
                stage="ai-edition-seed", video_key="paper", evidence="seed",
            )
            self.assertEqual(memory.get(resolved.obj_id)["definition"], legacy)

            changed = _refresh_legacy_definition(
                memory, resolved.obj_id, "innovation", ROLE_MUST_BE_DEMONSTRATED
            )
            memory.conn.commit()
            self.assertTrue(changed)
            self.assertEqual(
                memory.get(resolved.obj_id)["definition"],
                ROLE_MUST_BE_DEMONSTRATED,
            )
            memory.close()

    def test_human_edited_definition_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            memory = Memory(memory_dir=str(Path(tmp) / "memory"),
                            embedding_backend="none")
            resolved = memory.resolve(
                "innovation", kind="signifier",
                definition="Human-reviewed project definition",
                stage="human", video_key="review", evidence="reviewed",
            )
            changed = _refresh_legacy_definition(
                memory, resolved.obj_id, "innovation", ROLE_MUST_BE_DEMONSTRATED
            )
            memory.conn.commit()
            self.assertFalse(changed)
            self.assertEqual(
                memory.get(resolved.obj_id)["definition"],
                "Human-reviewed project definition",
            )
            memory.close()


if __name__ == "__main__":
    unittest.main()
