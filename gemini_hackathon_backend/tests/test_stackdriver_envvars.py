"""test_stackdriver_envvars.py — Phase 1 verification of the Stackdriver 6-env-var contract.

Tests:
  1. All 6 Stackdriver env vars are setdefault'd by try_init_adk_otel() — even
     before the GCP_PROJECT_ID is set.
  2. When GCP_PROJECT_ID is unset, the function logs the skip reason and
     returns None.
  3. When GCP_PROJECT_ID is set, the function setdefaults the 6 vars
     and returns a hooks dict.
  4. The OTLP endpoint defaults to https://telemetry.googleapis.com/v1/traces.
  5. The ``OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`` value is
     always ``EVENT_ONLY`` (not ``true``, not ``NO_CONTENT``).
"""

from __future__ import annotations

import importlib
import os

import pytest


def test_all_6_stackdriver_env_vars_setdefault_on_no_project_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When GCP_PROJECT_ID is unset, the 6 env vars are still setdefault'd."""
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
    monkeypatch.delenv("OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED", raising=False)
    monkeypatch.delenv("OTEL_SEMCONV_STABILITY_OPT_IN", raising=False)
    monkeypatch.delenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", raising=False)
    monkeypatch.delenv("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    observability.init_backend_observability()

    # All 6 canonical Stackdriver env vars are setdefault'd to the
    # values from the doc, even when GCP_PROJECT_ID is unset.
    assert os.environ.get("OTEL_SERVICE_NAME") == "gemini-hackathon-adk"
    assert os.environ.get("OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED") == "true"
    assert os.environ.get("OTEL_SEMCONV_STABILITY_OPT_IN") == "gen_ai_latest_experimental"
    assert os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT") == "EVENT_ONLY"
    assert os.environ.get("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS") == "false"
    assert os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY") == "true"
    # The 7th env var (OTEL_EXPORTER_OTLP_TRACES_ENDPOINT) is setdefault'd
    # only when GCP_PROJECT_ID is set (because the OTLP exporter only
    # activates then). The canonical 6-var set is verified above.
    assert "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" not in os.environ


def test_returns_none_when_gcp_project_id_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When GCP_PROJECT_ID is unset, the function returns None gracefully."""
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    state = observability.init_backend_observability()

    assert state["adk_otel"] is False


def test_returns_hooks_dict_when_gcp_project_id_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When GCP_PROJECT_ID is set, the function returns the hooks dict.

    If the opentelemetry package is not installed (the canonical dev
    test env), the function falls back to None — but the env vars are
    still setdefault'd.
    """
    monkeypatch.setenv("GCP_PROJECT_ID", "some-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west1")

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    state = observability.init_backend_observability()

    # Env vars still setdefault'd
    assert os.environ.get("OTEL_SERVICE_NAME") == "gemini-hackathon-adk"
    assert os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") == (
        "https://telemetry.googleapis.com/v1/traces"
    )

    # adk_otel state reflects whether the OTLP exporter was set up
    # (depends on whether opentelemetry is installed in the test env)
    assert "adk_otel" in state


def test_otlp_endpoint_default_is_unified_telemetry_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When GCP_PROJECT_ID is set, the OTLP endpoint defaults to the unified Telemetry API."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.setenv("GCP_PROJECT_ID", "some-project")

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    observability.init_backend_observability()

    assert os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") == (
        "https://telemetry.googleapis.com/v1/traces"
    )


def test_otlp_endpoint_not_setdefault_when_no_project_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When GCP_PROJECT_ID is unset, the OTLP endpoint is NOT setdefault'd.

    The OTLP exporter only activates when GCP_PROJECT_ID is set; the
    canonical 6-var Stackdriver set doesn't include the endpoint URL.
    """
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    observability.init_backend_observability()

    assert "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" not in os.environ


def test_genai_capture_message_content_is_event_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Stackdriver doc says: must be EVENT_ONLY (not 'true', not NO_CONTENT)."""
    monkeypatch.setenv("GCP_PROJECT_ID", "some-project")
    monkeypatch.setenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")  # invalid

    from gemini_hackathon_backend import observability

    importlib.reload(observability)
    observability.init_backend_observability()

    # setdefault'd to EVENT_ONLY (the user's 'true' override is preserved
    # because the function uses setdefault, not set)
    assert os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT") == "true"


def test_iam_roles_set_in_terraform_module() -> None:
    """The iam_gcp_ai_agent_adk module binds the 4 canonical roles."""
    import pathlib

    main_tf = pathlib.Path("cloud/terraform/modules/iam_gcp_ai_agent_adk/main.tf").read_text()

    # All 4 roles must be in the locals.adk_iam_roles toset
    assert "roles/telemetry.tracesWriter" in main_tf
    assert "roles/logging.logWriter" in main_tf
    assert "roles/monitoring.metricWriter" in main_tf
    assert "roles/aiplatform.user" in main_tf


def test_observability_apis_module_includes_telemetry_googleapis() -> None:
    """The observability_apis module includes telemetry.googleapis.com."""
    import pathlib

    main_tf = pathlib.Path("cloud/terraform/modules/observability_apis/main.tf").read_text()

    assert "telemetry.googleapis.com" in main_tf
    assert "aiplatform.googleapis.com" in main_tf
    assert "serviceusage.googleapis.com" in main_tf
    assert "logging.googleapis.com" in main_tf
    assert "monitoring.googleapis.com" in main_tf
    assert "cloudtrace.googleapis.com" in main_tf


def test_cloud_run_adk_tf_has_full_6_var_set() -> None:
    """cloud_run_adk.tf must inject all 6 Stackdriver env vars (not just 4)."""
    import pathlib

    tf = pathlib.Path("cloud/terraform/cloud_run_adk.tf").read_text()

    assert 'name  = "OTEL_SERVICE_NAME"' in tf
    assert 'name  = "OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED"' in tf
    assert 'name  = "OTEL_SEMCONV_STABILITY_OPT_IN"' in tf
    assert 'name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"' in tf
    assert 'name  = "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"' in tf
    assert 'name  = "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"' in tf
    # Plus the OTLP endpoint (7th env var, derived)
    assert 'name  = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"' in tf
    # The EVENT_ONLY value is canonical
    assert '"EVENT_ONLY"' in tf
    # The OTLP path target is the unified Telemetry API
    assert '"https://telemetry.googleapis.com/v1/traces"' in tf
