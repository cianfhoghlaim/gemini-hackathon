"""Tests for the NCCA progression ledger + unofficial certificates."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


# ---------------------------------------------------------------------------
# Phase 11 — progression
# ---------------------------------------------------------------------------


def test_score_to_descriptor_thresholds():
    from gemini_hackathon.progression.progression import _score_to_descriptor
    assert _score_to_descriptor(0.95) == "Exceptional"
    assert _score_to_descriptor(0.85) == "Exceptional"
    assert _score_to_descriptor(0.75) == "Above expectations"
    assert _score_to_descriptor(0.65) == "Above expectations"
    assert _score_to_descriptor(0.50) == "In line with expectations"
    assert _score_to_descriptor(0.40) == "In line with expectations"
    assert _score_to_descriptor(0.20) == "Yet to meet expectations"
    assert _score_to_descriptor(0.00) == "Yet to meet expectations"


def _event(score=0.8, descriptor="Above expectations", subject="ncca_maths_lc"):
    from gemini_hackathon.progression import AssessmentEvent, AssessmentType
    return AssessmentEvent(
        learner_id="alice", outcome_id="outcome-1",
        subject_slug=subject, score=score, descriptor=descriptor,
        assessment_type=AssessmentType.FORMATIVE,
        captured_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def test_apply_event_creates_initial_mastery():
    from gemini_hackathon.progression import apply_event
    new, ev = apply_event(None, _event(score=0.9, descriptor="Exceptional"))
    assert new.event_count == 1
    assert new.mastery_level == 0.9
    # For the first event, the descriptor is taken from the event itself (no
    # synthetic derivation from a single-sample mean).
    assert new.descriptor == "Exceptional"


def test_apply_event_increments_event_count():
    from gemini_hackathon.progression import apply_event
    current, _ = apply_event(None, _event(score=0.9))
    new, _ = apply_event(current, _event(score=0.7))
    assert new.event_count == 2


def test_progress_summary_counts_per_descriptor():
    from gemini_hackathon.progression import (
        AssessmentEvent, AssessmentType, progress_summary,
    )
    events = [
        AssessmentEvent(
            learner_id="a", outcome_id="o", subject_slug="s",
            score=0.9, descriptor="Exceptional",
            assessment_type=AssessmentType.FORMATIVE,
        ),
        AssessmentEvent(
            learner_id="a", outcome_id="o", subject_slug="s",
            score=0.7, descriptor="Above expectations",
            assessment_type=AssessmentType.FORMATIVE,
        ),
        AssessmentEvent(
            learner_id="a", outcome_id="o", subject_slug="s",
            score=0.5, descriptor="In line with expectations",
            assessment_type=AssessmentType.FORMATIVE,
        ),
    ]
    counts = progress_summary(events)
    assert counts["Exceptional"] == 1
    assert counts["Above expectations"] == 1
    assert counts["In line with expectations"] == 1
    assert counts["Yet to meet expectations"] == 0


# ---------------------------------------------------------------------------
# Phase 11 — certificates (always unofficial)
# ---------------------------------------------------------------------------


def test_certificate_renders_unoffical_banner():
    from gemini_hackathon.progression import CertificateRecord, render_certificate_markdown
    cert = CertificateRecord(
        learner_id="alice",
        learner_name="Alice Example",
        award_type="leaving_cycle",
        award_title="Leaving Certificate — Maths",
        jurisdiction="Ireland",
        subject_slug="lc_maths",
        outcomes_covered=("outcome-1", "outcome-2"),
        descriptor="Exceptional",
    )
    md, meta = render_certificate_markdown(cert)
    assert "UNOFFICIAL" in md
    assert "Alice Example" in md
    assert "Exceptional" in md
    assert "outcome-1" in md
    assert meta["award_type"] == "leaving_cycle"
    assert meta["learner_name"] == "Alice Example"


def test_certificate_metadata_keys_match_award_types():
    """The metadata dict keys line up with the AwardType enum + extras."""
    from gemini_hackathon.progression import CertificateRecord, render_certificate_markdown
    cert = CertificateRecord(
        learner_id="b", learner_name="Bob", award_type="gcse",
        award_title="GCSE Mathematics", jurisdiction="England",
    )
    _, meta = render_certificate_markdown(cert)
    for key in (
        "learner_id", "learner_name", "award_type", "award_title",
        "jurisdiction", "subject_slug", "descriptor", "issued_at",
        "outcomes_covered",
    ):
        assert key in meta, f"missing metadata key {key!r}"


def test_certificate_award_types_match_phase_3_registry():
    """The AwardType literal aligns with the Phase-3 per-subnation-user-context
    schema — no drift."""
    from gemini_hackathon.progression import AwardType
    # All 12 surface values from Phase 3.
    expected = {
        "junior_cycle", "leaving_cycle", "cba", "short_course",
        "gcse", "a_level", "national_5", "higher",
        "advanced_higher", "l1lp", "l2lp", "special_education",
    }
    # AwardType is a Literal[str, ...] — we can introspect via __args__.
    assert set(AwardType.__args__) == expected
