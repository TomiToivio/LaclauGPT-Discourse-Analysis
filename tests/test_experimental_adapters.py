# -*- coding: utf-8 -*-
"""Supplementary smoke tests for the EXPERIMENTAL layer.

Complements tests/test_experimental_integrations.py (PR #131): capability
registry coverage, actionable error hints, the interim pure-python drift
helper, and adapter importability WITHOUT optional deps (CI passes with
or without the research-experimental extra).
"""
from __future__ import annotations

import unittest

from laclaugpt.experimental import (
    INTEGRATIONS,
    OptionalDependencyError,
    available_integrations,
    is_available,
)

try:
    from laclaugpt.experimental.corpus import (  # noqa: F401
        compare_keyness,
        semantic_shift,
        track_signifier,
    )
    HAS_CORPUS = True
except ImportError:
    HAS_CORPUS = False

from laclaugpt.experimental.drift import temporal_drift, pycorpdiff_available


class RegistryTests(unittest.TestCase):
    def test_all_documented_packages_registered(self) -> None:
        for pkg in ("pycorpdiff", "scattertext", "convokit", "hypothesaes",
                    "textnets", "edsl"):
            self.assertIn(pkg, INTEGRATIONS)
            self.assertTrue(INTEGRATIONS[pkg].epistemic_limit,
                            f"{pkg} needs an epistemic-limit note")

    def test_available_integrations_shape(self) -> None:
        avail = available_integrations()
        self.assertIsInstance(avail, dict)
        self.assertEqual(set(avail), set(INTEGRATIONS))
        self.assertTrue(all(isinstance(v, bool) for v in avail.values()))

    def test_pycorpdiff_gate_consistent(self) -> None:
        # pycorpdiff needs py>=3.11: availability must be False on older
        # interpreters and must never raise.
        self.assertIsInstance(pycorpdiff_available(), bool)
        self.assertIsInstance(is_available("pycorpdiff"), bool)


class ActionableErrorTests(unittest.TestCase):
    def test_optional_dependency_error_is_import_error(self) -> None:
        self.assertTrue(issubclass(OptionalDependencyError, ImportError))

    def test_corpus_adapters_raise_actionable_error_without_pycorpdiff(
            self) -> None:
        if not HAS_CORPUS:
            self.skipTest("corpus module not importable in this env")
        if is_available("pycorpdiff"):
            self.skipTest("pycorpdiff installed")
        with self.assertRaises(OptionalDependencyError):
            compare_keyness(object(), object())


class TemporalDriftTests(unittest.TestCase):
    def test_drift_counts(self) -> None:
        buckets = {
            "2026-01": ["acceleration wins again", "abundance ahead"],
            "2026-02": ["doomers wrong again", "acceleration wins"],
        }
        out = temporal_drift(buckets)
        self.assertEqual(set(out), {"2026-01", "2026-02"})
        self.assertEqual(out["2026-01"]["counts"]["acceleration"], 1)
        self.assertEqual(out["2026-02"]["counts"]["acceleration"], 1)

    def test_drift_filters_short_tokens(self) -> None:
        out = temporal_drift({"b": ["AI AI! (it) ., their words"]})
        counts = out["b"]["counts"]
        self.assertNotIn("ai", counts)
        self.assertNotIn("it", counts)
        self.assertIn("their", counts)
        self.assertIn("words", counts)


class AdapterImportTests(unittest.TestCase):
    def test_all_adapter_modules_importable(self) -> None:
        import importlib
        for mod in ("conversation", "corpus", "hypotheses", "models",
                    "networks", "signifiers", "drift"):
            mod_obj = importlib.import_module(
                f"laclaugpt.experimental.{mod}")
            self.assertIsNotNone(mod_obj)

    def test_no_pipeline_imports_experimental(self) -> None:
        # the experimental layer must stay a leaf: pipeline must not import it
        import pathlib
        repo = pathlib.Path(__file__).resolve().parents[1]
        offenders = []
        for path in (repo / "laclaugpt").rglob("*.py"):
            if "experimental" in str(path):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "from laclaugpt.experimental" in text:
                offenders.append(str(path))
        self.assertEqual(offenders, [],
                         "experimental layer must stay a leaf module")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()