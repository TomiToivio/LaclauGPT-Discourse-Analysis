"""Regression checks for the AI26 live-dashboard export boundary."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "ai26_runtime" / "export_dashboard_jsonl.py"
SERVICE = ROOT / "deploy" / "systemd" / "ai26" / "ai26-export.service"


def test_dashboard_export_is_atomic() -> None:
    source = EXPORTER.read_text(encoding="utf-8")
    assert "os.replace(" in source
    assert '.open("w", encoding="utf-8")' in source
    assert '.open("a", encoding="utf-8")' not in source


def test_systemd_export_does_not_truncate_live_files_before_export() -> None:
    source = SERVICE.read_text(encoding="utf-8")
    assert "ExecStartPre" not in source
    assert "export_dashboard_jsonl.py" in source
