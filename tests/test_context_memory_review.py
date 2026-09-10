"""Issue #62 regression tests: Context Memory reviewability.

- explicit LLM EXISTING without chosen ID → UNCERTAIN (no 0.60 re-point)
- rejected merges are consulted by both resolution layers (no auto-reuse)
- only exact normalised matches auto-reuse; near-identical forms stay
  candidates for human review
- context block framing is neutral and the fallback ordering is alphabetical
- resolve_candidates no longer folds UNCERTAIN into matched
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from laclaugpt.memory.context import CanonicalRegistry, Resolution
from laclaugpt_memory import Memory as RealMemory


def _memory() -> RealMemory:
    # Isolated temp dir: the None default resolves to data/memory, which
    # persists across tests and would leak objects between them.
    return RealMemory(memory_dir=tempfile.mkdtemp(), embedding_backend="none")


def _seed(memory: RealMemory, raw: str, kind: str) -> str:
    """Create a PROVISIONAL object via the public resolve() API; return obj_id."""
    res = memory.resolve(raw, kind)  # decision=None → NEW (no candidate) → provisional
    return res.obj_id


class ExplicitExistingWithoutChosenIdTests(unittest.TestCase):
    """Finding 1: EXISTING without chosen ID → UNCERTAIN, not 0.60 re-point."""

    def test_no_silent_repoint_below_fuzzy_threshold(self) -> None:
        memory = _memory()
        try:
            # A candidate just below the fuzzy-entity threshold 0.90.
            _seed(memory, "Elon Musk", "entity")
            oid = memory.conn.execute(
                "SELECT obj_id FROM objects WHERE label='Elon Musk'").fetchone()[0]
            res = memory.resolve("Elon Muskk", "entity", decision="EXISTING",
                                 chosen_obj_id=None)
            self.assertEqual(res.decision, "UNCERTAIN",
                             "unresolved EXISTING must not re-point via similarity")
        finally:
            memory.close()

    def test_uncertain_keeps_candidate_for_review(self) -> None:
        memory = _memory()
        try:
            _seed(memory, "European Union", "target")
            res = memory.resolve("European Unio", "target",
                                 decision="EXISTING", chosen_obj_id=None)
            self.assertEqual(res.decision, "UNCERTAIN")
            self.assertTrue(res.obj_id, "candidate id rides along for review")
        finally:
            memory.close()

    def test_explicit_chosen_id_still_resolves(self) -> None:
        memory = _memory()
        try:
            _seed(memory, "Elon Musk", "entity")
            res = memory.resolve("Elon Musk", "entity", decision="EXISTING",
                                 chosen_obj_id="E001")
            self.assertEqual(res.decision, "EXISTING")
            self.assertEqual(res.obj_id, "E001")
        finally:
            memory.close()


class RejectedMergeConsultedTests(unittest.TestCase):
    """Finding 2: rejected merge pairs block auto-reuse (both layers)."""

    def test_memory_layer_rejects_reused_merge_pair(self) -> None:
        memory = _memory()
        try:
            _seed(memory, "OpenAI", "entity")
            _seed(memory, "OpenAI Inc", "entity")
            memory.reject_merge("E001", "E002", rationale="distinct legal entities")
            # A similarity proposal pointing back into the rejected pair must
            # not auto-resolve to EXISTING.
            res = memory.resolve("OpenAI incorporated", "entity")  # no decision → auto rules
            self.assertIn(res.decision, ("NEW", "UNCERTAIN"),
                          "rejected merge pair must not auto-merge")
        finally:
            memory.close()

    def test_registry_layer_never_reuses_rejected_pair(self) -> None:
        registry = CanonicalRegistry()
        registry.add("e1", "Musk", "entity")
        registry.add("e2", "Elon Musk", "entity")
        registry.reject_merge("e1", "e2")

        def provider(mention, kind):
            # similarity would score e2 at 0.99 for "elon musk jr"
            return [("e2", 0.99)]

        res = registry.resolve("elon musk jr", "entity", candidate_provider=provider,
                               auto_merge_threshold=0.98)
        self.assertEqual(res.decision, "create_candidate",
                         "rejected pair must never auto-reuse")

    def test_registry_still_resolves_unrelated_candidates(self) -> None:
        registry = CanonicalRegistry()
        registry.add("e1", "Musk", "entity")
        registry.add("e2", "Grimes", "entity")
        registry.reject_merge("e1", "e2")

        def provider(mention, kind):
            return [("e2", 0.0)]  # unrelated candidate is not part of a rejected pair

        res = registry.resolve("Grimes", "entity", candidate_provider=provider,
                               auto_merge_threshold=0.5)
        self.assertIn(res.decision, ("candidate_reuse", "reuse"))
        self.assertEqual(res.canonical_id, "e2")


class ExactOnlyAutoReuseTests(unittest.TestCase):
    """Finding 3: near-identical surface forms stay candidates for review."""

    def test_memory_layer_no_auto_reuse_below_exact(self) -> None:
        memory = _memory()
        try:
            _seed(memory, "European Union", "target")
            res = memory.resolve("The European Union", "target")  # no LLM in the loop
            # 0.99 alias-ish / 0.98 fuzzy is no longer an unambiguous reuse:
            self.assertIn(res.decision, ("NEW", "UNCERTAIN"),
                          "near-identical form must not silently become the concept")
        finally:
            memory.close()

    def test_exact_normalised_match_still_auto_reuses(self) -> None:
        memory = _memory()
        try:
            obj_id = _seed(memory, "European Union", "target")
            res = memory.resolve("European union", "target")  # exact after normalisation
            self.assertEqual(res.decision, "EXISTING")
            self.assertEqual(res.obj_id, obj_id)
        finally:
            memory.close()

    def test_alias_exact_match_still_auto_reuses(self) -> None:
        memory = _memory()
        try:
            obj_id = _seed(memory, "European Union", "target")
            memory._add_alias(obj_id, "the EU")
            res = memory.resolve("the EU", "target")
            self.assertEqual(res.decision, "EXISTING")
            self.assertEqual(res.obj_id, obj_id)
        finally:
            memory.close()

    def test_registry_layer_requires_full_score_for_reuse(self) -> None:
        registry = CanonicalRegistry()
        registry.add("e1", "OpenAI", "entity")

        def provider(mention, kind):
            return [("e1", 0.98)]  # the old auto threshold

        # The default threshold is 1.0 (exact only); the 0.98 similarity
        # proposal stays a candidate instead of auto-merging (issue #62).
        res = registry.resolve("openai inc", "entity", candidate_provider=provider)
        self.assertEqual(res.decision, "create_candidate",
                         "0.98 similarity must not auto-merge (issue #62)")


class NeutralContextPrimingTests(unittest.TestCase):
    """Finding 4: neutral wording, alphabetical fallback ordering."""

    def test_context_block_has_no_prefer_existing_priming(self) -> None:
        memory = _memory()
        try:
            obj_id = _seed(memory, "European Union", "target")
            memory.promote(obj_id)  # CANONICAL-only preview includes it
            memory._bump(obj_id)  # simulate model-driven usage
            memory._bump(obj_id)
            block = memory.context_prompt_block("European Union", kinds=("target",))
            self.assertNotIn("prefer EXISTING", block)
            self.assertNotIn("Established", block)
            self.assertIn("suggestions", block.lower())
            self.assertIn("reference only", block.lower())
        finally:
            memory.close()

    def test_fallback_context_ordering_is_alphabetical(self) -> None:
        memory = _memory()
        try:
            # Create in reverse alphabetical order, bump each heavily: the
            # fallback preview must still be alphabetical, not usage-ordered.
            for label in ("Surveillance", "Abundance", "Misinformation"):
                obj_id = _seed(memory, label, "topic")
                memory.promote(obj_id)
                for _ in range(3):
                    memory._bump(obj_id)
            block = memory.context_prompt_block("zzz-no-match", kinds=("topic",))
            lines = [l for l in block.splitlines() if l.strip().startswith("-")]
            labels = [l.split("= ", 1)[1].split(" —")[0] for l in lines]
            self.assertEqual(labels, sorted(labels),
                             "fallback preview must not be usage-ordered")
        finally:
            memory.close()


class ResolveCandidatesUncertainTests(unittest.TestCase):
    """Minor: UNCERTAIN must not be folded into matched."""

    def test_uncertain_stays_out_of_matched(self) -> None:
        from laclaugpt_memory import resolve_candidates
        memory = _memory()
        try:
            _seed(memory, "European Union", "target")
            # Below the fuzzy threshold: previously folded into matched.
            matched, new = resolve_candidates(["European Unio"], "target", memory)
            self.assertNotIn("european union", matched)
            self.assertIn("european union", new)
        finally:
            memory.close()

    def test_exact_match_still_lands_in_matched(self) -> None:
        from laclaugpt_memory import resolve_candidates
        memory = _memory()
        try:
            _seed(memory, "European Union", "target")
            matched, new = resolve_candidates(["European Union"], "target", memory)
            self.assertIn("european union", matched)
        finally:
            memory.close()


if __name__ == "__main__":
    unittest.main()