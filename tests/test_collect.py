"""Offline tests for the collection spine (issue: many sources, one corpus).

No network, no live feeds, no real channel identifiers — synthetic
fixtures only. Telegram is tested through the generic external-collector
adapter boundary.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from laclaugpt.collect import (CollectRecord, CollectionStore, collect_hermes,
                               collect_manual, collect_rss, collect_telegram_message,
                               collect_web, content_hash, normalize_url)

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Test Feed</title>
<item><title>Post One</title><link>https://example.org/a?utm_source=x</link>
<guid>tag:example.org,2026:1</guid><description>&lt;p&gt;Hello world&lt;/p&gt;</description>
<pubDate>Mon, 07 Sep 2026 10:00:00 GMT</pubDate><author>me@example.org (Alice)</author></item>
<item><title>Post Two</title><link>https://example.org/b</link>
<guid>tag:example.org,2026:2</guid><description>Second</description></item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom Feed</title>
<entry><title>Atom Entry</title><link href="https://example.org/atom1"/>
<id>urn:uuid:aaa-bbb</id><summary>Atom text</summary>
<author><name>Bob</name></author>
<updated>2026-09-07T12:00:00Z</updated></entry></feed>"""

WEB_HTML = """<html><head><title>Test Page</title></head><body>
<script>var x=1;</script><article><p>Main political content here.</p></article>
</body></html>"""


class StoreTests(unittest.TestCase):

    def _store(self, tmp: str) -> CollectionStore:
        return CollectionStore(root=Path(tmp) / "collection-data")

    def test_dedup_by_native_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            rec = CollectRecord(source_type="rss", native_id="guid-1",
                                text="x", collector="rss")
            first = store.save(rec)
            again = store.save(CollectRecord(source_type="rss",
                                             native_id="guid-1", text="x",
                                             collector="rss"))
            self.assertIsNotNone(first)
            self.assertIsNone(again)

    def test_dedup_by_normalized_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            a = CollectRecord(source_type="web",
                              url="https://Example.org/a?utm_source=x&keep=1",
                              text="t", collector="web")
            b = CollectRecord(source_type="web",
                              url="https://example.org/a?keep=1&utm_source=y",
                              text="t", collector="web")
            self.assertIsNotNone(store.save(a))
            self.assertIsNone(store.save(b), "normalized URL must dedup")

    def test_no_cross_source_merge_on_same_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            a = store.save(CollectRecord(source_type="rss", text="same text",
                                         collector="rss"))
            b = store.save(CollectRecord(source_type="web", text="same text",
                                         collector="web"))
            self.assertIsNotNone(a)
            self.assertIsNotNone(b, "same text in different sources = different items")


class NormalizeTests(unittest.TestCase):

    def test_normalize_url(self) -> None:
        self.assertEqual(normalize_url("https://Example.org/A"),
                         "https://example.org/A")
        self.assertEqual(
            normalize_url("https://example.org/a?utm_source=x&b=2"),
            "https://example.org/a?b=2")
        self.assertIsNone(normalize_url(None))

    def test_content_hash_stable(self) -> None:
        self.assertEqual(content_hash("a  b"), content_hash("a b"))
        self.assertIsNone(content_hash(None))


class RssTests(unittest.TestCase):

    def test_rss_parsing(self) -> None:
        import feedparser
        parsed = feedparser.parse(RSS_SAMPLE)
        from laclaugpt.collect import _entry_author, _strip_html
        entry = parsed.entries[0]
        rec = CollectRecord(source_type="rss", native_id=entry.id,
                            url=entry.link, title=entry.title,
                            author=_entry_author(entry),
                            text=_strip_html(entry.summary),
                            collector="rss")
        self.assertEqual(rec.native_id, "tag:example.org,2026:1")
        self.assertIn("Alice", rec.author or "")
        self.assertIn("Hello world", rec.text)

    def test_atom_parsing(self) -> None:
        import feedparser
        parsed = feedparser.parse(ATOM_SAMPLE)
        self.assertEqual(len(parsed.entries), 1)
        self.assertEqual(parsed.entries[0].id, "urn:uuid:aaa-bbb")

    def test_fetch_article_enriches_rss_through_web_adapter(self) -> None:
        from laclaugpt.collect.cli import _enrich_rss_articles
        rss_record = CollectRecord(
            source_type="rss", native_id="guid-1",
            url="https://example.org/article", title="Feed title",
            text="Short feed summary", collector="rss",
            metadata={"feed_url": "https://example.org/feed.xml"},
        )
        web_record = collect_web(
            "https://example.org/final-article", html_text=WEB_HTML, http_status=200)
        with patch("laclaugpt.collect.cli._fetch_web_record", return_value=web_record):
            enriched = _enrich_rss_articles([rss_record])[0]
        self.assertIn("Main political content", enriched.text or "")
        self.assertEqual(enriched.metadata["feed_summary"], "Short feed summary")
        self.assertEqual(enriched.metadata["article_fetch"]["status"], "ok")
        self.assertEqual(enriched.metadata["article_fetch"]["final_url"],
                         "https://example.org/final-article")


