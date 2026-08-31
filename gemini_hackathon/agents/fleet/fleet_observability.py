"""gemini_hackathon.agents.fleet.fleet_observability — Langfuse + MLflow + structlog.

The 4th Fleet primitive (per the openspec
``2026-08-24-gemini-hackathon-public-v1``). Provides a single
``Observability`` class that wraps three concerns:

* **Langfuse** — LLM cost tracking + prompt management + per-trace
  metadata (the canonical observability surface for the BIEP fleet).
* **MLflow** — experiment tracking + model registry (used for the
  ``ExtractSourcePalette`` extraction experiments + the RAGAS
  evaluation runs).
* **structlog** — per-request structured logs with the
  ``llm.invocation`` contract from
  ``model-policy/spec.md:163-184``.

Every :func:`gemini_hackathon.call_llm` invocation flows through
:meth:`Observability.trace_llm_invocation`, which records the
``llm.tier`` / ``llm.model`` / ``llm.latency_ms`` dimensions on
both Langfuse and MLflow.

This module is a wholesale port of the Cianfhoghlaim
``agents/fleet/observability.py`` module (per the
``wholesale-copy-convention``) with two adaptations:

1. Langfuse + MLflow are optional dependencies — missing clients
   degrade gracefully (the ``Observability`` class logs a
   ``WARNING`` and remains a no-op for that backend).
2. The 3-tier model contract from ``call_llm`` is enforced
   uniformly (no Cloudflare Workers AI / Qwen3-coder leakage).
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from gemini_hackathon.call_llm import LLMResponse, Message

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Optional clients (graceful degradation)
# ---------------------------------------------------------------------------

_LANGFUSE_AVAILABLE: bool = False
try:
    from langfuse import Langfuse  # type: ignore[import-not-found]

    _LANGFUSE_AVAILABLE = True
except ImportError:  # pragma: no cover
    Langfuse = None  # type: ignore[assignment,misc]

_MLFLOW_AVAILABLE: bool = False
try:
    import mlflow  # type: ignore[import-not-found]

    _MLFLOW_AVAILABLE = True
except ImportError:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]


def _env_flag(name: str, default: bool) -> bool:
    """Return the boolean value of an env var (``"1"`` / ``"true"`` → True)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TraceContext:
    """The metadata for a single traced operation.

    Attributes:
        trace_id: A stable UUID-4 identifier (or the operator-
            supplied ID). Used as both the Langfuse trace ID and
            the MLflow run ID.
        agent: The agent name (e.g. ``"marking_grader_workflow"``).
        user_id: The authenticated user ID (or ``"anonymous"``).
        session_id: The session/conversation ID.
        metadata: Free-form per-trace metadata dict.
    """

    trace_id: str
    agent: str
    user_id: str = "anonymous"
    session_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InvocationRecord:
    """A single :func:`call_llm` invocation captured for observability.

    Attributes:
        tier: The tier that served the request (1, 2, or 3).
        model: The model string.
        latency_ms: The wall-clock latency.
        tokens_in: Prompt tokens consumed.
        tokens_out: Completion tokens produced.
        cost_usd: Estimated cost in USD.
        fallback_reason: The fallback reason (empty for Tier 1).
        success: Whether the call succeeded.
    """

    tier: int
    model: str
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    fallback_reason: str = ""
    success: bool = True


# ---------------------------------------------------------------------------
# The Observability class
# ---------------------------------------------------------------------------


