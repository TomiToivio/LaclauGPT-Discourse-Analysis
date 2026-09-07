"""Study configuration loading (accounts, window, platform toggles)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml


class StudyConfig:
    """Parsed study config: window, platforms, candidates and parties."""

    def __init__(self, data: dict[str, Any], source: str) -> None:
        self.source = source
        window = data.get("window") or {}
        self.start: date = _date(window.get("start"))
        self.end: date = _date(window.get("end"))
        self.timezone = data.get("timezone", "UTC")
        platforms = data.get("platforms") or {}
        self.platforms = [p for p, cfg in platforms.items()
                          if isinstance(cfg, dict) and cfg.get("enabled")]
        self.platform_urls = {p: (cfg.get("base_urls") or [])
                              for p, cfg in platforms.items()
                              if isinstance(cfg, dict)}
        self.candidates: list[dict] = list(data.get("candidates") or [])
        self.parties: list[dict] = list(data.get("parties") or [])
        self.expected_candidates = int(data.get("expected_candidates",
                                                _infer_expected(data)))
        self.study = data.get("study", "unnamed")

    def accounts(self) -> list[dict]:
        """All collection targets as flat (name, kind, platform, handle) rows.

        Accepts both config shapes used in this repo: entity["handles"]
        (collector original) and entity["accounts"] (skeleton commit
        b419ac1). Keys other than the entity metadata are treated as
        platform -> handle-list mappings.
        """
        rows: list[dict] = []
        meta_keys = {"id", "name", "party", "notes", "comment"}
        for kind, group in (("candidate", self.candidates), ("party", self.parties)):
            for entity in group:
                handles = entity.get("handles") or entity.get("accounts") or {}
                for platform in self.platforms:
                    for handle in handles.get(platform) or []:
                        rows.append({"name": entity["name"], "kind": kind,
                                     "platform": platform, "handle": handle})
        return rows

    def in_window(self, today: date | None = None) -> bool:
        return self.start <= (today or date.today()) <= self.end

    def missing_candidates(self) -> list[str]:
        """Flag expected-but-unlisted candidates (never invented)."""
        if self.expected_candidates <= 0:
            return []
        have = {c["name"] for c in self.candidates}
        return [f"expected {self.expected_candidates} candidates, "
                f"{len(have)} configured"] if len(have) < self.expected_candidates else []


def _date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _infer_expected(data: dict) -> int:
    """Study expectation: seven main presidential candidates (issue #20).

    The researcher said SEVEN; six are supplied. expected_candidates may
    be set explicitly in the YAML; default 7 keeps the gap flagged.
    """
    return 7 if (data.get("candidates") or data.get("parties")) else 0


def load_config(path: str | Path) -> StudyConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return StudyConfig(data, str(path))