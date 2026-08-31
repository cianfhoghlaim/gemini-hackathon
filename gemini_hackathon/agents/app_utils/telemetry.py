"""App utilities for the gemini_hackathon ADK agent.

Mirrors the canonical google-adk starter-pack pattern:
- :func:`setup_telemetry` configures OpenTelemetry + GenAI telemetry with
  GCP-native Cloud Trace + Cloud Logging + GCS upload (NO_CONTENT mode).
- :func:`ensure_vertex_env` sets the standard Vertex AI env vars before
  the ADK runtime instantiates the ``Gemini`` model class.
- :func:`build_runner` wraps the ``LlmAgent`` in the production-grade
  ``App(root_agent=..., name=...)`` container so telemetry, session, and
  artifact services work the way the Agent Engine deploy path expects.

Lifted from ``research/agents/google-adk/app/agent.py`` +
``research/agents/google-adk/app/app_utils/telemetry.py`` and adapted
to the gemini_hackathon agent tree (no A2A protocol surface here).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def ensure_vertex_env(*, location: str = "global") -> str | None:
    """Set the standard Vertex AI env vars. Returns the resolved project_id.

    Idempotent — safe to call multiple times. If ``GOOGLE_CLOUD_PROJECT``
    is already set, it is honoured; otherwise we read it from
    ``google.auth.default()``.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        try:
            import google.auth

            _, project_id = google.auth.default()
            if project_id:
                os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        except Exception as e:
            logger.debug("ensure_vertex_env: google.auth.default() failed: %s", e)
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", location)
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
    return project_id


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry + GenAI telemetry with GCS upload.

    Mirrors the canonical starter-pack telemetry setup:
      - GCP-native Cloud Trace + Cloud Logging exporters (always on)
      - Optional GCS prompt-response upload in NO_CONTENT mode
        (only when LOGS_BUCKET_NAME + capture-mode env are set)

    Safe to call when ``google.adk.telemetry.*`` is unavailable (e.g. dev
    without adk installed) — returns ``None`` and logs a debug message.
    """
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false")

    if bucket and capture_content != "false":
        logger.info(
            "Prompt-response logging enabled — mode: NO_CONTENT "
            "(metadata only, no prompts/responses)"
        )
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault("OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental")
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=gemini-hackathon,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )
    else:
        logger.info(
            "Prompt-response logging disabled "
            "(set LOGS_BUCKET_NAME + OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT "
            "to enable)"
        )

    try:
        import google.auth
        from google.adk.telemetry.google_cloud import (
            get_gcp_exporters,
            get_gcp_resource,
        )
        from google.adk.telemetry.setup import maybe_set_otel_providers
    except ImportError as e:
        logger.debug("setup_telemetry: google-adk telemetry not available: %s", e)
        return bucket

    try:
        credentials, project_id = google.auth.default()
    except Exception as e:
        logger.debug("setup_telemetry: google.auth.default() failed: %s", e)
        return bucket

    otel_hooks = get_gcp_exporters(
        enable_cloud_tracing=True,
        enable_cloud_metrics=False,
        enable_cloud_logging=True,
        google_auth=(credentials, project_id),
    )
    otel_resource = get_gcp_resource(project_id)
    maybe_set_otel_providers(
        otel_hooks_to_setup=[otel_hooks],
        otel_resource=otel_resource,
    )

    try:
        from google.adk.cli.adk_web_server import (
            _setup_instrumentation_lib_if_installed,
        )

        _setup_instrumentation_lib_if_installed()
    except ImportError:
        pass

    logger.info(
        "setup_telemetry: Cloud Trace + Cloud Logging exporters wired for project=%s bucket=%s",
        project_id,
        bucket or "(none)",
    )
    return bucket


def build_app(root_agent, *, name: str = "gemini_hackathon"):
    """Wrap a ``google.adk.agents.LlmAgent`` in the production ``App``.

    Mirrors the canonical starter-pack pattern at
    ``research/agents/google-adk/app/agent.py:77``:
        app = App(root_agent=root_agent, name="app")

    The App wrapper is required for:
      - Cloud Run / Agent Engine deployment (telemetry, session, artifact)
      - The A2A protocol surface (not used here, but the wrapper enables it)
      - The MCP server mounting on the App object

    Returns ``root_agent`` unchanged if the App class is unavailable
    (so callers can always use the returned agent).
    """
    try:
        from google.adk.apps.app import App  # type: ignore[import-not-found]
    except ImportError:
        logger.debug("build_app: google.adk.apps.app.App unavailable; returning root_agent")
        return root_agent

    try:
        return App(root_agent=root_agent, name=name)
    except Exception as e:
        logger.debug("build_app: App() construction failed (%s); returning root_agent", e)
        return root_agent


__all__ = [
    "build_app",
    "ensure_vertex_env",
    "setup_telemetry",
]
