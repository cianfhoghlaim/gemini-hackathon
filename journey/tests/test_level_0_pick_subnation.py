"""test_level_0_pick_subnation.py — Level 0 tests."""

from __future__ import annotations


def test_subnation_table_has_eight_jurisdictions():
    from gemini_hackathon.journey.level_0_pick_subnation.app import SUBNATIONS

    assert len(SUBNATIONS) == 8
    slugs = {s[0] for s in SUBNATIONS}
    assert slugs == {
        "ireland",
        "england",
        "northern_ireland",
        "scotland",
        "wales",
        "jersey",
        "guernsey",
        "isle_of_man",
    }


def test_build_learner_doc_shape():
    from gemini_hackathon.journey.level_0_pick_subnation.app import _build_learner_doc

    doc = _build_learner_doc(
        learner_id="alice@school.ie",
        display_name="Alice",
        subnation="ireland",
        palette_file="ncca_palette.json",
    )
    # Must contain every key the journey's progress dashboard reads back.
    for required in (
        "learner_id",
        "subnation",
        "active_subject",
        "current_level",
        "progress",
        "created_at",
        "journey_event_code",
    ):
        assert required in doc, f"missing key {required!r} from learner doc"


def test_apply_palette_stub_returns_expected_shape():
    from gemini_hackathon.journey.level_0_pick_subnation.app import _apply_palette

    out = _apply_palette("ireland")
    assert out.get("applied") is True
    assert out.get("subnation") == "ireland"
    # The stub surfaces a hint to the codelab participant about the real
    # call to swap in.
    assert "apply_palette_for_subnation" in out.get("_stub_note", "")


def test_write_learner_profile_offline_path():
    """The in-memory fallback path works (no Firestore needed)."""
    from gemini_hackathon.journey.level_0_pick_subnation.app import write_learner_profile

    out = write_learner_profile(
        learner_id="test@school.ie",
        display_name="Test",
        subnation="scotland",
    )
    assert out["learner_id"] == "test@school.ie"
    assert out["subnation"] == "scotland"
    assert out["palette_file"] == "scotland_palette.json"
    assert out["offline_stub"] is True


def test_write_learner_profile_jersey_uses_jersey_palette():
    from gemini_hackathon.journey.level_0_pick_subnation.app import write_learner_profile

    out = write_learner_profile(
        learner_id="bob@school.je",
        display_name="Bob",
        subnation="jersey",
    )
    assert out["palette_file"] == "jersey_palette.json"
