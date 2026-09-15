# -*- coding: utf-8 -*-
"""Context-profile contract (issue #140).

Profiles are pure configuration: they must never change models/stages/gates,
must be deterministic, and must fail loudly on unknown names.
"""
from __future__ import annotations


def test_bundled_profiles_resolve():
    from laclaugpt.context_profiles import load_profile, PROFILE_NAMES
    for name in PROFILE_NAMES:
        profile = load_profile(name)
        assert profile.name == name
        assert profile.max_context_chars >= 200
        assert profile.max_transcript_chars >= 500


def test_unknown_profile_fails_loudly():
    import pytest
    from laclaugpt.context_profiles import load_profile
    with pytest.raises(KeyError):
        load_profile("does_not_exist")


def test_profiles_only_touch_context_knobs():
    """balanced vs high_accuracy must not differ on models/stages/gates —
    those are the run YAML's authority."""
    from laclaugpt.context_profiles import load_profile
    balanced = load_profile("balanced").to_dict()
    high = load_profile("high_accuracy").to_dict()
    context_keys = {"name", "description", "glossary_top_k", "max_context_chars",
                    "max_transcript_chars", "inject_previous_batch_summary",
                    "inject_corpus_stats", "vector_rag"}
    differing = {k for k in balanced if balanced[k] != high[k]}
    assert differing <= context_keys


def test_codebook_required_stages_present_in_all_profiles():
    from laclaugpt.context_profiles import load_profile, PROFILE_NAMES
    for name in PROFILE_NAMES:
        profile = load_profile(name)
        assert profile.inject_codebook is True
        assert set(profile.codebook_required_stages) == {
            "summary", "discourse", "populism"}


def test_validation_profile_records_provenance():
    from laclaugpt.context_profiles import load_profile
    assert load_profile("validation").context_provenance is True
    assert load_profile("fast_local").context_provenance is False
