"""RSS source-manifest tests using synthetic fixtures only.

Operational AI26 watch lists are private research configuration and must not be
required by the public test suite. These tests exercise the same TOML manifest
semantics with fictional example.org sources:
- manifest parsing (TOML [[feed]] tables + legacy one-URL-per-line files)
- inactive feeds are skipped
- provenance metadata fields survive manifest loading
- one dead feed never fails the whole collection run
- --fetch-article enrichment through the canonical web adapter
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from laclaugpt.collect import CollectRecord, collect_rss, collect_web
from laclaugpt.collect.cli import _enrich_rss_articles, load_rss_manifest

TOML_SAMPLE = """\
[[feed]]
name = "example_feed"
feed_url = "https://example.org/feed.xml"
homepage = "https://example.org"
source_family = "synthetic comparison family"
sampling_rationale = "Synthetic fixture for manifest provenance testing."
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


def _write_manifest(text: str = TOML_SAMPLE) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as fh:
        fh.write(text)
        return fh.name


class ManifestLoaderTests(unittest.TestCase):
    def test_manifest_parses_all_active_feeds(self) -> None:
        path = _write_manifest()
        try:
            entries = load_rss_manifest(path)
            names = [e["name"] for e in entries]
            self.assertEqual(names, ["example_feed", "broken_feed"])
        finally:
            Path(path).unlink()

    def test_manifest_entries_carry_provenance(self) -> None:
        path = _write_manifest()
        try:
            entries = {e["name"]: e for e in load_rss_manifest(path)}
            example = entries["example_feed"]
            self.assertEqual(example["source_family"], "synthetic comparison family")
            self.assertIn("Synthetic fixture", example["sampling_rationale"])
            self.assertEqual(example["priority"], "P1")
            self.assertEqual(example["last_verified"], "2026-09-11")
            self.assertEqual(example["homepage"], "https://example.org")
        finally:
            Path(path).unlink()

    def test_inactive_feed_is_skipped(self) -> None:
        path = _write_manifest()
        try:
            names = [e["name"] for e in load_rss_manifest(path)]
            self.assertEqual(names, ["example_feed", "broken_feed"])
            self.assertNotIn("inactive_feed", names)
        finally:
            Path(path).unlink()

    def test_legacy_url_list_still_loads(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write(
                "# comment line\nhttps://a.example/feed\n\n"
                "https://b.example/rss\n"
            )
            path = fh.name
        try:
            entries = load_rss_manifest(path)
            self.assertEqual(
                entries,
                [
                    {"feed_url": "https://a.example/feed"},
                    {"feed_url": "https://b.example/rss"},
                ],
            )
        finally:
            Path(path).unlink()

    def test_empty_manifest_returns_empty(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("# only comments\n\n")
            path = fh.name
        try:
            self.assertEqual(load_rss_manifest(path), [])
        finally:
            Path(path).unlink()


class ManifestProvenanceTests(unittest.TestCase):
    def test_provenance_fields_can_be_stamped_on_records(self) -> None:
        entry = {
            "name": "example_feed",
            "feed_url": "https://example.org/feed.xml",
            "source_family": "synthetic comparison family",
            "sampling_rationale": "synthetic heuristic, not truth",
            "priority": "P1",
            "last_verified": "2026-09-11",
            "homepage": "https://example.org",
        }
        records = [
            CollectRecord(
                source_type="rss",
                native_id="synthetic-1",
                url="https://example.org/1",
                title="Synthetic title",
                collector="rss",
                metadata={
                    "feed_url": entry["feed_url"],
                    "feed_name": entry["name"],
                },
            )
        ]
        for rec in records:
            for key in (
                "source_family",
                "sampling_rationale",
                "priority",
                "last_verified",
                "homepage",
            ):
                if entry.get(key):
                    rec.metadata[f"source_{key}"] = entry[key]
        self.assertEqual(
            records[0].metadata["source_source_family"],
            "synthetic comparison family",
        )
        self.assertEqual(
            records[0].metadata["source_sampling_rationale"],
            "synthetic heuristic, not truth",
        )

    def test_fetch_article_keeps_feed_summary_and_records_status(self) -> None:
        rss_record = CollectRecord(
            source_type="rss",
            native_id="synthetic-guid-9",
            url="https://example.org/article",
            title="Synthetic feed title",
            text="Short synthetic summary",
            collector="rss",
            metadata={
                "feed_url": "https://example.org/feed.xml",
                "source_family": "synthetic comparison family",
            },
        )
        web_record = collect_web(
            "https://example.org/final-article",
            html_text="<p>Full synthetic text</p>",
            http_status=200,
        )
        with patch(
            "laclaugpt.collect.cli._fetch_web_record",
            return_value=web_record,
        ):
            enriched = _enrich_rss_articles([rss_record])[0]
        self.assertEqual(enriched.metadata["article_fetch"]["status"], "ok")
        self.assertEqual(
            enriched.metadata["feed_summary"],
            "Short synthetic summary",
        )
        self.assertIn("Full synthetic text", enriched.text or "")


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
        cli_mod.run(args)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
