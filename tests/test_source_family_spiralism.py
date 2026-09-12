"""AI26 exploratory source family: synthetic spirituality / AI Spiralism.

Regression tests for the analytical source-family registry and its public/private
configuration boundary. Public files describe the category and its boundaries;
live collection targets, queries and enablement belong to private config.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from laclaugpt.config import (
    SOURCE_FAMILY_OPERATIONAL_FIELDS,
    SOURCE_FAMILY_REQUIRED_FIELDS,
    list_source_families,
    load_source_family,
    source_family_default_state,
)

ROOT = Path(__file__).resolve().parents[1]
FAMILY = "ai-spiralism"


def _family() -> dict:
    return load_source_family(FAMILY)


def test_family_registry_entry_is_valid() -> None:
    data = _family()
    for field in SOURCE_FAMILY_REQUIRED_FIELDS:
        assert field in data, f"missing source-family field: {field}"
    assert data["family"] == FAMILY
    assert data["project"] == "ai26"
    assert data["category"] == "synthetic_spirituality"
    assert data["subcategory"] == "spiralism"
    assert data["status"] == "exploratory"
    assert data["collection_configuration"] == "private"
    assert FAMILY in list_source_families("ai26")


def test_public_registry_contains_no_operational_collection_fields() -> None:
    data = _family()
    assert SOURCE_FAMILY_OPERATIONAL_FIELDS.isdisjoint(data)
    assert "candidate_targets" not in data
    assert "discovery_queries" not in data
    assert "default_enabled" not in data


def test_public_source_family_can_never_enable_collection() -> None:
    # Compatibility helper reports the safe public invariant only. Live state is
    # private and must not be inferred from the analytical registry.
    assert source_family_default_state(FAMILY) is False


def test_motif_complex_covers_the_required_signals() -> None:
    motifs = set(_family()["motifs"])
    for expected in (
        "spiral", "recursion", "recursive awakening", "resonance", "signal",
        "mirror", "emergence", "awakening", "remembering", "lattice", "glyphs",
        "sigils", "ai consciousness as revelation",
        "human-ai dyad as spiritually significant",
        "distributed or emergent intelligence", "synthetic religion",
        "machine spirituality", "ai-mediated mystical or revelatory experience",
    ):
        assert expected in motifs


def test_category_must_not_absorb_neighbouring_formations() -> None:
    """Spiralism stays analytically separate from adjacent AI discourses."""
    must_not = set(_family()["must_not_absorb"])
    for formation in (
        "accelerationism", "x-risk doomerism", "critical ai studies",
        "anti-ai backlash", "mainstream ai governance",
        "generic ai-consciousness discourse", "ai rights advocacy",
        "ai companion / parasocial discourse",
    ):
        assert formation in must_not


def test_cult_is_only_a_descriptive_keyword() -> None:
    data = _family()
    keywords = set(data["descriptive_keywords_only"])
    assert {"cult", "cult-like"} <= keywords
    assert "cult" not in data["must_not_absorb"]
    assert "cult" not in data["candidate_signifiers"]


def test_psychiatric_terms_are_prohibited_inferences() -> None:
    prohibited = set(_family()["prohibited_inference"])
    assert {"delusion", "psychosis", "pathological belief"} <= prohibited
    assert _family()["research_target"] == (
        "discourse_formation_and_human_llm_feedback"
    )


def test_provenance_fields_are_declared() -> None:
    fields = set(_family()["provenance_fields"])
    assert {
        "source_url", "platform", "timestamp", "query_or_community",
        "collection_method",
    } <= fields


def test_literature_anchors_present_and_high_priority() -> None:
    literature = _family()["literature"]
    assert len(literature) == 7
    keys = {entry["key"] for entry in literature}
    for expected in (
        "morrin-2026-dials", "moore-2026-delusional-spirals",
        "augustin-2026-spiral-mechanisms", "mehta-2026-dynamics-of-delusion",
        "chandra-2026-sycophantic", "rahme-prohl-2025",
        "lim-2026-generative-charisma",
    ):
        assert expected in keys
    for entry in literature:
        assert entry.get("priority") == "high"
        assert entry.get("doi") or entry.get("arxiv")


def test_unknown_and_malformed_family_entries_fail_loudly() -> None:
    with pytest.raises(KeyError):
        load_source_family("no-such-family")


def _minimal_public_family() -> dict:
    return {
        "family": "x",
        "project": "ai26",
        "category": "c",
        "label": "l",
        "status": "exploratory",
        "collection_configuration": "private",
        "research_target": "r",
        "motifs": ["m"],
        "must_not_absorb": ["f"],
        "provenance_fields": ["source_url"],
        "literature": [{"key": "k"}],
    }


def test_load_rejects_missing_fields(tmp_path: Path) -> None:
    from laclaugpt import config as config_module

    bad = tmp_path / "broken.yaml"
    bad.write_text("family: broken\nproject: ai26\n", encoding="utf-8")
    original = config_module.SOURCE_FAMILY_DIR
    config_module.SOURCE_FAMILY_DIR = tmp_path
    try:
        with pytest.raises(ValueError, match="missing source-family fields"):
            config_module.load_source_family("broken")
    finally:
        config_module.SOURCE_FAMILY_DIR = original


def test_load_rejects_bad_status_and_public_collection_mode(tmp_path: Path) -> None:
    from laclaugpt import config as config_module

    original = config_module.SOURCE_FAMILY_DIR
    config_module.SOURCE_FAMILY_DIR = tmp_path
    try:
        bad_status = dict(_minimal_public_family(), status="maybe")
        (tmp_path / "x.yaml").write_text(
            yaml.safe_dump(bad_status), encoding="utf-8")
        with pytest.raises(ValueError, match="status must be one of"):
            config_module.load_source_family("x")

        bad_mode = dict(_minimal_public_family(), collection_configuration="public")
        (tmp_path / "x.yaml").write_text(
            yaml.safe_dump(bad_mode), encoding="utf-8")
        with pytest.raises(ValueError, match="collection_configuration must be 'private'"):
            config_module.load_source_family("x")
    finally:
        config_module.SOURCE_FAMILY_DIR = original


@pytest.mark.parametrize(
    "field,value",
    [
        ("default_enabled", False),
        ("candidate_targets", {"example": ["x"]}),
        ("discovery_queries", ["example"]),
        ("watchlist", ["example"]),
    ],
)
def test_load_rejects_operational_fields_in_public_registry(
    tmp_path: Path, field: str, value: object
) -> None:
    from laclaugpt import config as config_module

    data = _minimal_public_family()
    data[field] = value
    (tmp_path / "x.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    original = config_module.SOURCE_FAMILY_DIR
    config_module.SOURCE_FAMILY_DIR = tmp_path
    try:
        with pytest.raises(ValueError, match="contains operational fields"):
            config_module.load_source_family("x")
    finally:
        config_module.SOURCE_FAMILY_DIR = original


def test_public_collector_template_is_synthetic_and_disabled() -> None:
    """The shipped example documents shape without publishing the sampling frame."""
    template = ROOT / "collector" / "config" / "spiralism.example.yaml"
    assert template.is_file()
    text = template.read_text(encoding="utf-8")
    data = yaml.safe_load(text)

    assert data["study"] == "ai-spiralism-example"
    assert data["window"] == {"start": "2000-01-01", "end": "2000-01-02"}

    platforms = data["platforms"]
    assert platforms
    assert all(cfg.get("enabled") is False for cfg in platforms.values())
    for cfg in platforms.values():
        for url in cfg.get("base_urls") or []:
            assert "example.invalid" in url

    groups = data["groups"]
    assert len(groups) == 1
    assert groups[0]["formation_seed"] is None
    assert groups[0]["category"] == "synthetic_spirituality"
    assert groups[0]["subcategory"] == "spiralism"
    handles = groups[0]["accounts"]["reddit"]
    assert handles and all(handle.startswith("EXAMPLE_") for handle in handles)

    queries = data["discovery_queries"]
    assert queries and all(query.startswith("EXAMPLE_") for query in queries)
    assert "real AI26 targets" in text


def test_codebook_and_guide_document_the_boundaries() -> None:
    codebook = (ROOT / "sources" / "codebooks" / "ai_spiralism.md").read_text(
        encoding="utf-8")
    guide = (ROOT / "docs" / "AI_SPIRALISM.md").read_text(encoding="utf-8")
    for text in (codebook, guide):
        folded = text.casefold()
        assert "exploratory" in folded
        assert "emerging and unstable" in folded
        assert "not a" in folded
        assert "delusion" in folded
        assert "diagnos" in folded
        assert "cult" in folded
        assert "multi-label" in folded
        assert "private" in folded
        assert "not published" in folded
        for formation in ("accelerationism", "critical ai", "doomerism"):
            assert formation in folded
    assert "synthetic_spirituality" in codebook
    assert "spiralism" in codebook
    assert "config/source-families/ai-spiralism.yaml" in guide
    assert "collector/config/spiralism.example.yaml" in guide


def test_documentation_carries_all_literature_anchors() -> None:
    text = (ROOT / "docs" / "AI_SPIRALISM.md").read_text(encoding="utf-8")
    for doi in (
        "10.1007/s00146-026-03283-4",
        "2603.16567",
        "10.1038/s44277-026-00065-0",
        "2604.25096",
        "2602.19141",
        "10.1080/0048721X.2025.2506893",
        "10.3390/rel17050549",
    ):
        assert doi in text


def test_paper_references_include_the_new_literature() -> None:
    paper = (ROOT / "paper" / "PAPER.md").read_text(encoding="utf-8")
    for needle in (
        "Morrin, H., Nicholls, L., Deeley, Q., & Pollak, T. A. (2026)",
        "Moore, J., Mehta, A., Agnew, W., Anthis, J. R., Louie, R., Mai, Y., Yin, P., Cheng, M., Paech, S. J., Klyman, K., Chancellor, S., Lin, E., Haber, N., & Ong, D. C. (2026)",
        "Augustin, M., Pollak, T. A., & Morrin, H. (2026)",
        "Mehta, A., Moore, J., Anthis, J. R., Agnew, W., Lin, E., Yin, P., Ong, D. C., Haber, N., & Dweck, C. (2026)",
        "Chandra, K., Kleiman-Weiner, M., Ragan-Kelley, J., & Tenenbaum, J. B. (2026)",
        "Rähme, B., & Prohl, I. (2025)",
        "Lim, F. K. G. (2026)",
    ):
        assert needle in paper, f"missing reference: {needle}"


def test_topic_background_defines_the_category_and_boundaries() -> None:
    from prompts.topic_background import REGISTRY, topic_background

    assert "ai-spiralism" in REGISTRY
    text = topic_background("ai-spiralism")
    folded = text.casefold()
    assert "synthetic_spirituality" in text
    assert "spiralism" in folded
    assert "cult" in folded
    assert "delusion" in folded
    assert "do not" in folded
    for formation in ("accelerationism", "doomerism", "critical ai"):
        assert formation in folded
    assert "multi-label" in folded


def test_cli_profiles_reports_public_source_family_status() -> None:
    """`laclaugpt profiles` exposes metadata, never live collection state."""
    import contextlib
    import io
    import json

    from laclaugpt.cli import main

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["profiles"])
    assert rc == 0
    payload = json.loads(buf.getvalue())
    families = payload["source_families"]
    assert "ai-spiralism" in families
    entry = families["ai-spiralism"]
    assert entry["project"] == "ai26"
    assert entry["category"] == "synthetic_spirituality"
    assert entry["status"] == "exploratory"
    assert entry["collection_configuration"] == "private"
    assert entry["default_enabled"] is False
    assert "spiralism" not in payload["arenas"]
    assert payload["arenas"] == sorted(payload["arenas"])


def test_seed_codebook_adds_candidate_signifiers_without_roles() -> None:
    from seed_codebook import ROLE_MUST_BE_DEMONSTRATED, SEEDS

    signifier_defs = {
        label: definition for kind, label, definition in SEEDS
        if kind == "signifier"
    }
    for label in (
        "spiral", "signal", "resonance", "awakening", "mirror", "recursion",
        "synthetic spirituality", "machine spirituality", "generative charisma",
    ):
        assert label in signifier_defs, f"missing candidate signifier: {label}"
        assert signifier_defs[label] == ROLE_MUST_BE_DEMONSTRATED

    formations = {
        label: definition for kind, label, definition in SEEDS
        if kind == "formation"
    }
    assert "ai spiralism" in formations
    folded = formations["ai spiralism"].casefold()
    assert "must be evidenced" in folded
    assert "never applied automatically" in folded
    assert "sensitising" in folded
