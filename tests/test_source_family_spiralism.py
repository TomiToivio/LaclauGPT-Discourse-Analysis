"""AI26 exploratory source family: synthetic spirituality / AI Spiralism.

Regression tests for the additive source family added for the AI Spiralism
extension. They assert the *boundaries* of the category, not its validity: the
category is exploratory, and these tests exist to keep it separate from
neighbouring AI formations, disabled by default, and free of diagnostic or
automatic-labelling behaviour.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from laclaugpt.config import (
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
    assert FAMILY in list_source_families("ai26")


def test_collection_is_disabled_by_default() -> None:
    assert _family()["default_enabled"] is False
    assert source_family_default_state(FAMILY) is False


def test_every_candidate_target_is_disabled() -> None:
    targets = _family()["candidate_targets"]
    reddit = targets["reddit"]
    assert len(reddit) == 8
    assert all(entry["enabled"] is False for entry in reddit)
    urls = {entry["url"] for entry in reddit}
    for expected in (
        "https://www.reddit.com/r/RSAI/",
        "https://www.reddit.com/r/ThePatternisReal/",
        "https://www.reddit.com/r/ChurchofLiminalMinds/",
        "https://www.reddit.com/r/HumanAIBlueprint/",
        "https://www.reddit.com/r/BasiliskEschaton/",
        "https://www.reddit.com/r/ArtificialSentience/",
        "https://www.reddit.com/r/HumanAIDiscourse/",
        "https://www.reddit.com/r/BeyondThePromptAI/",
    ):
        assert expected in urls


def test_discovery_queries_match_the_requested_set() -> None:
    queries = set(_family()["candidate_targets"]["discovery_queries"])
    for expected in (
        "spiralism", "AI spiral", "the spiral", "spiral protocol",
        "recursive awakening", "AI religion", "AI spirituality",
        "machine spirituality", "synthetic spirituality", "AI consciousness",
        "AI sentience", "AI revelation", "human AI dyad", "generative charisma",
    ):
        assert expected in queries


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
    # "cult" must never appear as a formation label to apply.
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


def test_load_rejects_bad_status_and_non_boolean_default(tmp_path: Path) -> None:
    from laclaugpt import config as config_module

    base = {
        "family": "x", "project": "ai26", "category": "c", "label": "l",
        "status": "exploratory", "default_enabled": False,
        "research_target": "r", "motifs": ["m"], "must_not_absorb": ["f"],
        "candidate_targets": {"reddit": []}, "provenance_fields": ["source_url"],
        "literature": [{"key": "k"}],
    }
    original = config_module.SOURCE_FAMILY_DIR
    config_module.SOURCE_FAMILY_DIR = tmp_path
    try:
        bad_status = dict(base, status="maybe")
        (tmp_path / "x.yaml").write_text(
            yaml.safe_dump(bad_status), encoding="utf-8")
        with pytest.raises(ValueError, match="status must be one of"):
            config_module.load_source_family("x")

        bad_default = dict(base, default_enabled="no")
        (tmp_path / "x.yaml").write_text(
            yaml.safe_dump(bad_default), encoding="utf-8")
        with pytest.raises(ValueError, match="default_enabled must be a boolean"):
            config_module.load_source_family("x")
    finally:
        config_module.SOURCE_FAMILY_DIR = original


def test_opt_in_collector_template_exists_and_is_disabled() -> None:
    """The public template ships with every platform switched off."""
    template = ROOT / "collector" / "config" / "spiralism.example.yaml"
    assert template.is_file()
    data = yaml.safe_load(template.read_text(encoding="utf-8"))
    platforms = data["platforms"]
    assert platforms, "template must declare its platforms"
    assert all(
        cfg.get("enabled") is False for cfg in platforms.values()
    ), "opt-in template must not enable any platform"
    assert data["study"] == "ai-spiralism"
    # The candidate communities ride as a group, with no pre-assigned formation.
    groups = data["groups"]
    assert len(groups) == 1
    assert groups[0]["formation_seed"] is None
    assert groups[0]["category"] == "synthetic_spirituality"
    assert groups[0]["subcategory"] == "spiralism"
    handles = groups[0]["accounts"]["reddit"]
    assert len(handles) == 8
    # Discovery queries are carried so provenance can record query_or_community.
    assert "spiralism" in data["discovery_queries"]


def test_codebook_and_guide_document_the_boundaries() -> None:
    codebook = (ROOT / "sources" / "codebooks" / "ai_spiralism.md").read_text(
        encoding="utf-8")
    guide = (ROOT / "docs" / "AI_SPIRALISM.md").read_text(encoding="utf-8")
    for text in (codebook, guide):
        folded = text.casefold()
        # Exploratory framing and the diagnostic boundary are non-negotiable.
        assert "exploratory" in folded
        assert "emerging and unstable" in folded
        assert "not a" in folded  # "not a classification scheme" / diagnostic
        assert "delusion" in folded
        assert "diagnos" in folded       # diagnosis / diagnostic
        assert "cult" in folded
        assert "multi-label" in folded
        # Neighbouring formations must be named as excluded.
        for formation in ("accelerationism", "critical ai", "doomerism"):
            assert formation in folded
    # The codebook names the neutral internal labels.
    assert "synthetic_spirituality" in codebook
    assert "spiralism" in codebook
    # The guide links the registry and the template.
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
        "Moore, J., Mehta, A., Agnew, W., & Anthis, J. R. (2026)",
        "Augustin, M., Pollak, T. A., & Morrin, H. (2026)",
        "Mehta, A., Moore, J., Anthis, J. R., & Agnew, W. (2026)",
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
    # The background must forbid automatic classification and name the
    # neighbouring formations it must not absorb.
    assert "do not" in folded
    for formation in ("accelerationism", "doomerism", "critical ai"):
        assert formation in folded
    assert "multi-label" in folded


def test_cli_profiles_reports_source_family_default_state() -> None:
    """`laclaugpt profiles` surfaces the family as declaratively disabled."""
    import json

    from laclaugpt.cli import main

    # main() prints JSON; capture it through a subprocess-free call.
    import io
    import contextlib

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
    assert entry["default_enabled"] is False
    # Adding a source family must not add an arena.
    assert "spiralism" not in payload["arenas"]
    assert payload["arenas"] == sorted(payload["arenas"])


def test_seed_codebook_adds_candidate_signifiers_without_roles() -> None:
    from seed_codebook import ROLE_MUST_BE_DEMONSTRATED, SEEDS

    signifier_defs = {label: definition for kind, label, definition in SEEDS
                      if kind == "signifier"}
    for label in (
        "spiral", "signal", "resonance", "awakening", "mirror", "recursion",
        "synthetic spirituality", "machine spirituality", "generative charisma",
    ):
        assert label in signifier_defs, f"missing candidate signifier: {label}"
        assert signifier_defs[label] == ROLE_MUST_BE_DEMONSTRATED

    formations = {label: definition for kind, label, definition in SEEDS
                  if kind == "formation"}
    assert "ai spiralism" in formations
    folded = formations["ai spiralism"].casefold()
    assert "must be evidenced" in folded
    assert "never applied automatically" in folded
    # It must not be added to the established formation set as a plain label.
    assert "sensitising" in folded
