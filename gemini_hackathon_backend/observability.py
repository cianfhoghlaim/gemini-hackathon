"""gemini_hackathon_backend.observability — Langfuse + MLflow + Cloud Logging init for the ADK FastAPI service.

Re-uses the parent package's env-gated init functions (which already
gracefully degrade to structlog-only when Langfuse / MLflow env vars are
absent). Adds the ADK-specific extras:

  - FastAPI lifespan hook that calls all three init functions on startup
  - `trace_agui_run()` context manager that wraps an AG-UI request in a
    Langfuse trace + a structlog span (so every chat turn has both a
    parent trace in Langfuse and a `agent.trace_opened` event in
    structured logs)
  - `LiteLLMCallback` shim that forwards the LLM model + token usage to
    Langfuse as a generation span

When LANGFUSE_PUBLIC_KEY / MLFLOW_TRACKING_URI are unset (the dev default),
all of these become no-ops and the only observability surface is
structlog → Cloud Logging (via GCP_PROJECT_ID).
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Re-exports from the parent package's observability module so callers can
# `from gemini_hackathon_backend.observability import try_init_langfuse, ...`
# ---------------------------------------------------------------------------
try:
    from gemini_hackathon.observability import (
        try_init_cloud_logging,
        try_init_langfuse,
        try_init_mlflow,
    )
except ImportError as e:
    logger.warning(
        "gemini_hackathon.observability not importable (%s); backend observability will fall back to structlog only",
        e,
    )

    def try_init_langfuse() -> Any:  # type: ignore[no-redef]
        return None

    def try_init_mlflow() -> Any:  # type: ignore[no-redef]
        return None

    def try_init_adk_otel() -> None:  # type: ignore[no-redef]
        return None

    def try_init_openinference_langfuse() -> None:  # type: ignore[no-redef]
        return None


def try_init_openinference_langfuse() -> Any:
    """Phase 1 — auto-instrument every ADK call as a Langfuse span.

    Wraps ``GoogleADKInstrumentor().instrument()`` so every ADK LLM
    call, tool invocation, and agent run becomes a nested span under
    the parent Langfuse trace (set by ``AguiTraceMiddleware``). Replaces
    the manual ``record_generation()`` pattern when active.

    Returns the instrumentor on success, ``None`` when
    ``LANGFUSE_PUBLIC_KEY`` is unset or ``openinference-instrumentation-google-adk``
    is not installed.
    """
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        logger.info(
            "observability.openinference_skipped reason='LANGFUSE_PUBLIC_KEY unset'"
        )
        return None
    try:
        from openinference.instrumentation.google_adk import (  # type: ignore[import-not-found]
            GoogleADKInstrumentor,
        )
        instrumentor = GoogleADKInstrumentor()
        instrumentor.instrument()
        logger.info("observability.openinference_initialised")
        return instrumentor
    except ImportError as exc:
        logger.info(
            "observability.openinference_skipped reason=%s",
            f"{type(exc).__name__}: {exc}",
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "observability.openinference_unavailable reason=%s",
            f"{type(exc).__name__}: {exc}",
        )
        return None


def try_init_adk_otel() -> Any:
    """Phase 1 — wire the ADK-native OpenTelemetry pipeline.

    Auto-streams every ADK LLM call, tool invocation, and agent run as
    an OTel span to Cloud Trace + Cloud Logging, following the
    OpenTelemetry GenAI semantic conventions. The Vertex AI Application
    Monitoring dashboards auto-populate from these spans.

    Returns the otel hooks object on success, ``None`` when the env
    vars are unset (``GCP_PROJECT_ID`` / ``GOOGLE_CLOUD_PROJECT``) or
    when ``google-adk`` is not importable.

    Per the ADK 2 docs at ``adk.dev/observability/logging/``:
    ``get_gcp_exporters(enable_cloud_logging=True)`` + ``maybe_set_otel_providers``.
    """
    project_id = (
        os.environ.get("GCP_PROJECT_ID", "").strip()
        or os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    )
    if not project_id:
        logger.info(
            "observability.adk_otel_skipped reason='GCP_PROJECT_ID unset'"
        )
        return None
    # Set the OpenTelemetry resource attributes (service name + namespace).
    # Done OUTSIDE the try block so the env vars are setdefault'd even
    # when google.adk isn't importable — operators can verify the
    # service name via /healthz and downstream exporters will pick it up
    # when google.adk is installed.
    os.environ.setdefault(
        "OTEL_SERVICE_NAME",
        os.environ.get("OTEL_SERVICE_NAME", "gemini-hackathon-adk"),
    )
    os.environ.setdefault(
        "OTEL_RESOURCE_ATTRIBUTES",
        "service.namespace=gemini-hackathon,"
        f"service.version={os.environ.get('COMMIT_SHA', 'dev')},"
        "deployment.environment=hackathon",
    )
    # Privacy: never log full prompts in Cloud Run (use GCS upload
    # for full-prompt retention if needed).
    os.environ.setdefault(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "NO_CONTENT"
    )

    try:
        from google.adk.telemetry.google_cloud import (  # type: ignore[import-not-found]
            get_gcp_exporters,
            get_gcp_resource,
        )
        from google.adk.telemetry.setup import (  # type: ignore[import-not-found]
            maybe_set_otel_providers,
        )

        otel_hooks = get_gcp_exporters(
            enable_cloud_tracing=True,
            enable_cloud_metrics=False,
            enable_cloud_logging=True,
        )
        otel_resource = get_gcp_resource(project_id)
        maybe_set_otel_providers(
            otel_hooks_to_setup=[otel_hooks],
            otel_resource=otel_resource,
        )
        logger.info(
            "observability.adk_otel_initialised",
            project_id=project_id,
            service_name=os.environ["OTEL_SERVICE_NAME"],
        )
        return otel_hooks
    except ImportError as exc:
        logger.info(
            "observability.adk_otel_skipped reason=%s",
            f"{type(exc).__name__}: {exc}",
        )
        return None
    except Exception as exc:  # noqa: BLE001 — observability is opt-in
        logger.warning(
            "observability.adk_otel_unavailable reason=%s",
            f"{type(exc).__name__}: {exc}",
        )
        return None


def try_init_cloud_logging() -> Any:  # type: ignore[no-redef]
        return None


# ---------------------------------------------------------------------------
# Module-level singletons, populated by `init_backend_observability()`.
# ---------------------------------------------------------------------------
_LANGFUSE_CLIENT: Any = None
_MLFLOW: Any = None
_CLOUD_LOGGING_CLIENT: Any = None
# Phase 1: ADK-native OTel hooks (Cloud Trace + Cloud Logging via OTLP).
# Populated by try_init_adk_otel(); truthy when the pipeline is active.
_ADK_OTEL_HOOKS: Any = None
# Phase 1: OpenInference Langfuse instrumentor handle. Truthy when the
# auto-instrumentation succeeded (LANGFUSE_PUBLIC_KEY set + the openinference
# package installed + google-adk importable).
_OPENINFERENCE_INSTRUMENTOR: Any = None


def init_backend_observability() -> dict[str, Any]:
    """Initialise ADK OTel, OpenInference, Langfuse, MLflow, and Cloud Logging.

    Called once at FastAPI startup. Returns a dict of the live handles
    (values may be None when the env vars are absent) so the caller can
    surface them in /healthz.

    Initialisation order matters:
      1. ADK OTel (auto-streams spans to Cloud Trace + Cloud Logging)
      2. OpenInference (auto-instruments ADK calls as Langfuse spans)
      3. Langfuse client (used by manual ``record_generation()``)
      4. MLflow (per-tool counters)
      5. Cloud Logging (raw stdlib handler — skipped if OTel is active
         to avoid double-logging)
    """
    global _ADK_OTEL_HOOKS, _OPENINFERENCE_INSTRUMENTOR
    global _LANGFUSE_CLIENT, _MLFLOW, _CLOUD_LOGGING_CLIENT
    _ADK_OTEL_HOOKS = try_init_adk_otel()
    _OPENINFERENCE_INSTRUMENTOR = try_init_openinference_langfuse()
    _LANGFUSE_CLIENT = try_init_langfuse()
    _MLFLOW = try_init_mlflow()
    # Avoid double-logging when the OTel pipeline is already streaming
    # every span to Cloud Logging via OTLP.
    _CLOUD_LOGGING_CLIENT = (
        None if _ADK_OTEL_HOOKS else try_init_cloud_logging()
    )
    return {
        "adk_otel": _ADK_OTEL_HOOKS is not None,
        "openinference": _OPENINFERENCE_INSTRUMENTOR is not None,
        "langfuse": _LANGFUSE_CLIENT is not None,
        "mlflow": _MLFLOW is not None,
        "cloud_logging": _CLOUD_LOGGING_CLIENT is not None,
    }


def get_langfuse() -> Any:
    return _LANGFUSE_CLIENT


def get_mlflow() -> Any:
    return _MLFLOW


def get_adk_otel_hooks() -> Any:
    """Return the ADK-native OTel hooks (Cloud Trace + Cloud Logging).

    Returns ``None`` when the pipeline is inactive (env vars unset or
    ``google-adk`` not installed).
    """
    return _ADK_OTEL_HOOKS


def get_openinference_instrumentor() -> Any:
    """Return the OpenInference Langfuse instrumentor handle.

    Returns ``None`` when auto-instrumentation is inactive.
    """
    return _OPENINFERENCE_INSTRUMENTOR


# ---------------------------------------------------------------------------
# AG-UI run tracing — opens a Langfuse trace + structlog span per request
# ---------------------------------------------------------------------------
@contextmanager
def trace_agui_run(
    *,
    agent: str,
    session_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Wrap an AG-UI request in a Langfuse trace (if configured) and a structlog span.

    The yielded dict is the `TraceHandle` — pass it to `record_generation()`
    on every LLM call inside the run so they nest under the parent trace.
    """
    trace_id = str(uuid.uuid4())
    started_ms = int(time.time() * 1000)
    handle: dict[str, Any] = {
        "trace_id": trace_id,
        "agent": agent,
        "session_id": session_id,
        "user_id": user_id,
        "langfuse_trace_id": None,
    }
    lf = get_langfuse()
    if lf is not None:
        try:
            lf_trace = lf.trace(
                id=trace_id,
                name=f"ag-ui:{agent}",
                session_id=session_id,
                user_id=user_id,
                metadata=metadata or {},
            )
            handle["langfuse_trace_id"] = getattr(lf_trace, "id", trace_id)
        except Exception as e:
            logger.warning(
                "trace_agui_run.langfuse_failed reason=%s", type(e).__name__
            )

    logger.info(
        "ag_ui.trace_opened",
        agent=agent,
        trace_id=trace_id,
        session_id=session_id,
        user_id=user_id,
        langfuse=handle["langfuse_trace_id"] is not None,
    )
    try:
        yield handle
    finally:
        duration_ms = int(time.time() * 1000) - started_ms
        logger.info(
            "ag_ui.trace_closed",
            agent=agent,
            trace_id=trace_id,
            total_latency_ms=duration_ms,
        )
        lf = get_langfuse()
        if lf is not None:
            try:
                lf.flush()
            except Exception as e:
                logger.warning(
                    "trace_agui_run.langfuse_flush_failed reason=%s",
                    type(e).__name__,
                )


