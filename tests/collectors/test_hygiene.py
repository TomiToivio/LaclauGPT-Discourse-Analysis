"""Git and parser-lineage hygiene for the public collector."""
from __future__ import annotations

from pathlib import Path


def test_gitignore_covers_research_data():
    repo = Path(__file__).resolve().parents[2]
    ignore = (repo / ".gitignore").read_text(encoding="utf-8")
    assert "laclaugpt-brasil-data" in ignore
    assert "data-root" in ignore or "collection-data" in ignore


def test_platform_parsers_are_laclaugpt_native():
    repo = Path(__file__).resolve().parents[2]
    for name in ("tiktok.py", "instagram.py", "twitter.py", "common.py"):
        text = (repo / "collector" / "modules" / name).read_text(encoding="utf-8")
        assert "Adapted from Zeeschuimer" not in text
        assert "Python ports of the Zeeschuimer" not in text
        assert "MPL-2.0" not in text
        assert "_zs_" not in text
