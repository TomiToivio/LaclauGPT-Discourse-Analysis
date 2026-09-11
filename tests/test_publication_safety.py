from scripts import check_publication_safety as safety


def _suspicious(line: str) -> bool:
    return any(pattern.search(line) for pattern in safety.SUSPICIOUS_CONTENT)


def test_path_guard_blocks_common_private_artifacts() -> None:
    problems = safety.path_violations([
        "credentials.json",
        "cookies.sqlite-wal",
        "exports/ai26.jsonl",
        "ai26_runtime/local-export.jsonl",
        "capture.session",
        "private-key.pem",
        "database.dump",
        "bundle.tar.gz",
        "tests/fixtures/synthetic_ai.csv",
    ])
    rendered = "\n".join(problems)
    assert "credentials.json" in rendered
    assert "cookies.sqlite-wal" in rendered
    assert "exports/ai26.jsonl" in rendered
    assert "ai26_runtime/local-export.jsonl" in rendered
    assert "capture.session" in rendered
    assert "private-key.pem" in rendered
    assert "database.dump" in rendered
    assert "bundle.tar.gz" in rendered
    assert "tests/fixtures/synthetic_ai.csv" not in rendered


def test_content_guard_catches_high_signal_secrets_and_private_infra() -> None:
    assert _suspicious('password: "correct-horse-battery-staple"')
    assert _suspicious("api_key: abcdefghijklmnopqrstuvwxyz")
    assert _suspicious("mongodb://researcher:supersecret@db.example:27017/laclaugpt")
    assert _suspicious("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456")
    assert _suspicious("/home/researcher/private/ai26.yaml")
    assert _suspicious(r"C:\Users\researcher\private\ai26.yaml")
    assert _suspicious("host: 192.168.10.42")


def test_content_guard_allows_explicit_placeholders_and_loopback() -> None:
    assert not _suspicious('password: "${LACLAUGPT_ARANGODB_PASSWORD}"')
    assert not _suspicious("api_key: placeholder")
    assert not _suspicious("base_url: http://127.0.0.1:11434")
    assert not _suspicious("path: /home/user/project")
    assert not _suspicious(r"path: C:\Users\user\project")
