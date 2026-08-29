"""gemini_hackathon.observability — Cloud Trace/Logging + Langfuse + MLflow + structlog.

Lightweight port of cianfhoghlaim/observability/* for the hackathon
project. Phase 7 of the GCP-first refactor added Cloud Trace + Cloud
Logging as the primary exporters (matching what `functions/src/
observability.ts` already does on the TypeScript side); Langfuse :3001 +
MLflow :5050 remain as optional cianfhoghlaim-parity exporters, used when
their env vars are set (typically local dev). All 4 are additive — none
excludes another; every one is env-gated and degrades to structured
logging alone when unconfigured.

Each LLM call (via ``call_llm``) emits a structlog event ``llm.invocation``
with the resolved tier + backend + latency. Agents emit
``agent.trace_opened`` + ``agent.trace_closed`` events. Asset generation
emits ``asset.generated`` events.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Bridge structlog to stdlib logging so caplog still works.
try:
    logging.basicConfig(level=logging.INFO)
except Exception:
    pass


@dataclass
class TraceContext:
    """A trace span for a single agent invocation."""
    agent: str
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    _start_ms: int = field(default_factory=lambda: int(time.time() * 1000), repr=False)

    def end(self) -> dict[str, Any]:
        duration_ms = int(time.time() * 1000) - self._start_ms
        return {
            "trace_id": self.trace_id,
            "agent": self.agent,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "duration_ms": duration_ms,
        }


@contextmanager
def trace_agent(
    agent: str,
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[TraceContext]:
    """Open a trace span for an agent invocation. Returns the context.

    Emits ``agent.trace_opened`` on entry + ``agent.trace_closed`` on exit.
    """
    ctx = TraceContext(
        agent=agent,
        session_id=session_id,
        user_id=user_id,
        metadata=metadata or {},
    )
    logger.info(
        "agent.trace_opened",
        agent=agent,
        trace_id=ctx.trace_id,
        session_id=session_id,
        user_id=user_id,
    )
    try:
        yield ctx
    finally:
        closed = ctx.end()
        logger.info(
            "agent.trace_closed",
            agent=agent,
            trace_id=ctx.trace_id,
            total_latency_ms=closed["duration_ms"],
        )


def try_init_langfuse() -> Any:
    """Return a Langfuse client if LANGFUSE_PUBLIC_KEY is set, else None.

    The client is used as a context manager; never required.
    """
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        logger.info("observability.langfuse_skipped reason='LANGFUSE_PUBLIC_KEY unset'")
        return None
    try:
        from langfuse import Langfuse  # type: ignore[import-not-found]
        client = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        logger.info("observability.langfuse_initialised")
        return client
    except Exception as e:
        logger.warning(f"observability.langfuse_unavailable reason='{type(e).__name__}: {e}'")
        return None


def try_init_mlflow() -> Any:
    """Return an MLflow tracking URI if MLFLOW_TRACKING_URI is set, else None."""
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        logger.info("observability.mlflow_skipped reason='MLFLOW_TRACKING_URI unset'")
        return None
    try:
        import mlflow  # type: ignore[import-not-found]
        mlflow.set_tracking_uri(uri)
        logger.info(f"observability.mlflow_initialised tracking_uri={uri}")
        return mlflow
    except Exception as e:
        logger.warning(f"observability.mlflow_unavailable reason='{type(e).__name__}: {e}'")
        return None


def try_init_cloud_logging() -> Any:
    """Attach a Cloud Logging handler to the root logger if `GCP_PROJECT_ID`
    is set, else return None. Idempotent-ish: safe to call more than once
    (the underlying client just adds another handler; harmless in a
    single-process Cloud Run instance).
    """
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        logger.info("observability.cloud_logging_skipped reason='GCP_PROJECT_ID unset'")
        return None
    try:
        from google.cloud import logging as cloud_logging  # noqa: PLC0415

        client = cloud_logging.Client(project=project_id)
        client.setup_logging(log_level=logging.INFO)
        logger.info("observability.cloud_logging_initialised", project_id=project_id)
        return client
    except Exception as e:
        logger.warning(f"observability.cloud_logging_unavailable reason='{type(e).__name__}: {e}'")
        return None


def try_init_cloud_trace() -> Any:
    """Register a Cloud Trace span exporter via OpenTelemetry if
    `GCP_PROJECT_ID` is set, else return None.

    Requires the optional `opentelemetry-exporter-gcp-trace` package
    (not a hard dependency of this repo — install it in the Cloud Run
    image if trace export is wanted; degrades to structlog-only tracing
    otherwise, which is always active via `trace_agent()` regardless).
    """
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        logger.info("observability.cloud_trace_skipped reason='GCP_PROJECT_ID unset'")
        return None
    try:
        from opentelemetry import trace  # noqa: PLC0415
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter  # noqa: PLC0415
        from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter(project_id=project_id)))
        trace.set_tracer_provider(provider)
        logger.info("observability.cloud_trace_initialised", project_id=project_id)
        return trace.get_tracer(__name__)
    except ImportError:
        logger.info(
            "observability.cloud_trace_skipped "
            "reason='opentelemetry-exporter-gcp-trace not installed'"
        )
        return None
    except Exception as e:
        logger.warning(f"observability.cloud_trace_unavailable reason='{type(e).__name__}: {e}'")
        return None


def log_asset_generated(result: Any) -> None:
    """Emit the canonical ``asset.generated`` event for a generated asset."""
    p = result.provenance
    logger.info(
        "asset.generated",
        backend=p.get("backend", "unknown"),
        model_key=p.get("model_key", "unknown"),
        control_record_hash=p.get("control_record_hash", ""),
        seed=p.get("seed", 0),
        source_pdf_path=p.get("source_pdf_path", ""),
        source_page=p.get("source_page", 0),
        outcome_id=p.get("learning_outcome_id"),
        duration_ms=getattr(result, "duration_ms", 0),
    )


__all__ = [
    "TraceContext",
    "log_asset_generated",
    "trace_agent",
    "try_init_cloud_logging",
    "try_init_cloud_trace",
    "try_init_langfuse",
    "try_init_mlflow",
]
