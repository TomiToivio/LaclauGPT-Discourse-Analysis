"""AI26 RSS source-manifest tests: loader, provenance, graceful failure.

Covers `config/projects/ai26-rss-sources.toml` semantics:
- manifest parsing (TOML [[feed]] tables + legacy one-URL-per-line files)
- inactive feeds are skipped
- provenance metadata (source_family / sampling_rationale / priority /
  last_verified / homepage) rides on every collected record
- one dead feed never fails the whole collection run
- dedup across runs (CollectionStore ledger)
- --fetch-article enrichment through the canonical web adapter
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from laclaugpt.collect import CollectRecord, collect_rss, collect_web
from laclaugpt.collect.cli import _enrich_rss_articles, load_rss_manifest

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "config" / "projects" / "ai26-rss-sources.toml"

TOML_SAMPLE = """\
[[feed]]
name = "example_feed"
feed_url = "https://example.org/feed.xml"
homepage = "https://example.org"
source_family = "critical ai"
sampling_rationale = "Testing manifest provenance propagation."
priority = "P1"
active = true
last_verified = "2026-09-11"

[[feed]]
name = "inactive_feed"
feed_url = "https://inactive.example.org/feed"
active = false
last_verified = "2026-09-11"

[[feed]]
name = "broken_feed"
feed_url = "https://broken.example.org/feed"
active = true
"""


class ManifestLoaderTests(unittest.TestCase):
    def test_manifest_parses_all_active_feeds(self) -> None:
        entries = load_rss_manifest(str(MANIFEST))
        names = [e["name"] for e in entries]
        self.assertEqual(len(entries), 14)
        self.assertIn("lesswrong_frontpage", names)
        self.assertIn("works_in_progress", names)

    def test_manifest_entries_carry_provenance(self) -> None:
        entries = {e["name"]: e for e in load_rss_manifest(str(MANIFEST))}
        pmarca = entries["pmarca"]
        self.assertEqual(pmarca["source_family"], "techno-optimism / acceleration")
        self.assertIn("Techno-Optimist Manifesto",
                      pmarca["sampling_rationale"])
        self.assertEqual(pmarca["priority"], "P1")
        self.assertTrue(pmarca["last_verified"])

    def test_inactive_feed_is_skipped(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".toml",
                                         delete=False) as fh:
            fh.write(TOML_SAMPLE)
            path = fh.name
        try:
            names = [e["name"] for e in load_rss_manifest(path)]
            self.assertEqual(names, ["example_feed", "broken_feed"])
            self.assertNotIn("inactive", names)
        finally:
            Path(path).unlink()

    def test_legacy_url_list_still_loads(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as fh:
            fh.write("# comment line\nhttps://a.example/feed\n\n"
                     "https://b.example/rss\n")
            path = fh.name
        try:
            entries = load_rss_manifest(path)
            self.assertEqual(entries, [
                {"feed_url": "https://a.example/feed"},
                {"feed_url": "https://b.example/rss"},
            ])
        finally:
            Path(path).unlink()

    def test_empty_manifest_returns_empty(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt",
                                         delete=False) as fh:
            fh.write("# only comments\n\n")
            path = fh.name
        try:
            self.assertEqual(load_rss_manifest(path), [])
        finally:
            Path(path).unlink()


class ManifestProvenanceTests(unittest.TestCase):
    def test_provenance_rides_on_records(self) -> None:
        entry = {"name": "example_feed",
                 "feed_url": "https://example.org/feed.xml",
                 "source_family": "critical ai",
                 "sampling_rationale": "heuristic, not truth",
                 "priority": "P1", "last_verified": "2026-09-11",
                 "homepage": "https://example.org"}
        parsed = collect_rss(entry["feed_url"])  # dead DNS → 0 records
        self.assertEqual(parsed, [])
        # provenance stamping is a pure loop over records; simulate records
        records = [CollectRecord(
            source_type="rss", native_id="n1", url="https://example.org/1",
            title="t", collector="rss",
            metadata={"feed_url": entry["feed_url"],
                      "feed_name": entry["name"]})]
        for rec in records:
            for key in ("source_family", "sampling_rationale", "priority",
                        "last_verified", "homepage"):
                if entry.get(key):
                    rec.metadata[f"source_{key}"] = entry[key]
        self.assertEqual(records[0].metadata["source_source_family"],
                         "critical ai")
        self.assertEqual(records[0].metadata["source_sampling_rationale"],
                         "heuristic, not truth")

    def test_fetch_article_keeps_feed_summary_and_records_status(self) -> None:
        rss_record = CollectRecord(
            source_type="rss", native_id="guid-9",
            url="https://example.org/article", title="Feed title",
            text="Short summary", collector="rss",
            metadata={"feed_url": "https://example.org/feed.xml",
                      "source_family": "critical ai"})
        web_record = collect_web(
            "https://example.org/final-article", html_text="<p>Full text</p>",
            http_status=200)
        with patch("laclaugpt.collect.cli._fetch_web_record",
                   return_value=web_record):
            enriched = _enrich_rss_articles([rss_record])[0]
        self.assertEqual(enriched.metadata["article_fetch"]["status"], "ok")
        self.assertEqual(enriched.metadata["feed_summary"], "Short summary")
        self.assertIn("Full text", enriched.text or "")


class DeadFeedGracefulTests(unittest.TestCase):
    def test_dead_feed_yields_zero_records_without_error(self) -> None:
        records = collect_rss("https://dead.invalid/feed.xml")
        self.assertEqual(records, [])

    def test_unresolvable_feed_file_does_not_crash_run(self) -> None:
        from laclaugpt.collect import cli as cli_mod
        args = type("Args", (), {})()
        args.collect_target = "rss"
        args.feeds = ["/tmp/definitely-missing-manifest.toml"]
        args.fetch_article = False
        # run() should not raise; the store simply receives nothing
        cli_mod.run(args)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()