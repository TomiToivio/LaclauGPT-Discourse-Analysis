"""Offline tests: minet CSV + Zeeschuimer NDJSON into the collection spine.

Synthetic fixtures only — minet-produced CSV shapes and Zeeschuimer
NDJSON export shapes, no network, no real platform data.
"""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from laclaugpt.collect import CollectionStore
from laclaugpt.collect.minet_zeeschuimer import (
    collect_minet_collector, collect_minet_extract, collect_zeeschuimer,
    iter_zeeschuimer)

MINET_EXTRACT_CSV = """extract_original_index,plain_content,content,url,author,date,fetch_error,extract_error
0,First extracted article,First extracted article,https://example.org/a,Alice,2026-09-07,,
1,Second article,Second article,https://example.org/b,Bob,2026-09-07,,
2,,,,https://example.org/c,,,"""

MINET_COLLECTOR_CSV = """id,text,user_screen_name,created_at,url
100,Tweet text here,alice,2026-09-07T10:00:00Z,https://x.com/a/100
101,youtube caption,bob,2026-09-07T11:00:00Z,https://youtu.be/x"""


def _write_csv(path: Path, content: str) -> str:
    path.write_text(content, encoding="utf-8")
    return str(path)


ZEES_LINE_1 = json.dumps({
    "data": {"id": "777", "desc": "TikTok post description",
             "author": {"unique_id": "creator1"},
             "create_time": "2026-09-07 12:00:00"},
    "timestamp": 1760000000000, "platform": "tiktok",
    "source": "https://www.tiktok.com/", "search": "",
    "complete": True, "item_index": 0})

ZEES_LINE_2 = json.dumps({
    "data": {"pk": "888", "caption": {"text": "IG caption text"},
             "user": {"username": "creator2"}, "taken_at": 1760000500},
    "timestamp": 1760000500000, "platform": "instagram",
    "source": "https://www.instagram.com/", "search": "",
    "complete": False, "item_index": 1})


class MinetExtractTests(unittest.TestCase):

    def test_minet_extract_to_spine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_csv(Path(tmp) / "extract.csv",
                                  MINET_EXTRACT_CSV)
            records = collect_minet_extract(csv_path)
            self.assertEqual(len(records), 2)  # errored row skipped
            rec = records[0]
            self.assertEqual(rec.source_type, "minet")
            self.assertEqual(rec.collector, "minet")
            self.assertEqual(rec.text, "First extracted article")
            self.assertEqual(rec.author, "Alice")
            self.assertIn("extract.csv", rec.imported_from)

    def test_minet_extract_dedup_via_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_csv(Path(tmp) / "extract.csv",
                                  MINET_EXTRACT_CSV)
            store = CollectionStore(root=Path(tmp) / "collection-data")
            records = collect_minet_extract(csv_path)
            saved, skipped = store.save_many(records)
            self.assertEqual(saved, 2)
            saved2, skipped2 = store.save_many(records)
            self.assertEqual((saved2, skipped2), (0, 2),
                             "re-import must not duplicate")


class MinetCollectorTests(unittest.TestCase):

    def test_minet_collector_to_spine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = _write_csv(Path(tmp) / "collector.csv",
                                  MINET_COLLECTOR_CSV)
            records = collect_minet_collector(csv_path, platform="twitter")
            self.assertEqual(len(records), 2)
            rec = records[0]
            self.assertEqual(rec.platform, "minet-twitter")
            self.assertEqual(rec.native_id, "100")
            self.assertEqual(rec.author, "alice")
            self.assertIn("Tweet text", rec.text)


class ZeeschuimerTests(unittest.TestCase):

    def test_iter_ndjson_and_array(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            nd = Path(tmp) / "export.ndjson"
            nd.write_text(ZEES_LINE_1 + "\n" + ZEES_LINE_2 + "\n",
                          encoding="utf-8")
            self.assertEqual(len(list(iter_zeeschuimer(str(nd)))), 2)
            arr = Path(tmp) / "export.json"
            arr.write_text(json.dumps([json.loads(ZEES_LINE_1)]),
                           encoding="utf-8")
            self.assertEqual(len(list(iter_zeeschuimer(str(arr)))), 1)

    def test_zeeschuimer_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            nd = Path(tmp) / "export.ndjson"
            nd.write_text(ZEES_LINE_1 + "\n" + ZEES_LINE_2 + "\n",
                          encoding="utf-8")
            records = collect_zeeschuimer(str(nd))
            self.assertEqual(len(records), 2)
            first = records[0]
            self.assertEqual(first.source_type, "zeeschuimer")
            self.assertEqual(first.platform, "tiktok")
            self.assertEqual(first.native_id, "777")
            self.assertEqual(first.author, "creator1")
            self.assertIn("TikTok post description", first.text)
            self.assertTrue(first.metadata["zeeschuimer"]["complete"])
            second = records[1]
            self.assertEqual(second.platform, "instagram")
            self.assertIn("IG caption text", second.text)
            self.assertFalse(second.metadata["zeeschuimer"]["complete"])

    def test_zeeschuimer_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            nd = Path(tmp) / "export.ndjson"
            nd.write_text(ZEES_LINE_1 + "\n", encoding="utf-8")
            store = CollectionStore(root=Path(tmp) / "collection-data")
            records = collect_zeeschuimer(str(nd))
            saved, _ = store.save_many(records)
            saved2, skipped2 = store.save_many(records)
            self.assertEqual(saved, 1)
            self.assertEqual((saved2, skipped2), (0, 1))

    def test_platform_text_field_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            item = json.dumps({
                "data": {"id": "9", "body_text": "custom field"},
                "platform": "custom", "timestamp": 0, "complete": True})
            nd = Path(tmp) / "x.ndjson"
            nd.write_text(item, encoding="utf-8")
            records = collect_zeeschuimer(str(nd),
                                          text_fields=("body_text",))
            self.assertIn("custom field", records[0].text or "")


if __name__ == "__main__":
    unittest.main()