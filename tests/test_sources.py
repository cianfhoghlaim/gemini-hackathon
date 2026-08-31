"""Tests for the gemini_hackathon.sources jurisdiction/board axis split.

8 jurisdictions (5 active + 3 future-expansion-pack) × 10 awarding
bodies, with 31 subjects spread across the canonical British Isles
matriculation landscape.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Jurisdiction count + invariants
# ---------------------------------------------------------------------------


def test_eight_jurisdictions():
    from gemini_hackathon.sources import JURISDICTIONS

    assert len(JURISDICTIONS) == 8


def test_jurisdiction_codes_are_unique():
    from gemini_hackathon.sources import JURISDICTIONS

    codes = [j.code for j in JURISDICTIONS]
    assert len(set(codes)) == 8
    # Spot-check the canonical 8 are present.
    for required in (
        "ireland",
        "england",
        "scotland",
        "wales",
        "northern_ireland",
        "jersey",
        "guernsey",
        "isle_of_man",
    ):
        assert required in codes


def test_jurisdiction_axes_consistent():
    """Every jurisdiction's awarding_bodies resolve in BOARDS_BY_CODE."""
    from gemini_hackathon.sources import BOARDS_BY_CODE, JURISDICTIONS

    for j in JURISDICTIONS:
        for b in j.awarding_bodies:
            assert b in BOARDS_BY_CODE, f"{j.code} references unknown board {b!r}"


# ---------------------------------------------------------------------------
# Board count + invariants
# ---------------------------------------------------------------------------


def test_ten_boards_three_for_england():
    from gemini_hackathon.sources import BOARDS

    assert len(BOARDS) == 10
    england_boards = [b for b in BOARDS if b.jurisdiction == "england"]
    assert {b.code for b in england_boards} == {"aqa", "ocr", "pearson"}


def test_one_board_per_non_england_jurisdiction():
    from gemini_hackathon.sources import BOARDS

    by_j = {}
    for b in BOARDS:
        by_j.setdefault(b.jurisdiction, []).append(b)
    for j, bs in by_j.items():
        if j != "england":
            assert len(bs) == 1, f"{j} has {len(bs)} boards, expected 1"


# ---------------------------------------------------------------------------
# Subjects per (jurisdiction, board)
# ---------------------------------------------------------------------------


def test_subjects_have_at_least_one_per_active_jurisdiction():
    from gemini_hackathon.sources import SUBJECTS

    by_j = {s.jurisdiction for s in SUBJECTS}
    assert by_j >= {
        "ireland",
        "england",
        "scotland",
        "northern_ireland",
        "wales",
        "jersey",
        "guernsey",
    }


def test_subjects_for_filters_by_jurisdiction():
    from gemini_hackathon.sources import subjects_for

    ie = subjects_for("ireland")
    assert all(s.jurisdiction == "ireland" for s in ie)
    assert len(ie) >= 3


def test_subjects_for_filters_by_jurisdiction_and_board():
    from gemini_hackathon.sources import subjects_for

    aqa = subjects_for("england", "aqa")
    assert all(s.jurisdiction == "england" and s.board == "aqa" for s in aqa)


def test_subjects_jersey_cycle_is_gcse():
    from gemini_hackathon.sources import subjects_for

    je = subjects_for("jersey")
    assert len(je) >= 1
    assert all(s.cycle == "gcse" for s in je)


def test_wales_welsh_medium_subject_marked():
    from gemini_hackathon.sources import subjects_for

    cymraeg = [s for s in subjects_for("wales") if "cymraeg" in s.slug.lower()]
    assert cymraeg
    assert cymraeg[0].is_welsh_medium is True


# ---------------------------------------------------------------------------
# Public roster (excludes future expansion pack)
# ---------------------------------------------------------------------------


def test_public_roster_excludes_future_expansion_pack():
    from gemini_hackathon.sources import public_roster

    js = [r for r in public_roster() if r["jurisdiction_code"] == "jersey"]
    gs = [r for r in public_roster() if r["jurisdiction_code"] == "guernsey"]
    im = [r for r in public_roster() if r["jurisdiction_code"] == "isle_of_man"]
    assert not js, "Jersey should be hidden from the public roster"
    assert not gs, "Guernsey should be hidden from the public roster"
    assert not im, "Isle of Man should be hidden from the public roster"


def test_public_roster_includes_5_active_jurisdictions():
    from gemini_hackathon.sources import public_roster

    js = {r["jurisdiction_code"] for r in public_roster()}
    assert "ireland" in js
    assert "england" in js
    assert "scotland" in js
    assert "wales" in js
    assert "northern_ireland" in js


def test_public_roster_is_deterministic():
    from gemini_hackathon.sources import public_roster

    a = public_roster()
    b = public_roster()
    assert a == b


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def test_get_jurisdiction_meta_known():
    from gemini_hackathon.sources import get_jurisdiction_meta

    j = get_jurisdiction_meta("ireland")
    assert j.name == "Ireland"
    assert j.default_cycle == "leaving_cycle"


def test_get_jurisdiction_meta_unknown_raises():
    from gemini_hackathon.sources import get_jurisdiction_meta

    with pytest.raises(KeyError):
        get_jurisdiction_meta("atlantis")


def test_get_board_meta_known():
    from gemini_hackathon.sources import get_board_meta

    b = get_board_meta("aqa")
    assert b.jurisdiction == "england"
    assert "aqa.org.uk" in b.official_url
