"""Study configuration loading (accounts, window, platform toggles)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
        """All collection targets as flat (name, kind, platform, handle) rows."""
        rows: list[dict] = []
        for kind, group in (("candidate", self.candidates), ("party", self.parties)):
            for entity in group:
                handles = entity.get("handles") or entity.get("accounts") or {}
                for platform in self.platforms:
                    for handle in handles.get(platform) or []:
                        rows.append({"name": entity["name"], "kind": kind,
                                     "platform": platform, "handle": handle})
        return rows

    def local_today(self) -> date:
        """Current date in the study timezone, falling back to UTC if unavailable."""
        try:
            tz = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            tz = timezone.utc
        return datetime.now(tz).date()

    def in_window(self, today: date | None = None) -> bool:
        return self.start <= (today or self.local_today()) <= self.end

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
    """Study expectation: seven main presidential candidates (issue #20)."""
    return 7 if (data.get("candidates") or data.get("parties")) else 0


def load_config(path: str | Path) -> StudyConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"collector config {path!s} must contain a YAML mapping")
    return StudyConfig(data, str(path))