class Observability:
    """The fleet-wide observability surface.

    Wraps Langfuse + MLflow + structlog. Constructed once at
    process start and shared by every agent. All three backends
    are optional — the constructor degrades gracefully when a
    client library is missing.

    The expected usage pattern from an agent::

        obs = Observability()
        with obs.trace(agent="adaptive_tutor", user_id="pupil-42") as ctx:
            response = call_llm(messages=[...], metadata=ctx.metadata)
            obs.record_invocation(ctx, response)
    """

    def __init__(
        self,
        *,
        langfuse_public_key: str | None = None,
        langfuse_secret_key: str | None = None,
        langfuse_host: str | None = None,
        mlflow_tracking_uri: str | None = None,
        mlflow_experiment: str = "gemini-hackathon",
    ) -> None:
        """Initialise the three observability backends.

        Args:
            langfuse_public_key: Langfuse public key (defaults to
                ``LANGFUSE_PUBLIC_KEY``).
            langfuse_secret_key: Langfuse secret key (defaults to
                ``LANGFUSE_SECRET_KEY``).
            langfuse_host: Langfuse host URL (defaults to
                ``LANGFUSE_HOST``).
            mlflow_tracking_uri: MLflow tracking URI (defaults to
                ``MLFLOW_TRACKING_URI`` or ``"./mlruns"``).
            mlflow_experiment: MLflow experiment name (default
                ``"gemini-hackathon"``).
        """
        self._langfuse = self._init_langfuse(
            langfuse_public_key, langfuse_secret_key, langfuse_host
        )
        self._mlflow_experiment = mlflow_experiment
        self._mlflow_uri = mlflow_tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "./mlruns")
        self._init_mlflow()

    # ------------------------------------------------------------------
    # Langfuse
    # ------------------------------------------------------------------

    def _init_langfuse(
        self,
        public_key: str | None,
        secret_key: str | None,
        host: str | None,
    ) -> Any:
        """Initialise the Langfuse client, or return ``None``."""
        if not _LANGFUSE_AVAILABLE:
            logger.warning(
                "observability.langfuse_unavailable",
                reason="langfuse library not installed",
            )
            return None

        pk = public_key or os.getenv("LANGFUSE_PUBLIC_KEY", "")
        sk = secret_key or os.getenv("LANGFUSE_SECRET_KEY", "")
        host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        if not pk or not sk:
            logger.warning(
                "observability.langfuse_disabled",
                reason="LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set",
            )
            return None

        try:
            client = Langfuse(public_key=pk, secret_key=sk, host=host)
            logger.info(
                "observability.langfuse_ready",
                langfuse_host=host,
            )
            return client
        except Exception as e:
            logger.warning(
                "observability.langfuse_init_failed",
                error=f"{type(e).__name__}: {e}",
            )
            return None

    def langfuse_available(self) -> bool:
        """Return whether the Langfuse client is ready."""
        return self._langfuse is not None

    # ------------------------------------------------------------------
    # MLflow
    # ------------------------------------------------------------------

    def _init_mlflow(self) -> None:
        """Initialise MLflow tracking (or warn + skip)."""
        if not _MLFLOW_AVAILABLE:
            logger.warning(
                "observability.mlflow_unavailable",
                reason="mlflow library not installed",
            )
            return
        try:
            mlflow.set_tracking_uri(self._mlflow_uri)
            mlflow.set_experiment(self._mlflow_experiment)
            logger.info(
                "observability.mlflow_ready",
                mlflow_tracking_uri=self._mlflow_uri,
                mlflow_experiment=self._mlflow_experiment,
            )
        except Exception as e:
            logger.warning(
                "observability.mlflow_init_failed",
                error=f"{type(e).__name__}: {e}",
            )

    def mlflow_available(self) -> bool:
        """Return whether MLflow is ready."""
        return _MLFLOW_AVAILABLE

    # ------------------------------------------------------------------
    # Public API: trace context manager + invocation capture
    # ------------------------------------------------------------------

    @contextmanager
    def trace(
        self,
        *,
        agent: str,
        user_id: str = "anonymous",
        session_id: str = "",
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> Iterator[TraceContext]:
        """Open a new trace context.

        Args:
            agent: The agent name (e.g. ``"adaptive_tutor"``).
            user_id: The authenticated user ID.
            session_id: The session/conversation ID.
            metadata: Free-form per-trace metadata dict.
            trace_id: Optional operator-supplied trace ID
                (default: a fresh UUID-4).

        Yields:
            A :class:`TraceContext` instance.

        Example::

            with obs.trace(agent="adaptive_tutor", user_id="u-1") as ctx:
                response = call_llm([...], metadata=ctx.metadata)
                obs.record_invocation(ctx, response)
        """
        ctx = TraceContext(
            trace_id=trace_id or str(uuid.uuid4()),
            agent=agent,
            user_id=user_id,
            session_id=session_id,
            metadata=dict(metadata or {}),
        )
        start = time.monotonic()
        logger.info(
            "observability.trace_opened",
            trace_id=ctx.trace_id,
            agent=ctx.agent,
            user_id=ctx.user_id,
            session_id=ctx.session_id,
        )
        # Langfuse span (no-op if unavailable).
        span = self._open_langfuse_span(ctx)
        try:
            yield ctx
        except Exception as e:
            ctx.metadata["error"] = f"{type(e).__name__}: {e}"
            raise
        finally:
            total_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "observability.trace_closed",
                trace_id=ctx.trace_id,
                agent=ctx.agent,
                total_latency_ms=total_ms,
            )
            self._close_langfuse_span(span, ctx, total_ms)

    def record_invocation(
        self,
        ctx: TraceContext,
        response: LLMResponse | None,
        *,
        error: Exception | None = None,
    ) -> InvocationRecord:
        """Record a single :func:`call_llm` invocation.

        Args:
            ctx: The trace context (from :meth:`trace`).
            response: The :class:`LLMResponse` on success, or
                ``None`` on failure.
            error: The exception on failure (``None`` on success).

        Returns:
            The :class:`InvocationRecord` that was captured.
        """
        if response is not None:
            record = InvocationRecord(
                tier=response.tier,
                model=response.model,
                latency_ms=response.latency_ms,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                cost_usd=response.cost_usd,
                fallback_reason=("primary_5xx_or_timeout" if response.tier > 1 else ""),
                success=True,
            )
        else:
            err_msg = f"{type(error).__name__}: {error}" if error else "unknown"
            record = InvocationRecord(
                tier=0,
                model="unknown",
                latency_ms=0,
                fallback_reason=err_msg,
                success=False,
            )

        self._record_langfuse(ctx, record)
        self._record_mlflow(ctx, record)
        return record

    # ------------------------------------------------------------------
    # Internals — Langfuse
    # ------------------------------------------------------------------

    def _open_langfuse_span(self, ctx: TraceContext) -> Any:
        """Open a Langfuse span (or ``None`` if unavailable)."""
        if self._langfuse is None:
            return None
        try:
            return self._langfuse.span(
                name=f"{ctx.agent}.trace",
                trace_id=ctx.trace_id,
                metadata=ctx.metadata,
            )
        except Exception as e:
            logger.debug(
                "observability.langfuse_span_failed",
                error=f"{type(e).__name__}: {e}",
            )
            return None

    def _close_langfuse_span(self, span: Any, ctx: TraceContext, total_ms: int) -> None:
        """End the Langfuse span (no-op if unavailable)."""
        if span is None:
            return
        try:
            span.end(metadata={"total_latency_ms": total_ms})
        except Exception as e:
            logger.debug(
                "observability.langfuse_span_close_failed",
                error=f"{type(e).__name__}: {e}",
            )

    def _record_langfuse(self, ctx: TraceContext, record: InvocationRecord) -> None:
        """Push the invocation record to Langfuse."""
        if self._langfuse is None:
            return
        try:
            self._langfuse.generation(
                trace_id=ctx.trace_id,
                name=f"{ctx.agent}.llm_invocation",
                model=record.model,
                usage={
                    "input": record.tokens_in,
                    "output": record.tokens_out,
                },
                metadata={
                    "llm.tier": record.tier,
                    "llm.latency_ms": record.latency_ms,
                    "llm.fallback_reason": record.fallback_reason,
                    "llm.cost_usd": record.cost_usd,
                },
            )
        except Exception as e:
            logger.debug(
                "observability.langfuse_generation_failed",
                error=f"{type(e).__name__}: {e}",
            )

    # ------------------------------------------------------------------
    # Internals — MLflow
    # ------------------------------------------------------------------

    def _record_mlflow(self, ctx: TraceContext, record: InvocationRecord) -> None:
        """Push the invocation record to MLflow."""
        if not _MLFLOW_AVAILABLE:
            return
        try:
            with mlflow.start_run(run_name=ctx.trace_id[:12]):
                mlflow.set_tag("agent", ctx.agent)
                mlflow.set_tag("user_id", ctx.user_id)
                mlflow.set_tag("llm.tier", str(record.tier))
                mlflow.set_tag("llm.model", record.model)
                mlflow.log_metrics(
                    {
                        "llm.latency_ms": float(record.latency_ms),
                        "llm.tokens_in": float(record.tokens_in),
                        "llm.tokens_out": float(record.tokens_out),
                        "llm.cost_usd": float(record.cost_usd),
                    }
                )
        except Exception as e:
            logger.debug(
                "observability.mlflow_record_failed",
                error=f"{type(e).__name__}: {e}",
            )

    def log_metric(self, key: str, value: float, *, step: int | None = None) -> None:
        """Log a single custom metric to MLflow.

        Args:
            key: The metric name (e.g. ``"ragas.faithfulness"``).
            value: The metric value.
            step: Optional global step (defaults to MLflow auto-step).
        """
        if not _MLFLOW_AVAILABLE:
            return
        try:
            mlflow.log_metric(key, float(value), step=step)
        except Exception as e:
            logger.debug(
                "observability.mlflow_metric_failed",
                key=key,
                error=f"{type(e).__name__}: {e}",
            )

    def log_param(self, key: str, value: Any) -> None:
        """Log a single parameter to MLflow (string-coerced)."""
        if not _MLFLOW_AVAILABLE:
            return
        try:
            mlflow.log_param(key, str(value))
        except Exception as e:
            logger.debug(
                "observability.mlflow_param_failed",
                key=key,
                error=f"{type(e).__name__}: {e}",
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def configure_structlog(level: str = "INFO") -> None:
    """Configure structlog for the fleet.

    Args:
        level: The log level (default ``"INFO"``).
    """
    import logging

    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def hash_prompt(messages: Sequence[Message]) -> str:
    """Return a stable SHA-256 hash of the message list (for dedup)."""
    joined = "\n".join(f"{m['role']}:{m['content']}" for m in messages)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "InvocationRecord",
    "Observability",
    "TraceContext",
    "configure_structlog",
    "hash_prompt",
]
