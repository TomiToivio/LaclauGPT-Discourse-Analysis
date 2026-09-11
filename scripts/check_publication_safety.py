#!/usr/bin/env python3
"""Fail CI/pre-commit when obviously restricted or secret material is tracked.

This is a lightweight repository guard, not a replacement for GitHub secret
scanning, institutional disclosure review, or a forensic history audit. It aims
to catch the most common accidental publication routes in a public research
repository: raw/derived data, database/media dumps, browser/session state,
credentials, private infrastructure paths and high-confidence token formats.
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
    "raw/",
    "raw-data/",
    "raw_data/",
    "derived/",
    "derived-data/",
    "derived_data/",
    "output/",
    "outputs/",
    "exports/",
    "runs/",
    "logs/",
    "tmp/",
    "temp/",
    "checkpoints/",
    "transcripts/",
    "screenshots/",
    "recordings/",
    "media-downloads/",
    "media_downloads/",
    "browser-profiles/",
    "browser_profiles/",
    "config/sources/",
    "deploy/systemd/",
    "scripts/ep24/",
    "scripts/legacy_ep24/",
)

FORBIDDEN_EP24_PATHS = {
    "legacy_asr.py",
    "legacy_fetch.py",
    "legacy_full_pipeline.py",
    "legacy_mm_pipeline.py",
    "legacy_pipeline.py",
    "legacy_screen_metadata.py",
}

FORBIDDEN_EXTENSIONS = {
    ".sqlite", ".sqlite3", ".duckdb", ".db", ".bson", ".rdb", ".aof",
    ".dump", ".backup", ".bak", ".parquet", ".mp4", ".mov", ".avi",
    ".mkv", ".wav", ".mp3", ".m4a", ".session", ".pem", ".key",
    ".p12", ".pfx", ".jks", ".keystore", ".kdbx", ".har", ".zip",
    ".tar", ".gz", ".tgz", ".7z", ".rar",
}

FORBIDDEN_FILENAMES = {
    "credentials.json",
    "application_default_credentials.json",
    "token.json",
    "cookies.txt",
    "cookies.json",
    "cookies.sqlite",
    "login data",
    "web data",
    "local state",
    ".netrc",
}

_CREDENTIAL_NAMES = (
    r"api[_-]?key|api[_-]?token|access[_-]?token|refresh[_-]?token|"
    r"secret[_-]?key|client[_-]?secret|password|passwd|telegram[_-]?api[_-]?hash"
)
_PLACEHOLDER_NEGATIVE = (
    r"(?!\$\{)(?!<)(?!example\b)(?!changeme\b)(?!placeholder\b)"
    r"(?!dummy\b)(?!test\b)(?!synthetic\b)(?!none\b)(?!null\b)"
)
_LINE_END = r"(?=\s*(?:#.*)?$)"

SUSPICIOUS_CONTENT = (
    re.compile(r"https?://a3s\.fi/swift/v1/", re.IGNORECASE),
    re.compile(
        rf"(?i)\b({_CREDENTIAL_NAMES})\b\s*[:=]\s*['\"]"
        rf"{_PLACEHOLDER_NEGATIVE}[^'\"]{{8,}}['\"]{_LINE_END}"
    ),
    re.compile(
        rf"(?i)\b({_CREDENTIAL_NAMES})\b\s*[:=]\s*{_PLACEHOLDER_NEGATIVE}"
        rf"[A-Za-z0-9_./+=:@-]{{8,}}{_LINE_END}"
    ),
    re.compile(
        r"(?i)\b(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|mariadb|redis|rediss)://"
        r"[^\s:/@]+:[^\s/@]+@"
    ),
    # Known private deployment markers that previously appeared in the public
    # AI26 runtime history. Keep the generic/public code, but prevent these
    # concrete operational identifiers from being reintroduced into tracked text.
    re.compile(r"\bvasama_ai\b", re.IGNORECASE),
    re.compile(r"\bLaskin01\b", re.IGNORECASE),
    re.compile(r"/mnt/workspace/LaclauGPT-Discourse-Analysis", re.IGNORECASE),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?<![A-Za-z0-9])(?:/home|/Users|/users)/"
        r"(?!user/|username/|example/)[A-Za-z0-9._-]+/"
    ),
    re.compile(r"(?i)\b[A-Z]:\\Users\\(?!user\\|username\\|example\\)[^\\\s]+\\"),
    re.compile(
        r"(?<![A-Za-z0-9])/(?:scratch|projappl|project)/"
        r"project_[A-Za-z0-9._-]+(?:/|$)"
    ),
    re.compile(
        r"(?<!\d)(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|"
        r"100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])(?:\.\d{1,3}){2})(?!\d)"
    ),
)

TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".csv", ".sh", ".ps1", ".env", ".service", ".timer", "",
}


def tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def path_violations(paths: list[str]) -> list[str]:
    problems: list[str] = []
    for rel in paths:
        p = Path(rel)
        lowered = rel.lower()
        name = p.name.lower()

        if rel.startswith("data/") and rel not in ALLOWED_RESTRICTED_ROOT_FILES:
            problems.append(f"tracked runtime research data path: {rel}")

        if rel.startswith("sources/"):
            allowed = rel in ALLOWED_RESTRICTED_ROOT_FILES or rel.startswith(ALLOWED_SOURCE_PREFIX)
            if not allowed:
                problems.append(f"tracked restricted/copyright source path: {rel}")

        if lowered.startswith(FORBIDDEN_ROOT_PREFIXES):
            problems.append(f"tracked restricted/private runtime root: {rel}")

        # EP24 is an institutional research project with a stricter publication
        # boundary than this public code repository. High-level Markdown history
        # may mention it, but operational code/config/tests/codebooks stay local.
        if "ep24" in lowered and p.suffix.lower() != ".md":
            problems.append(f"tracked EP24 operational artifact: {rel}")
        if rel in FORBIDDEN_EP24_PATHS or "legacy_roihu" in lowered:
            problems.append(f"tracked renamed EP24 operational artifact: {rel}")
        if rel.startswith("sources/codebooks/") and "ep24" in lowered:
            problems.append(f"tracked EP24 operational codebook: {rel}")

        if p.suffix.lower() in FORBIDDEN_EXTENSIONS:
            problems.append(f"tracked database/media/auth/archive artifact ({p.suffix}): {rel}")

        credential_json = (
            name.startswith("client_secret")
            or name.startswith("service-account")
            or name.startswith("service_account")
            or (name.startswith("credentials") and name.endswith(".json"))
        )
        if name in FORBIDDEN_FILENAMES or credential_json:
            problems.append(f"tracked credential/session filename: {rel}")

        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            problems.append(f"tracked environment/secrets file: {rel}")

        if name.endswith(".session-journal") or name.startswith("cookies.sqlite"):
            problems.append(f"tracked browser/session state: {rel}")

        if rel.startswith("ai26_runtime/") and p.suffix.lower() in {".jsonl", ".csv", ".log", ".pid"}:
            problems.append(f"tracked AI26 runtime output: {rel}")

        if rel.startswith("deploy/") and any(part in name for part in (".private.", ".local.")):
            problems.append(f"tracked private deployment overlay: {rel}")

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
                    problems.append(f"suspicious private/credential indicator: {rel}:{lineno}")
                    break
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths-only", action="store_true",
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

    print("publication-safety: no high-signal tracked research-data/privacy violations found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
