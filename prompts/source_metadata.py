# -*- coding: utf-8 -*-
"""Source metadata module: describes each data source for the prompts.

Injects: platform, country/language, how the data was collected, and
what is known about the item's metadata. For TikTok mobile recordings
(v1 data), on-screen metadata (username, caption) is often the *only*
metadata — the frame-analysis stage is therefore instructed to extract
everything visible.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SourceMetadata:
    platform: str
    country: str
    language: str
    collection: str          # how the data was collected
    has_metadata: bool       # whether structured metadata exists (CSV columns)
    notes: str = ""

    def prompt_text(self) -> str:
        lines = [
            "### **Source Description**",
            f"- Platform: {self.platform}",
            f"- Country: {self.country} (language: {self.language})",
            f"- Collection: {self.collection}",
        ]
        if self.has_metadata:
            lines.append("- Structured source metadata is available in the input row; "
                         "use only fields that are actually present.")
        else:
            lines.append("- Structured source metadata is not available for this item. "
                         "Do not infer author, time, platform details, or provenance.")
        if self.notes:
            lines.append(f"- Notes: {self.notes}")
        return "\n".join(lines)


def tiktok_election(country: str, language: str) -> SourceMetadata:
    return SourceMetadata(
        platform="TikTok",
        country=country,
        language=language,
        collection=("Screen recordings of TikTok feeds collected during "
                    "data collection; videos split from feed recordings "
                    "by scroll detection."),
        has_metadata=False,
        notes=("If a username is visible on screen, include it in your "
               "output as observed_username. Do not guess beyond what is "
               "visible."),
    )


def tiktok_with_metadata(country: str, language: str,
                         collection: str = "API/scraper collection") -> SourceMetadata:
    return SourceMetadata(
        platform="TikTok",
        country=country,
        language=language,
        collection=collection,
        has_metadata=True,
    )
