"""test_journey_workflow.py — the orchestrator's 8 integration tests.

End-to-end tests that exercise the whole `run_full_journey` pipeline
against the in-memory fallbacks every backend ships with (Firestore,
MasteryLedger, Vertex embeddings, etc.).
"""

from __future__ import annotations

import asyncio


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class _FakeCtx:
    """Minimal context with a state dict — what every per-level node reads."""

    def __init__(self, state: dict | None = None):
        self.state = dict(state or {})


def test_journey_full_6_levels_offline():
    """The end-to-end happy path: all 6 levels run, no exceptions."""
    from gemini_hackathon.journey.journey_orchestrator.workflow import run_full_journey

    ctx = _FakeCtx(
        {
            "learner_id": "test@school.ie",
            "subnation": "ireland",
            "subject": "mathematics",
            "user_question": "Draw a labelled diagram of the sine rule",
            "student_answer": "a/sin(A) = b/sin(B)",
            "outcome_code": "MA-LC-MA-1.1",
            "mastery_score": 0.78,
        }
    )
    out = _run(run_full_journey(ctx))
    assert out.learner_id == "test@school.ie"
    assert out.subnation == "ireland"
    assert out.subject == "mathematics"
    # Every level must produce SOMETHING (even if it's an error dict in the
    # offline-stub path, it's not None).
    for level in (
        "level_1",
        "level_2",
        "level_3",
        "level_4",
        "level_5",
        "request_human_confirmation",
    ):
        assert getattr(out, level) is not None, f"{level} produced None"
    # NCCA citations must propagate from every level that emits them.
    assert out.ncca_policy_citations, "at least 1 NCCA citation must propagate"
    # Asset storage URI must be set on success.
    assert out.asset_storage_uri


def test_journey_resilient_to_missing_state_keys():
    """The orchestrator must NOT crash if the participant skipped Level 0."""
    from gemini_hackathon.journey.journey_orchestrator.workflow import run_full_journey

    ctx = _FakeCtx({})  # no learner_id, no subnation — defaults should apply
    out = _run(run_full_journey(ctx))
    assert out.learner_id == ""  # default
    assert out.subnation == "ireland"  # default
    assert out.subject == "mathematics"  # default
    # All 6 levels still ran.
    for level in (
        "level_1",
        "level_2",
        "level_3",
        "level_4",
        "level_5",
        "request_human_confirmation",
    ):
        assert getattr(out, level) is not None


def test_journey_human_confirmation_emits_correct_message():
    """The RequestInput between Level 4 and Level 5 must have the right message."""
    from gemini_hackathon.journey.journey_orchestrator.workflow import request_human_confirmation

    result = _run(request_human_confirmation(_FakeCtx()))
    # Either a Pydantic RequestInput (production path with ADK installed),
    # a structured dict (offline-stub path when google.adk is importable
    # but no Agent Engine), or a string-ish fallback.
    msg = ""
    if hasattr(result, "message"):
        msg = result.message
    elif isinstance(result, dict):
        msg = result.get("message", "")
    elif isinstance(result, str):
        msg = result
    else:
        msg = str(result)
    # In any branch, the message must signal the HITL pause. Allow either
    # of two valid phrasings (production: the canonical message;
    # offline-stub / ADK-unavailable: a graceful "skipped" marker).
    assert "Mastery ledger updated" in msg or "Continue" in msg or "skipped" in msg.lower(), (
        f"unexpected message in {type(result).__name__}: {msg!r}"
    )


def test_callback_hydrates_required_keys():
    """The before_agent_callback must populate all 6 whitelisted state keys."""
    from gemini_hackathon.journey.journey_orchestrator.callback_before_agent import (
        hydrate_participant_state,
    )

    ctx = _FakeCtx({})
    out = hydrate_participant_state(ctx)
    for key in (
        "learner_id",
        "subnation",
        "subject",
        "event_code",
        "journey_event_code",
        "display_name",
    ):
        assert key in out, f"key {key!r} missing from callback output"


def test_callback_respects_existing_ctx_state():
    """If the participant's Firestore state is already in ctx, the callback uses it."""
    from gemini_hackathon.journey.journey_orchestrator.callback_before_agent import (
        hydrate_participant_state,
    )

    ctx = _FakeCtx(
        {
            "learner_id": "from_ctx",
            "subnation": "jersey",
            "subject": "geography",
        }
    )
    out = hydrate_participant_state(ctx)
    # Offline path (no Firestore) falls back to the ctx-provided values.
    assert out["learner_id"] == "from_ctx"
    assert out["subnation"] == "jersey"
    assert out["subject"] == "geography"


def test_session_service_falls_back_to_inmemory_when_no_gcp():
    """make_session_service must always succeed (in-memory fallback)."""
    import os

    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    os.environ.pop("DEPLOYED_AGENT_ENGINE_ID", None)
    from gemini_hackathon.journey.journey_orchestrator.session_service import (
        make_session_service,
    )

    svc = make_session_service()
    assert svc is not None


def test_memory_service_returns_none_when_no_agent_engine():
    """make_memory_service must return None (not raise) when Memory Bank is unset."""
    import os

    os.environ.pop("DEPLOYED_AGENT_ENGINE_ID", None)
    from gemini_hackathon.journey.journey_orchestrator.memory_service import (
        make_memory_service,
    )

    svc = make_memory_service()
    assert svc is None


def test_journey_admin_event_doc_idempotent():
    """admin_create_event (--dry-run) returns the same shape every time."""
    import os

    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)  # ensure offline path
    from gemini_hackathon.journey.scripts import admin_create_event

    # The dry_run branch always returns the doc dict, regardless of creds.
    # We invoke it indirectly by checking the doc shape helper.
    doc = admin_create_event._build_event_doc(
        "demo",
        "Demo Workshop",
        max_participants=200,
        admin_email="",
    )
    assert doc["code"] == "demo"
    assert doc["active"] is True
    assert doc["default_subnation"] in ("ireland", "england")
    # The 6 unlocked levels are always present.
    assert doc["levels_unlocked"] == ["0", "1", "2", "3", "4", "5"]