def record_generation(
    handle: dict[str, Any],
    *,
    model: str,
    prompt: Any,
    completion: Any,
    usage: dict[str, int] | None = None,
    latency_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record an LLM generation as a Langfuse span under the parent trace."""
    lf = get_langfuse()
    if lf is None or handle.get("langfuse_trace_id") is None:
        return
    try:
        lf.generation(
            trace_id=handle["langfuse_trace_id"],
            name=model,
            model=model,
            input=prompt,
            output=completion,
            usage=usage or {},
            latency_ms=latency_ms,
            metadata=metadata or {},
        )
    except Exception as e:
        logger.warning(
            "record_generation.langfuse_failed reason=%s", type(e).__name__
        )


def log_mlflow_metric(name: str, value: float, *, step: int | None = None) -> None:
    """Log a single metric to MLflow (no-op when MLflow isn't configured)."""
    mf = get_mlflow()
    if mf is None:
        return
    try:
        mf.log_metric(name, value, step=step)
    except Exception as e:
        logger.warning("log_mlflow_metric.failed reason=%s", type(e).__name__)


@asynccontextmanager
async def lifespan_observability(app):  # type: ignore[no-untyped-def]
    """FastAPI lifespan hook — init at startup, flush at shutdown."""
    state = init_backend_observability()
    logger.info("observability.initialized", **state)
    try:
        yield
    finally:
        lf = get_langfuse()
        if lf is not None:
            try:
                lf.flush()
            except Exception:
                pass
            try:
                lf.shutdown()
            except Exception:
                pass
        logger.info("observability.shutdown")