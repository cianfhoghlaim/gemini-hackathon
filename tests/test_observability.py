"""Tests for gemini_hackathon.observability.

Covers:
- trace_agent emits opened + closed events with timing metadata.
- try_init_langfuse + try_init_mlflow are no-ops without keys (skip).
- log_asset_generated tolerates missing provenance keys (defensive).
- AssetResult from the image_gen router round-trips through observability.
"""

from __future__ import annotations

import structlog
from types import SimpleNamespace


def test_trace_agent_emits_opened_and_closed_events():
    from gemini_hackathon.observability import trace_agent
    with structlog.testing.capture_logs() as logs:
        with trace_agent(agent="smoke"):
            pass
    events = [e["event"] for e in logs]
    assert "agent.trace_opened" in events
    assert "agent.trace_closed" in events


def test_trace_agent_records_duration():
    from gemini_hackathon.observability import trace_agent
    with structlog.testing.capture_logs() as logs:
        with trace_agent(agent="smoke"):
            pass
    closed = [e for e in logs if e["event"] == "agent.trace_closed"][0]
    assert closed["total_latency_ms"] >= 0
    assert closed["agent"] == "smoke"


def test_try_init_langfuse_no_keys_returns_none():
    """Without LANGFUSE_PUBLIC_KEY, the wrapper returns None and logs a skip."""
    from gemini_hackathon.observability import try_init_langfuse
    import os
    os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
    assert try_init_langfuse() is None


def test_try_init_mlflow_no_uri_returns_none():
    """Without MLFLOW_TRACKING_URI, the wrapper returns None and logs a skip."""
    from gemini_hackathon.observability import try_init_mlflow
    import os
    os.environ.pop("MLFLOW_TRACKING_URI", None)
    assert try_init_mlflow() is None


def test_log_asset_generated_tolerates_missing_provenance_keys():
    """Even with a half-empty provenance dict, log_asset_generated does not
    raise KeyError. The contract is that observability never blocks the
    the asset pipeline."""
    from gemini_hackathon.observability import log_asset_generated
    class Stub:
        duration_ms = 50
        provenance = {}  # missing every key
    with structlog.testing.capture_logs() as logs:
        log_asset_generated(Stub())
    assert any(e["event"] == "asset.generated" for e in logs)


def test_log_asset_generated_with_real_router_result_round_trips():
    """A real AssetResult from ImageGenRouter flows through observability
    without losing any of the canonical provenance keys."""
    from gemini_hackathon.assets.image_gen import ImageGenRouter
    from gemini_hackathon.assets.control_record import AssetControlRecord

    rec = AssetControlRecord.from_syllabus_and_palette(
        source_pdf_path="/tmp/x.pdf",
        source_page=12,
        subject="Test",
        palette={"primary": "#00733B"},
    )
    result = ImageGenRouter().generate(rec)
    assert "control_record_hash" in result.provenance  # guard

    from gemini_hackathon.observability import log_asset_generated
    with structlog.testing.capture_logs() as logs:
        log_asset_generated(result)
    asset_event = [e for e in logs if e["event"] == "asset.generated"][0]
    assert asset_event["backend"] == result.backend.value
    assert asset_event["model_key"] == result.model_key
    assert asset_event["control_record_hash"] == result.provenance["control_record_hash"]
