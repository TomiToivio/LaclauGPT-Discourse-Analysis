"""Study configuration loading (accounts, window, platform toggles)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


class StudyConfig:
    """Parsed study config: window, platforms, candidates, parties, groups."""

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
        # Generic study groups (STUDY_TEMPLATE.yaml "groups"): free-form target
        # sets for non-election studies (researchers, labs, movements,
        # organisations). Election-specific groups ride as metadata.
        self.groups: list[dict] = [
            g for g in (data.get("groups") or []) if isinstance(g, dict)]
        # Handles are stored EXACTLY as supplied; empty or whitespace-only
        # handles fail loudly here instead of being silently corrected later.
        self._reject_invalid_handles()
        self.expected_candidates = int(data.get("expected_candidates",
                                                _infer_expected(data)))
        self.study = data.get("study", "unnamed")

    def _reject_invalid_handles(self) -> None:
        """Fail visibly on empty/whitespace/non-string handles (no silent fixes).

        Handles are research identifiers: they are stored exactly as supplied.
        A typo must surface at config-load time, never as a silently repaired
        tour URL pointing at the wrong account.
        """
        bad: list[str] = []
        for entity in self.candidates + self.parties:
            handles = entity.get("handles") or entity.get("accounts") or {}
            for platform, values in handles.items():
                for value in values or []:
                    if not isinstance(value, str) or not value.strip():
                        bad.append(f"{entity.get('name', '?')}/{platform}: {value!r}")
        for group in self.groups:
            handles = group.get("accounts") or group.get("handles") or {}
            for platform, values in handles.items():
                for value in values or []:
                    if not isinstance(value, str) or not value.strip():
                        bad.append(f"{group.get('id', '?')}/{platform}: {value!r}")
        if bad:
            raise ValueError(
                "study config contains empty/whitespace/non-string handles "
                "(handles are never silently corrected): " + "; ".join(bad))

    def accounts(self) -> list[dict]:
        """All collection targets as flat (name, kind, platform, handle) rows.

        Election studies keep their legacy candidate/party shape; generic
        studies use `groups` entries. Every row carries `group_id` and
        `formation_seed` as sampling provenance metadata (never used as an
        automatic discourse label — a group's seed category is provenance,
        not truth about any post).
        """
        rows: list[dict] = []
        for kind, group in (("candidate", self.candidates), ("party", self.parties)):
            for entity in group:
                handles = entity.get("handles") or entity.get("accounts") or {}
                for platform in self.platforms:
                    for handle in handles.get(platform) or []:
                        rows.append({"name": entity["name"], "kind": kind,
                                     "platform": platform, "handle": handle,
                                     "group_id": kind,
                                     "formation_seed": entity.get("formation_seed", "")})
        for group in self.groups:
            handles = group.get("accounts") or group.get("handles") or {}
            for platform in self.platforms:
                for handle in handles.get(platform) or []:
                    rows.append({
                        "name": group.get("name") or group.get("id", ""),
                        "kind": "group",
                        "platform": platform, "handle": handle,
                        "group_id": group.get("id", ""),
                        "formation_seed": _formation_seed(group),
                        "arena": group.get("arena", ""),
                        "notes": group.get("notes", ""),
                    })
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


def _formation_seed(group: dict) -> str:
    """Sampling-provenance seed of a generic group; empty string is allowed.

    This is a SAMPLING label recorded for provenance. It must never be used
    as an automatic discourse label for captured posts — documents keep
    requiring discourse analysis regardless of the group that captured them.
    """
    seed = group.get("formation_seed")
    return "" if seed is None else str(seed)


def _infer_expected(data: dict) -> int:
    """Study expectation: seven main presidential candidates (issue #20)."""
    return 7 if (data.get("candidates") or data.get("parties")) else 0


def load_config(path: str | Path) -> StudyConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"collector config {path!s} must contain a YAML mapping")
    return StudyConfig(data, str(path))
