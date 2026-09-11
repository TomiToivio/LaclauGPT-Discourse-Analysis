"""TASK3 sampling-stratum provenance: DAIR profile metadata propagation.

Synthetic-profile tests only (offline, no live calls): the collector must
carry sampling_stratum / sampling_rationale from the private profile into
every canonical record, while keeping them separate from analytical state
(classification_state stays "unjudged").
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from laclaugpt.collect import collect_web
from laclaugpt.collect.dair import _common, load_profile

EXAMPLE = """\
project: ai26
source_group: ai26-ideologies
selection_rationale: "stratified pilot; strata are heuristics"
sources:
  - key: bluesky-example
    kind: bluesky
    handle: example-org.example
    enabled: false
    sampling_stratum: xrisk_control
    sampling_rationale: "official pause-advocacy account"
  - key: mastodon-example
    kind: mastodon
    account: example.social/@scholar
    enabled: false
    sampling_stratum: critical_ai
    sampling_rationale: "named scholar, platform-power critique"
"""


class ProfileLoadTests(unittest.TestCase):
    def test_profile_loads_with_strata(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml",
                                         delete=False) as fh:
            fh.write(EXAMPLE)
            path = fh.name
        try:
            cfg = load_profile(path)
            self.assertEqual(cfg["source_group"], "ai26-ideologies")
            self.assertEqual(len(cfg["sources"]), 2)
            self.assertEqual(cfg["sources"][0]["sampling_stratum"],
                             "xrisk_control")
        finally:
            import pathlib
            pathlib.Path(path).unlink()

    def test_common_carries_stratum_but_not_as_truth(self) -> None:
        cfg = {"project": "ai26", "source_group": "g",
               "selection_rationale": "heuristic"}
        source = {"key": "k1", "sampling_stratum": "critical_ai",
                  "sampling_rationale": "why collected"}
        record = _common(
            CollectRecord := _record(), cfg, source)
        self.assertEqual(record.metadata["sampling_stratum"], "critical_ai")
        self.assertEqual(record.metadata["sampling_rationale"],
                         "why collected")
        # classification_state stays unjudged: stratum is NOT an analysis
        self.assertEqual(record.metadata["classification_state"], "unjudged")

    def test_common_without_arena_does_not_crash(self) -> None:
        cfg = {"project": "ai26"}  # minimal private profile
        source = {"key": "k1"}
        record = _common(_record(), cfg, source)
        self.assertEqual(record.metadata["arena"], "")
        self.assertEqual(record.metadata["sampling_stratum"], "")

    def test_example_profile_is_valid(self) -> None:
        import pathlib
        example = (pathlib.Path(__file__).resolve().parents[1]
                   / "docs" / "examples" / "ai26-ideologies.example.yaml")
        cfg = load_profile(str(example))
        self.assertEqual(len(cfg["sources"]), 3)
        self.assertTrue(all("sampling_stratum" in s for s in cfg["sources"]))


def _record():
    from laclaugpt.collect import CollectRecord
    return CollectRecord(source_type="social", native_id="n", url="u",
                         collector="dair-bluesky")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()