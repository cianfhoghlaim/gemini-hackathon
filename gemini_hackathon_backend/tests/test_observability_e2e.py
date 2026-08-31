"""test_observability_e2e.py — Phase 8c verification of the observability layer end-to-end.

Tests:
  1. ``init_backend_observability()`` returns a dict with 5 keys.
  2. When GCP_PROJECT_ID is set + adk_otel init succeeds, ``adk_otel=True`` and
     ``cloud_logging=False`` (no double-logging).
  3. The OTel service name + resource attributes env vars are setdefault'd.
  4. ``build_memory_service()`` falls through to None when no env vars set.
  5. ``record_generation()`` is a safe no-op when Langfuse is inactive.
  6. ``log_mlflow_metric()`` is a safe no-op when MLflow is inactive.
"""

from __future__ import annotations

import importlib

import pytest


def test_init_returns_5_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    state = observability.init_backend_observability()

    assert isinstance(state, dict)
    assert set(state.keys()) == {"adk_otel", "openinference", "langfuse", "mlflow", "cloud_logging"}


def test_otlp_env_vars_setdefault_when_gcp_project_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When GCP_PROJECT_ID is set, OTEL_* env vars get setdefault'd."""
    monkeypatch.setenv("GCP_PROJECT_ID", "some-project")
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    monkeypatch.delenv("OTEL_RESOURCE_ATTRIBUTES", raising=False)
    monkeypatch.delenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", raising=False)

    import os

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    observability.init_backend_observability()

    assert os.environ.get("OTEL_SERVICE_NAME") == "gemini-hackathon-adk"
    assert "service.namespace=gemini-hackathon" in os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
    assert os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT") == "EVENT_ONLY"


def test_cloud_logging_skipped_when_adk_otel_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the OTel pipeline is active, raw Cloud Logging is skipped (no double-log)."""
    monkeypatch.setenv("GCP_PROJECT_ID", "some-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west1")

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    state = observability.init_backend_observability()

    if state["adk_otel"]:
        assert state["cloud_logging"] is False


def test_memory_service_falls_through_when_no_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    monkeypatch.delenv("DEPLOYED_AGENT_ENGINE_ID", raising=False)
    monkeypatch.delenv("GH_MEMORY_DIR", raising=False)

    result = memory_mod.build_memory_service()
    assert result is None


def test_record_generation_is_safe_noop_without_langfuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``record_generation`` no-ops cleanly when Langfuse is inactive."""
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    observability.init_backend_observability()

    # No Langfuse client -> record_generation is a silent no-op.
    observability.record_generation(
        {"trace_id": "fake"},
        model="test-model",
        prompt="hi",
        completion="hello",
        usage={"prompt_tokens": 1, "completion_tokens": 1},
    )
    # No exception -> pass.


def test_log_mlflow_metric_is_safe_noop_without_mlflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``log_mlflow_metric`` no-ops cleanly when MLflow is inactive."""
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    observability.init_backend_observability()

    observability.log_mlflow_metric("test.metric", 1.0)
    # No exception -> pass.


def test_getters_return_singletons() -> None:
    """The module-level singletons + getters are wired."""
    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    observability.init_backend_observability()
    assert observability.get_adk_otel_hooks() is observability._ADK_OTEL_HOOKS
    assert observability.get_openinference_instrumentor() is (
        observability._OPENINFERENCE_INSTRUMENTOR
    )
    assert observability.get_langfuse() is observability._LANGFUSE_CLIENT
    assert observability.get_mlflow() is observability._MLFLOW


def test_state_dict_keys_match_init_backend_signature() -> None:
    """``init_backend_observability()`` returns a dict with stable keys.

    The web frontend's ``/healthz`` endpoint surfaces this dict;
    keeping the keys stable is a Phase 8c contract.
    """
    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    state = observability.init_backend_observability()
    expected_keys = {
        "adk_otel",
        "openinference",
        "langfuse",
        "mlflow",
        "cloud_logging",
    }
    assert set(state.keys()) == expected_keys
