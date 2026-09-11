# -*- coding: utf-8 -*-
"""EP24 screen-metadata extraction: OCR the on-screen UI, not just captions.

Issue #73 phase 1.3 (extended per Tomi's request): the HEPP24 videos are
screen recordings of Instagram/TikTok captured via digital ethnography.
The recording UI shows the *actual* poster (@handle, display name, platform
chrome, engagement counts) — metadata that is missing or unreliable in the
legacy CSV columns. This module OCRs the keyframes and lifts the on-screen
identity metadata into the document record.

Extraction contract (INV_HUMAN_REVIEW): everything lifted from the screen
is marked `screen_metadata` with `source: ocr` and `review_status:
proposed`. Nothing here is a validated finding until a human checks it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# On-screen UI patterns observed in HEPP24 screen recordings (IG/TikTok).
HANDLE_RE = re.compile(r"@([A-Za-z0-9._]{2,30})")
# Verified-badge/username rows: "Full Name\n@handle" — the handle line is
# the reliable anchor; display name is captured as-is when adjacent.
PLATFORM_HINTS = {
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "reels": "Instagram",
    "for you": "TikTok",
    "seuraa": "Instagram",    # fi IG UI: "Seuraa" (follow button row)
    "seuraat": "Instagram",   # fi IG UI: "Seuraat" (following tab)
    "seuraamme": "TikTok",    # fi UI variant
    "nyyt tilaa": "TikTok",
    "following": None,        # resolved via platform detection below
}


@dataclass
class ScreenMetadata:
    """On-screen identity metadata lifted from video frames via OCR."""
    handle: str | None = None            # @username as shown on screen
    display_name: str | None = None      # profile display name if adjacent
    platform: str | None = None          # Instagram | TikTok (from UI chrome)
    engagement: dict = field(default_factory=dict)  # likes/comments counters
    ocr_confidence: float | None = None
    source: str = "ocr"                  # provenance: lifted from frames
    review_status: str = "proposed"      # human must verify


def lift_handle(ocr_text: str) -> str | None:
    """First @handle-looking token in OCR text (UI rows put handles first)."""
    match = HANDLE_RE.search(ocr_text or "")
    if not match:
        return None
    return match.group(1)


def lift_platform(ocr_text: str) -> str | None:
    """Platform from UI chrome keywords (case-insensitive, fi/en)."""
    low = (ocr_text or "").lower()
    for hint, platform in PLATFORM_HINTS.items():
        if hint in low:
            # "following" is ambiguous: decide by other hints present
            if hint == "following":
                continue
            return platform
    return None


def lift_engagement(ocr_text: str) -> dict:
    """Like/comment/share counters as they appear next to UI icons.

    Two UI conventions: labelled text ("34 512 tykkäystä") and icon-only
    counters where the number sits alone on a line (TikTok "12,4K" above
    the heart icon). Icon-only lines are captured as bare counters; they
    stay `proposed` until human review maps them to kinds.
    """
    out: dict = {}
    low = (ocr_text or "").lower()
    m = re.search(r"([\d.,\s]+)\s*(?:tykk|like)", low)
    if m:
        out["likes_text"] = m.group(1).strip()
    m = re.search(r"([\d.,\s]+)\s*(?:komment|comment)", low)
    if m:
        out["comments_text"] = m.group(1).strip()
    m = re.search(r"([\d.,\s]+)\s*(?:jako|share)", low)
    if m:
        out["shares_text"] = m.group(1).strip()
    if not out:
        # icon-only counters: standalone short numeric lines (e.g. "12,4K")
        bare = re.findall(r"^\s*([\d.,]+[KkMk]?)\s*$", ocr_text or "", re.M)
        if bare:
            out["bare_counters"] = bare[:4]
    return out


def extract_screen_metadata(ocr_text: str, *,
                            confidence: float | None = None) -> ScreenMetadata:
    """Build ScreenMetadata from combined keyframe OCR text."""
    handle = lift_handle(ocr_text)
    display_name = None
    if handle:
        # Display name heuristic: the line above/below the handle line that
        # is not itself a handle and not UI chrome.
        for line in (ocr_text or "").splitlines():
            line = line.strip()
            if handle in line or not line:
                continue
            if line.startswith("@") or line.lower().startswith(("seuraa", "follow")):
                continue
            if 2 < len(line) <= 60 and not line.isdigit():
                display_name = line
                break
    return ScreenMetadata(
        handle=handle,
        display_name=display_name,
        platform=lift_platform(ocr_text),
        engagement=lift_engagement(ocr_text),
        ocr_confidence=confidence,
    )


def screen_metadata_record(meta: ScreenMetadata) -> dict:
    """JSONL-ready provenance record (always marked proposed/ocr)."""
    return {
        "screen_metadata": {
            "handle": meta.handle,
            "display_name": meta.display_name,
            "platform": meta.platform,
            "engagement": meta.engagement,
            "ocr_confidence": meta.ocr_confidence,
            "source": meta.source,
            "review_status": meta.review_status,
        }
    }


def merge_into_asr_record(record: dict, ocr_text: str, *,
                          confidence: float | None = None) -> dict:
    """Attach screen metadata to an ASR JSONL record (phase 1.2 output)."""
    record.update(screen_metadata_record(
        extract_screen_metadata(ocr_text, confidence=confidence)))
    return record