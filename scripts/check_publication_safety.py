#!/usr/bin/env python3
"""Fail CI/pre-commit when obviously restricted research artifacts are tracked.

This is a lightweight repository guard, not a privacy or secret-scanning product.
It intentionally focuses on high-signal path/extension checks and a small set of
production-data indicators. Human disclosure review remains mandatory.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_RESTRICTED_ROOT_FILES = {
    "data/README.md",
    "sources/README.md",
}
ALLOWED_SOURCE_PREFIX = "sources/codebooks/"

FORBIDDEN_ROOT_PREFIXES = (
    "private_data/",
    "restricted/",
    "scratch/",
    "secrets/",
)

FORBIDDEN_EXTENSIONS = {
    ".sqlite",
    ".sqlite3",
    ".duckdb",
    ".parquet",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".wav",
    ".mp3",
    ".m4a",
}

# High-signal production/research-storage patterns. Safe example/test URLs may
# be explicitly marked with PUBLICATION-SAFETY: allow on the same line.
SUSPICIOUS_CONTENT = (
    re.compile(r"https?://a3s\.fi/swift/v1/", re.IGNORECASE),
    re.compile(r"/scratch/project_[0-9]+/", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"][^'\"]+['\"]"),
)

TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".csv", ".sh", ".ps1", ".env", "",
}


def tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def path_violations(paths: list[str]) -> list[str]:
    problems: list[str] = []
    for rel in paths:
        p = Path(rel)
        lowered = rel.lower()

        if rel.startswith("data/") and rel not in ALLOWED_RESTRICTED_ROOT_FILES:
            problems.append(f"tracked runtime research data path: {rel}")

        if rel.startswith("sources/"):
            allowed = rel in ALLOWED_RESTRICTED_ROOT_FILES or rel.startswith(ALLOWED_SOURCE_PREFIX)
            if not allowed:
                problems.append(f"tracked restricted/copyright source path: {rel}")

        if lowered.startswith(FORBIDDEN_ROOT_PREFIXES):
            problems.append(f"tracked restricted/private root: {rel}")

        if p.suffix.lower() in FORBIDDEN_EXTENSIONS:
            problems.append(f"tracked database/media artifact ({p.suffix}): {rel}")

        if p.name == ".env" or p.name.startswith(".env.") and p.name != ".env.example":
            problems.append(f"tracked environment/secrets file: {rel}")

    return problems


def content_violations(paths: list[str]) -> list[str]:
    problems: list[str] = []
    for rel in paths:
        path = ROOT / rel
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for lineno, line in enumerate(text.splitlines(), 1):
            if "PUBLICATION-SAFETY: allow" in line:
                continue
            for pattern in SUSPICIOUS_CONTENT:
                if pattern.search(line):
                    problems.append(f"suspicious production-data/secret indicator: {rel}:{lineno}")
                    break
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths-only",
        action="store_true",
        help="skip content indicators and check tracked paths/extensions only",
    )
    args = parser.parse_args()

    try:
        paths = tracked_files()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"publication-safety: cannot enumerate tracked files: {exc}", file=sys.stderr)
        return 2

    problems = path_violations(paths)
    if not args.paths_only:
        problems.extend(content_violations(paths))

    if problems:
        print("Publication-safety guard found items requiring review:", file=sys.stderr)
        for problem in sorted(set(problems)):
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nDo not bypass this by renaming research data. Move restricted material "
            "to controlled storage or document a genuinely safe fixture exception.",
            file=sys.stderr,
        )
        return 1

    print("publication-safety: no high-signal tracked research-data violations found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
