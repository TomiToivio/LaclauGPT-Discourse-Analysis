from pathlib import Path

path = Path("tests/test_collect_dair.py")
text = path.read_text(encoding="utf-8")
start = text.index("def test_profile_switches_peer_tube_and_public_hygiene():")
end = text.index("\ndef test_empty_duplicate_or_malformed_source_lists", start)
replacement = '''def test_private_profile_switches_and_hygiene(tmp_path: Path):
    profile_path = tmp_path / "dair-private.yaml"
    synthetic = {
        **CFG,
        "sources": [
            {
                "key": "synthetic-enabled",
                "kind": "page",
                "enabled": True,
                "url": "https://example.org/enabled",
            },
            {
                "key": "synthetic-disabled",
                "kind": "page",
                "enabled": False,
                "url": "https://example.org/disabled",
            },
        ],
    }
    profile_path.write_text(yaml.safe_dump(synthetic), encoding="utf-8")
    profile = load_profile(profile_path)
    enabled = {source["key"] for source in profile["sources"] if source["enabled"]}
    assert enabled == {"synthetic-enabled"}
    assert not next(
        source for source in profile["sources"] if source["key"] == "synthetic-disabled"
    )["enabled"]
    serialized = yaml.safe_dump(profile).lower()
    assert "classification_state" not in serialized or "unjudged" in serialized
    assert not any(
        secret in serialized
        for secret in ("api_key", "password", "bearer ", "c:\\users", "/scratch/")
    )
'''
path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")
