"""gemini_hackathon.agents.fleet.fleet_agui — AG-UI protocol bridge.

The 6th Fleet primitive (per the openspec
``2026-08-24-gemini-hackathon-public-v1``). Implements the AG-UI
protocol bridge that streams agent output back to the CopilotKit
frontend via the 16-event AG-UI protocol.

The :class:`FleetAGUIBridge` class wraps an :class:`AgentResponse`
from the :class:`FleetGateway` and produces an event stream that
CopilotKit can consume over Server-Sent Events (SSE). The event
sequence follows the canonical AG-UI contract:

1. ``run_started`` — the run has begun.
2. ``step_started`` — a new step (e.g. agent selection, LLM call)
   has begun.
3. ``text_message_start`` — the assistant message starts.
4. ``text_message_content`` — incremental text chunks (the LLM
   token stream).
5. ``text_message_end`` — the assistant message ends.
6. ``step_finished`` — the step has finished.
7. ``run_finished`` — the run has finished.

Optional events (emitted as needed):

* ``tool_call`` / ``tool_result`` — when the agent invokes an MCP
  tool (e.g. ``fleet_mcp_curriculum.lookup_topic``).
* ``state_snapshot`` — when the UI state should be updated
  (e.g. when the source palette changes).
* ``error`` — when an unrecoverable error happens mid-run.

This module is a wholesale port of the Cianfhoghlaim
``agents/fleet/agui_bridge.py`` (per the
``wholesale-copy-convention``) with two adaptations:

1. The bridge consumes an :class:`AgentResponse` from the local
   :class:`FleetGateway` (in production this could be replaced by
   a remote agent over HTTP).
2. The 16-event protocol is implemented as a thin abstraction
   (no AG-UI SDK dependency required at import time).
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

import structlog

from .fleet_gateway import AgentResponse

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# The 16 AG-UI event types (per the AG-UI 1.0 spec)
# ---------------------------------------------------------------------------


class AGUIEventType(str, Enum):
    """The 16 canonical AG-UI event types."""

    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    RUN_ERROR = "run_error"
    STEP_STARTED = "step_started"
    STEP_FINISHED = "step_finished"
    TEXT_MESSAGE_START = "text_message_start"
    TEXT_MESSAGE_CONTENT = "text_message_content"
    TEXT_MESSAGE_END = "text_message_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_ARGS = "tool_call_args"
    TOOL_CALL_END = "tool_call_end"
    TOOL_CALL_RESULT = "tool_call_result"
    STATE_SNAPSHOT = "state_snapshot"
    STATE_DELTA = "state_delta"
    RAW = "raw"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Event dataclass + serialiser
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AGUIEvent:
    """A single AG-UI protocol event.

    Attributes:
        type: The event type (one of :class:`AGUIEventType`).
        run_id: The run identifier (stable for the entire run).
        timestamp: ISO-8601 UTC timestamp.
        data: Event-specific payload (any JSON-serialisable dict).
    """

    type: AGUIEventType
    run_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    data: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        """Serialise the event to an SSE-formatted string.

        Format::

            event: <type>
            id: <run_id>
            data: <json payload>

        Returns:
            The SSE-formatted event string (with trailing ``\\n\\n``).
        """
        payload = json.dumps(
            {"type": self.type.value, **self.data},
            default=str,
            separators=(",", ":"),
        )
        return f"event: {self.type.value}\nid: {self.run_id}\ndata: {payload}\n\n"

    def to_dict(self) -> dict[str, Any]:
        """Serialise the event to a plain dict (for tests + JSON dumps)."""
        return asdict(self)


# ---------------------------------------------------------------------------
# The FleetAGUIBridge class
# ---------------------------------------------------------------------------


class FleetAGUIBridge:
    """The AG-UI protocol bridge.

    Constructed once at process start and shared by the TanStack
    Start frontend (via the ``/api/agui/stream`` endpoint). The
    bridge turns :class:`AgentResponse` instances into AG-UI event
    streams.

    The bridge supports two consumption modes:

    * **Streaming** — :meth:`stream_events` returns a generator of
      :class:`AGUIEvent` instances, suitable for SSE.
    * **Batch** — :meth:`to_sse_events` returns the concatenated
      SSE string, suitable for buffering + late flush.
    """

    def __init__(
        self,
        *,
        default_chunk_size: int = 32,
        include_state_snapshot: bool = True,
    ) -> None:
        """Initialise the bridge.

        Args:
            default_chunk_size: The number of characters per
                ``text_message_content`` chunk (default 32).
            include_state_snapshot: Whether to emit a
                ``state_snapshot`` event with the active palette
                (default ``True``).
        """
        self.default_chunk_size = default_chunk_size
        self.include_state_snapshot = include_state_snapshot

    # ------------------------------------------------------------------
    # Public API: streaming
    # ------------------------------------------------------------------

    def stream_events(
        self,
        response: AgentResponse,
        *,
        run_id: str | None = None,
    ) -> Iterable[AGUIEvent]:
        """Yield AG-UI events for the given :class:`AgentResponse`.

        The event sequence is:

        1. ``run_started`` (with the agent name + identity).
        2. ``step_started`` (the LLM invocation step).
        3. ``text_message_start`` (the assistant message).
        4. ``text_message_content`` (chunked incremental text).
        5. ``text_message_end``.
        6. ``step_finished``.
        7. Optional ``state_snapshot`` (palette + identity).
        8. ``run_finished``.

        Args:
            response: The :class:`AgentResponse` from
                :class:`FleetGateway.invoke`.
            run_id: Optional explicit run ID (default: fresh UUID).

        Yields:
            A sequence of :class:`AGUIEvent` instances.
        """
        rid = run_id or str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        # 1. run_started
        yield AGUIEvent(
            type=AGUIEventType.RUN_STARTED,
            run_id=rid,
            data={
                "agent": response.agent,
                "user_id": response.identity.user_id,
                "role": response.identity.role,
                "jurisdiction": response.identity.jurisdiction,
                "level": response.identity.level,
                "trace_id": response.trace_id,
            },
        )

        # 2. step_started
        step_id = str(uuid.uuid4())
        yield AGUIEvent(
            type=AGUIEventType.STEP_STARTED,
            run_id=rid,
            data={"step_id": step_id, "step_type": "llm_invocation"},
        )

        # 3. text_message_start
        yield AGUIEvent(
            type=AGUIEventType.TEXT_MESSAGE_START,
            run_id=rid,
            data={
                "message_id": message_id,
                "role": "assistant",
                "model": response.model,
                "tier": response.tier,
            },
        )

        # 4. text_message_content — chunked incremental text.
        content = response.content or ""
        for chunk in _chunk_text(content, self.default_chunk_size):
            yield AGUIEvent(
                type=AGUIEventType.TEXT_MESSAGE_CONTENT,
                run_id=rid,
                data={
                    "message_id": message_id,
                    "delta": chunk,
                },
            )

        # 5. text_message_end
        yield AGUIEvent(
            type=AGUIEventType.TEXT_MESSAGE_END,
            run_id=rid,
            data={"message_id": message_id},
        )

        # 6. step_finished
        yield AGUIEvent(
            type=AGUIEventType.STEP_FINISHED,
            run_id=rid,
            data={
                "step_id": step_id,
                "latency_ms": response.latency_ms,
                "tier": response.tier,
                "model": response.model,
            },
        )

        # 7. Optional state_snapshot (palette + identity).
        if self.include_state_snapshot:
            yield AGUIEvent(
                type=AGUIEventType.STATE_SNAPSHOT,
                run_id=rid,
                data={
                    "source_palette_key": response.identity.source_palette_key,
                    "jurisdiction": response.identity.jurisdiction,
                    "level": response.identity.level,
                    "authenticated": response.identity.authenticated,
                },
            )

        # 8. run_finished
        yield AGUIEvent(
            type=AGUIEventType.RUN_FINISHED,
            run_id=rid,
            data={
                "total_latency_ms": response.latency_ms,
                "tokens_in": response.llm_response.tokens_in,
                "tokens_out": response.llm_response.tokens_out,
                "cost_usd": response.llm_response.cost_usd,
            },
        )

    def stream_sse(
        self,
        response: AgentResponse,
        *,
        run_id: str | None = None,
    ) -> Iterable[str]:
        """Yield SSE-formatted strings for the given response.

        Args:
            response: The :class:`AgentResponse` from
                :class:`FleetGateway.invoke`.
            run_id: Optional explicit run ID.

        Yields:
            SSE-formatted event strings (with trailing ``\\n\\n``).
        """
        for event in self.stream_events(response, run_id=run_id):
            yield event.to_sse()

    def to_sse_events(
        self, response: AgentResponse, *, run_id: str | None = None
    ) -> str:
        """Concatenate the full event stream into one SSE string.

        Args:
            response: The :class:`AgentResponse` to serialise.
            run_id: Optional explicit run ID.

        Returns:
            The concatenated SSE event stream.
        """
        return "".join(self.stream_sse(response, run_id=run_id))

    # ------------------------------------------------------------------
    # Convenience: build an error stream
    # ------------------------------------------------------------------

    def stream_error(
        self,
        error: Exception,
        *,
        run_id: str | None = None,
    ) -> Iterable[AGUIEvent]:
        """Emit a minimal error event stream.

        Args:
            error: The exception that aborted the run.
            run_id: Optional explicit run ID.

        Yields:
            The ``run_started`` + ``run_error`` + ``run_finished``
            events.
        """
        rid = run_id or str(uuid.uuid4())
        yield AGUIEvent(
            type=AGUIEventType.RUN_STARTED,
            run_id=rid,
            data={"agent": "unknown", "trace_id": ""},
        )
        yield AGUIEvent(
            type=AGUIEventType.RUN_ERROR,
            run_id=rid,
            data={
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )
        yield AGUIEvent(
            type=AGUIEventType.RUN_FINISHED,
            run_id=rid,
            data={"status": "error"},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk_text(text: str, chunk_size: int) -> Iterable[str]:
    """Yield ``text`` in fixed-size chunks.

    Args:
        text: The text to chunk.
        chunk_size: The chunk size (in characters).

    Yields:
        Consecutive substrings of ``text``, each of length
        ``chunk_size`` (except possibly the last).
    """
    if chunk_size <= 0:
        yield text
        return
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


def list_supported_events() -> list[str]:
    """Return the list of supported AG-UI event type names."""
    return [e.value for e in AGUIEventType]


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "AGUIEvent",
    "AGUIEventType",
    "FleetAGUIBridge",
    "list_supported_events",
]