class WebTests(unittest.TestCase):

    def test_web_normalization_mocked(self) -> None:
        rec = collect_web("https://example.org/page", html_text=WEB_HTML,
                          http_status=200)
        self.assertEqual(rec.native_id, "https://example.org/page")
        self.assertEqual(rec.title, "Test Page")
        self.assertIn("Main political content", rec.text)
        self.assertNotIn("var x=1", rec.text)
        self.assertEqual(rec.collector, "web")


class HermesTests(unittest.TestCase):

    def test_hermes_submission_keeps_commentary_out_of_text(self) -> None:
        payload = {"items": [{
            "source_type": "web", "url": "https://example.org/news",
            "title": "News", "text": "SOURCE TEXT ONLY",
            "hermes_metadata": {"fetched_by": "hermes", "tool": "web"},
            "hermes_commentary": "This looks politically relevant to AI26",
            "tags": ["ai26", "pilot"],
        }]}
        records = collect_hermes(payload)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec.collector, "hermes")
        self.assertEqual(rec.text, "SOURCE TEXT ONLY")
        self.assertNotIn("politically relevant", rec.text)
        self.assertIn("politically relevant", rec.metadata["hermes_commentary"])


class ManualTests(unittest.TestCase):

    def test_manual_text(self) -> None:
        rec = collect_manual(text="field note", title="Note",
                             author="Synthetic Researcher", notes="pilot")
        self.assertEqual(rec.collector, "manual")
        self.assertEqual(rec.text, "field note")

    def test_manual_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "note.md"
            p.write_text("# markdown source", encoding="utf-8")
            rec = collect_manual(file_path=str(p), title="File")
            self.assertIn("markdown source", rec.text)


class TelegramTests(unittest.TestCase):

    def test_external_event_normalization(self) -> None:
        event = {"_id": "synthetic-64ff1", "message_id": "synthetic-64ff1",
                 "channel": "synthetic_ai_news",
                 "text": "channel post",
                 "url": "https://example.org/telegram/synthetic-64ff1",
                 "published_at": "2026-09-07T09:00:00Z"}
        rec = collect_telegram_message(event)
        self.assertEqual(rec.source_type, "telegram")
        self.assertEqual(rec.collector, "telegram")
        self.assertEqual(rec.platform, "telegram")
        self.assertEqual(rec.native_id, "synthetic-64ff1")
        self.assertEqual(rec.metadata["upstream_source"], "external-telegram-event")
        self.assertEqual(rec.imported_from, "external-telegram-collector")
        self.assertNotIn("vasama", json.dumps(rec.metadata).lower())


class CliTests(unittest.TestCase):

    def test_cli_registers_collect(self) -> None:
        from laclaugpt.cli import parser
        args = parser().parse_args(["collect", "manual", "--text", "hi",
                                    "--title", "t"])
        self.assertEqual(args.command, "collect")
        self.assertEqual(args.collect_target, "manual")

    def test_cli_manual_end_to_end(self) -> None:
        import laclaugpt.cli as cli
        with tempfile.TemporaryDirectory() as tmp:
            import laclaugpt.collect as collect_mod
            old_root = collect_mod.COLLECTION_ROOT
            collect_mod.COLLECTION_ROOT = Path(tmp)
            try:
                rc = cli.main(["collect", "manual", "--text", "hello",
                               "--title", "manual test"])
            finally:
                collect_mod.COLLECTION_ROOT = old_root
            self.assertEqual(rc, 0)
            out = Path(tmp) / "normalized" / "manual.jsonl"
            self.assertTrue(out.exists())
            payload = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(payload["source"]["source_type"], "manual")
            self.assertEqual(payload["ingestion"]["collector"], "manual")


if __name__ == "__main__":
    unittest.main()
