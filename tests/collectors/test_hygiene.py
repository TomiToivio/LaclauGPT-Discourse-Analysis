"""Git hygiene: research data roots are never committed (issue #20)."""
from __future__ import annotations

from pathlib import Path

import yaml


def test_gitignore_covers_research_data():
    repo = Path(__file__).resolve().parents[2]
    ignore = (repo / ".gitignore").read_text(encoding="utf-8")
    assert "laclaugpt-brasil-data" in ignore
    assert "data-root" in ignore or "collection-data" in ignore