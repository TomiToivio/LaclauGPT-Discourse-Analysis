"""Issue #73 phase 1.3: screen-metadata OCR lift tests (digital ethnography).

The HEPP24 videos are screen recordings — the poster identity shown in the
UI is metadata the legacy CSV lacks. These tests lock the OCR lift rules.
"""
from __future__ import annotations

import unittest

from ep24_screen_metadata import (ScreenMetadata, extract_screen_metadata,
                                  lift_engagement, lift_handle, lift_platform,
                                  merge_into_asr_record)


IG_OCR = """seuraa
Kokoomus
@kokoomus
34 512 tykkäystä
1 024 kommenttia
Näytä käännös"""


TT_OCR = """For You
 @perussuomalaiset
Perussuomalaiset
12,4K
891
Jaa"""


class HandleTests(unittest.TestCase):

    def test_lifts_handle_from_ig_ui(self) -> None:
        self.assertEqual(lift_handle(IG_OCR), "kokoomus")

    def test_lifts_handle_from_tt_ui(self) -> None:
        self.assertEqual(lift_handle(TT_OCR), "perussuomalaiset")

    def test_no_handle_returns_none(self) -> None:
        self.assertIsNone(lift_handle("ei yhtään handlea täällä"))


class PlatformTests(unittest.TestCase):

    def test_ig_chrome(self) -> None:
        self.assertEqual(lift_platform(IG_OCR), "Instagram")

    def test_tt_chrome(self) -> None:
        self.assertEqual(lift_platform(TT_OCR), "TikTok")

    def test_unknown_chrome(self) -> None:
        self.assertIsNone(lift_platform("kaksi käryää pöydällä"))


class EngagementTests(unittest.TestCase):

    def test_fi_counters(self) -> None:
        got = lift_engagement(IG_OCR)
        self.assertEqual(got["likes_text"], "34 512")
        self.assertEqual(got["comments_text"], "1 024")

    def test_tt_k_suffix(self) -> None:
        got = lift_engagement(TT_OCR)
        self.assertIn("12,4K", got["bare_counters"])
        self.assertNotIn("likes_text", got)  # icon-only: no label


class ExtractionTests(unittest.TestCase):

    def test_full_lift_ig(self) -> None:
        meta = extract_screen_metadata(IG_OCR, confidence=0.93)
        self.assertEqual(meta.handle, "kokoomus")
        self.assertEqual(meta.display_name, "Kokoomus")
        self.assertEqual(meta.platform, "Instagram")
        self.assertEqual(meta.source, "ocr")
        self.assertEqual(meta.review_status, "proposed")

    def test_record_is_provenance_marked(self) -> None:
        meta = extract_screen_metadata(TT_OCR)
        record = merge_into_asr_record({"document_id": "PL1"}, TT_OCR)
        sm = record["screen_metadata"]
        self.assertEqual(sm["review_status"], "proposed")
        self.assertEqual(sm["source"], "ocr")
        self.assertEqual(record["document_id"], "PL1")


if __name__ == "__main__":
    unittest.main()