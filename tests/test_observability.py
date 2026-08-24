"""Tests for the gemini_hackathon.observability module."""

from __future__ import annotations

import pytest
import structlog


def test_trace_agent_emits_opened_and_closed():
    from gemini_hackathon.observability import trace_agent

    with structlog.testing.capture_logs() as logs:
        with trace_agent(agent="marking_grader", user_id="teacher-1") as ctx:
            assert ctx.trace_id
            assert ctx.agent == "marking_grader"

    events = [e["event"] for e in logs]
    assert "agent.trace_opened" in events
    assert "agent.trace_closed" in events


def test_trace_agent_records_duration():
    from gemini_hackathon.observability import trace_agent

    with structlog.testing.capture_logs() as logs:
        with trace_agent(agent="curriculum_change_sensor"):
            pass

    closed = [e for e in logs if e["event"] == "agent.trace_closed"][0]
    assert "total_latency_ms" in closed
    assert closed["total_latency_ms"] >= 0


def test_trace_agent_propagates_exceptions():
    from gemini_hackathon.observability import trace_agent

    with structlog.testing.capture_logs() as logs:
        with pytest.raises(RuntimeError):
            with trace_agent(agent="flaky"):
                raise RuntimeError("kaboom")

    events = [e["event"] for e in logs]
    assert "agent.trace_opened" in events
    assert "agent.trace_closed" in events


def test_try_init_langfuse_no_key_returns_none(monkeypatch):
    from gemini_hackathon import observability
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    assert observability.try_init_langfuse() is None


def test_try_init_mlflow_no_uri_returns_none(monkeypatch):
    from gemini_hackathon import observability
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    assert observability.try_init_mlflow() is None


def test_log_asset_generated_emits_event():
    from dataclasses import dataclass, field
    from gemini_hackathon.observability import log_asset_generated

    @dataclass
    class _FakeResult:
        duration_ms: int = 42
        provenance: dict = field(default_factory=lambda: {
            "backend": "stub",
            "model_key": "deterministic-stub-v1",
            "control_record_hash": "abc123",
            "seed": 12345,
            "source_pdf_path": "/tmp/x.pdf",
            "source_page": 12,
            "learning_outcome_id": "LC-CHEM-3.1.2",
        })

    with structlog.testing.capture_logs() as logs:
        log_asset_generated(_FakeResult())
    events = [e["event"] for e in logs]
    assert "asset.generated" in events
    asset = [e for e in logs if e["event"] == "asset.generated"][0]
    assert asset["backend"] == "stub"
    assert asset["seed"] == 12345
    assert asset["control_record_hash"] == "abc123"
