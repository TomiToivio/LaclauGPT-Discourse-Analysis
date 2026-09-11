from scripts import check_publication_safety as safety


def _suspicious(line: str) -> bool:
    return any(pattern.search(line) for pattern in safety.SUSPICIOUS_CONTENT)


def test_path_guard_blocks_common_private_artifacts() -> None:
    problems = safety.path_violations([
        "credentials.json",
        "cookies.sqlite-wal",
        "exports/ai26.jsonl",
        "config/sources/live-watchlist.yaml",
        "deploy/systemd/ai26/live.service",
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
    assert "config/sources/live-watchlist.yaml" in rendered
    assert "deploy/systemd/ai26/live.service" in rendered
    assert "ai26_runtime/local-export.jsonl" in rendered
    assert "capture.session" in rendered
    assert "private-key.pem" in rendered
    assert "database.dump" in rendered
    assert "bundle.tar.gz" in rendered
    assert "tests/fixtures/synthetic_ai.csv" not in rendered


def test_content_guard_catches_high_signal_secrets_and_private_infra() -> None:
    assert _suspicious('password: "correct-horse-battery-staple"')  # PUBLICATION-SAFETY: allow
    assert _suspicious("api_key: abcdefghijklmnopqrstuvwxyz")  # PUBLICATION-SAFETY: allow
    assert _suspicious("mongodb://researcher:supersecret@db.example:27017/laclaugpt")  # PUBLICATION-SAFETY: allow
    assert _suspicious("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456")  # PUBLICATION-SAFETY: allow
    assert _suspicious("/home/researcher/private/ai26.yaml")  # PUBLICATION-SAFETY: allow
    assert _suspicious("/users/researcher/private/ai26.yaml")  # PUBLICATION-SAFETY: allow
    assert _suspicious("/scratch/project_1234567/private/ai26")  # PUBLICATION-SAFETY: allow
    assert _suspicious("/projappl/project_1234567/private/ai26")  # PUBLICATION-SAFETY: allow
    assert _suspicious(r"C:\Users\researcher\private\ai26.yaml")  # PUBLICATION-SAFETY: allow
    assert _suspicious("host: 192.168.10.42")  # PUBLICATION-SAFETY: allow
    assert _suspicious("host: 100.115.95.109")  # PUBLICATION-SAFETY: allow


def test_content_guard_allows_explicit_placeholders_and_loopback() -> None:
    assert not _suspicious('password: "${LACLAUGPT_ARANGODB_PASSWORD}"')
    assert not _suspicious("api_key: placeholder")
    assert not _suspicious("base_url: http://127.0.0.1:11434")
    assert not _suspicious("path: /home/user/project")
    assert not _suspicious("path: /users/user/project")
    assert not _suspicious(r"path: C:\Users\user\project")
    assert not _suspicious("path: ${LACLAUGPT_DATA_DIR}/ai26")


def test_content_guard_does_not_treat_code_expressions_as_literal_secrets() -> None:
    assert not _suspicious('api_key = os.environ.get("OLLAMA_API_KEY", "").strip()')
    assert not _suspicious(
        'password=_setting(config, "arangodb_password", "LACLAUGPT_ARANGODB_PASSWORD")'
    )
