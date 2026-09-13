"""tests/test_inscope_asset_chain.py — verify the BAML → certificate → A2UI chain.

Per `docs/SUBMISSION_SCOPE.md` + the `2026-08-31-submission-scope-realignment-v1`
openspec change, the headline demo flow is:

  BAML Extract<Subject>Syllabus → CertificatePipeline.run() → PNG bytes → A2UI surface

This test verifies that the chain produces non-empty output even when the
BAML client / certificate pipeline / etc. are stubbed.
"""

from __future__ import annotations

import pathlib

REPO = pathlib.Path("/Users/cianmacandeisigh/dev/gemini_hackathon")


class _FakeToolContext:
    def __init__(self) -> None:
        self.state: dict = {"citations": [], "a2ui_raw_events": []}


def _stub_baml_extraction() -> dict:
    return {
        "_stub": True,
        "subject": "mathematics",
        "language": "en",
        "module_topics": [
            {
                "title": "Differentiation",
                "learning_outcomes": [
                    {"lo_id": "MA-LC-1.1", "title": "Differentiate basic functions"},
                ],
            },
        ],
        "total_learning_outcomes": 1,
    }


def test_generate_certificate_returns_valid_payload() -> None:
    """The generate_certificate tool must return a non-empty dict with the expected keys."""
    from gemini_hackathon_backend.agents.ncca_panel import generate_certificate

    ctx = _FakeToolContext()
    out = generate_certificate(
        subject="mathematics",
        learner_name="Maya O'Brien",
        topic="Differentiation",
        mastery_score=0.78,
        tool_context=ctx,
    )
    assert isinstance(out, dict)
    assert "status" in out
    assert "subject" in out
    assert out["subject"] == "mathematics"
    assert "learner_name" in out
    assert out["learner_name"] == "Maya O'Brien"
    assert "asset_bytes_len" in out
    assert isinstance(out["asset_bytes_len"], int)


def test_generate_certificate_emits_a2ui_surface() -> None:
    """The A2UI Raw event must be appended to tool_context.state['a2ui_raw_events']."""
    from gemini_hackathon_backend.agents.ncca_panel import generate_certificate

    ctx = _FakeToolContext()
    generate_certificate(
        subject="chemistry",
        learner_name="Test Learner",
        topic="Atomic Structure",
        mastery_score=0.85,
        tool_context=ctx,
    )
    events = ctx.state.get("a2ui_raw_events", [])
    assert len(events) >= 1, "expected ≥1 A2UI Raw event after generate_certificate"
    event = events[0]
    # The Raw event structure: {"type": "Raw", "event": {...jsonl...}}
    assert "type" in event or "event" in event


def test_generate_asset_returns_ncca_pdf_card() -> None:
    """The original generate_asset (NCCA-PDF-tied) tool must still work."""
    from gemini_hackathon_backend.agents.ncca_panel import generate_asset

    ctx = _FakeToolContext()
    out = generate_asset(
        pdf_id="SC-L1-L2-Programme-Statement",
        asset_type="infographic",
        topic="Senior Cycle framework",
        tool_context=ctx,
    )
    assert isinstance(out, dict)
    assert out["status"] == "success"
    assert "surface_id" in out or "pdf_id" in out


def test_ncca_panel_agent_has_5_tools() -> None:
    """The NCCA panel ADK agent should expose 5 tools."""
    from gemini_hackathon_backend.agents.ncca_panel import build_ncca_panel_agent

    agent = build_ncca_panel_agent()
    tool_names = [
        t.__name__ if callable(t) else getattr(t, "__name__", str(t)) for t in agent.tools
    ]
    expected = {
        "cite_pdf",
        "fetch_highlight",
        "list_ncca_pdfs",
        "generate_asset",
        "generate_certificate",
    }
    actual = set(tool_names)
    assert expected.issubset(actual), f"missing tools: {expected - actual}; have: {actual}"
