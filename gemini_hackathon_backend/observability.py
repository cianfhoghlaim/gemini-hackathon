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

    def try_init_cloud_logging() -> Any:  # type: ignore[no-redef]
        return None


# ---------------------------------------------------------------------------
# Module-level singletons, populated by `init_backend_observability()`.
# ---------------------------------------------------------------------------
_LANGFUSE_CLIENT: Any = None
_MLFLOW: Any = None
_CLOUD_LOGGING_CLIENT: Any = None


def init_backend_observability() -> dict[str, Any]:
    """Initialise Langfuse, MLflow, and Cloud Logging clients.

    Called once at FastAPI startup. Returns a dict of the live handles
    (values may be None when the env vars are absent) so the caller can
    surface them in /healthz.
    """
    global _LANGFUSE_CLIENT, _MLFLOW, _CLOUD_LOGGING_CLIENT
    _LANGFUSE_CLIENT = try_init_langfuse()
    _MLFLOW = try_init_mlflow()
    _CLOUD_LOGGING_CLIENT = try_init_cloud_logging()
    return {
        "langfuse": _LANGFUSE_CLIENT is not None,
        "mlflow": _MLFLOW is not None,
        "cloud_logging": _CLOUD_LOGGING_CLIENT is not None,
    }


def get_langfuse() -> Any:
    return _LANGFUSE_CLIENT


def get_mlflow() -> Any:
    return _MLFLOW


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