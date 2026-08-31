"""Tests for `gemini_hackathon.subnations` — the 6 active British Isles
subnations (Ireland, England, NI, Wales, Scotland, IoM) + the 2 deferred
expansion-pack subnations (Jersey, Guernsey).

Updated 2026-08-31 (Phase 6): exercises the public API + 2 lookup helpers
that are referenced from the ADK agent + BAML extracts + DLT pipelines.
"""

from __future__ import annotations

from gemini_hackathon.subnations import (
    DEFERRED_SUBNATIONS,
    SUBNATIONS,
    get_active_subnations,
    get_hackathon_subnations,
    get_phase_2_subnations,
    get_subnation_by_iso,
    get_subnation_by_name,
    get_subnation_theme_key,
)


def test_subnations_constant_has_six_active():
    """The canonical shipping set is 6 active subnations."""
    assert len(SUBNATIONS) == 6


def test_subnations_have_required_keys():
    """Every SUBNATIONS entry carries the canonical key set."""
    required = {"name", "iso_code", "awarding_bodies", "phase", "official_url",
                "uk_naric_recognised", "stage_default", "themes_key"}
    for s in SUBNATIONS:
        missing = required - set(s.keys())
        assert not missing, f"{s['name']!r} is missing keys: {missing}"


def test_subnation_awarding_bodies_is_tuple():
    """`awarding_bodies` is a tuple (not a list) so it is hashable / immutable."""
    for s in SUBNATIONS:
        assert isinstance(s["awarding_bodies"], tuple)


def test_subnations_iso_codes_are_unique():
    """Every SUBNATIONS entry has a unique ISO country code."""
    iso_codes = [s["iso_code"] for s in SUBNATIONS]
    assert len(iso_codes) == len(set(iso_codes))


def test_subnations_active_set_is_subset_of_total():
    """The 4 phase_2 entries live alongside the 2 active entries."""
    assert len(get_hackathon_subnations()) == 2
    assert len(get_phase_2_subnations()) == 4
    assert len(get_hackathon_subnations()) + len(get_phase_2_subnations()) == len(SUBNATIONS)


def test_hackathon_subset_is_ireland_plus_england():
    """The two shipping subnations are Ireland (IE) + England (GB-ENG)."""
    names = {s["name"] for s in get_hackathon_subnations()}
    assert names == {"Ireland", "England"}


def test_phase_2_set_is_ni_wales_scotland_iom():
    """The 4 Phase 2 subnations match the deferred list."""
    names = {s["name"] for s in get_phase_2_subnations()}
    assert names == {"Northern Ireland", "Wales", "Scotland", "Isle of Man"}


def test_get_active_subnations_returns_all_six():
    """`get_active_subnations()` returns the full SUBNATIONS tuple."""
    assert get_active_subnations() == SUBNATIONS


def test_get_subnation_by_name_exact_match():
    """The lookup uses case-insensitive matching by display name."""
    ireland = get_subnation_by_name("Ireland")
    assert ireland is not None
    assert ireland["iso_code"] == "IE"
    assert ireland["themes_key"] == "ncca"


def test_get_subnation_by_name_case_insensitive():
    """`get_subnation_by_name` is case- and whitespace-insensitive."""
    for s in SUBNATIONS:
        upper = get_subnation_by_name(s["name"].upper())
        assert upper is not None
        assert upper["iso_code"] == s["iso_code"]


def test_get_subnation_by_name_unknown_returns_none():
    """Unknown names return None (not a KeyError)."""
    assert get_subnation_by_name("Atlantis") is None
    assert get_subnation_by_name("") is None


def test_get_subnation_by_iso_exact_match():
    """The ISO lookup returns the same record as the name lookup."""
    ireland_via_iso = get_subnation_by_iso("IE")
    ireland_via_name = get_subnation_by_name("Ireland")
    assert ireland_via_iso == ireland_via_name


def test_get_subnation_by_iso_case_insensitive():
    """`get_subnation_by_iso` is case-insensitive."""
    upper = get_subnation_by_iso("ie")
    assert upper is not None
    assert upper["iso_code"] == "IE"


def test_subnation_theme_keys_use_awarding_body_names():
    """The `themes_key` field carries the canonical palette key per subnation."""
    expected = {
        "Ireland": "ncca",
        "England": "aqa",
        "Northern Ireland": "ccea",
        "Wales": "wjec",
        "Scotland": "sqa",
        "Isle of Man": "iom",
    }
    for s in SUBNATIONS:
        assert s["themes_key"] == expected[s["name"]], (
            f"{s['name']} themes_key={s['themes_key']!r}, expected {expected[s['name']]!r}"
        )


def test_get_subnation_theme_key_known_and_unknown():
    """`get_subnation_theme_key` delegates to `get_subnation_by_name`."""
    assert get_subnation_theme_key("Ireland") == "ncca"
    assert get_subnation_theme_key("Atlantis") is None


def test_deferred_subnations_have_two_entries():
    """The expansion-pack set has Jersey + Guernsey (per Phase 0 commit)."""
    assert len(DEFERRED_SUBNATIONS) == 2
    names = {s["name"] for s in DEFERRED_SUBNATIONS}
    assert names == {"Jersey", "Guernsey"}


def test_deferred_subnations_marked_phase_expansion_pack():
    """Deferred subnations carry `phase=expansion_pack` so callers can skip them."""
    for s in DEFERRED_SUBNATIONS:
        assert s["phase"] == "expansion_pack"


def test_deferred_subnations_not_in_active_set():
    """Deferred subnations are NOT returned by `get_active_subnations()`."""
    active_names = {s["name"] for s in get_active_subnations()}
    for s in DEFERRED_SUBNATIONS:
        assert s["name"] not in active_names


def test_uk_naric_recognised_is_true_for_all_active():
    """All 6 active subnations are UK NARIC-recognised (per the 2026-08-30
    British-Isles refocus)."""
    for s in SUBNATIONS:
        assert s["uk_naric_recognised"] is True
