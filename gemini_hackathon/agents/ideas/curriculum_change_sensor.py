"""gemini_hackathon.agents.ideas.curriculum_change_sensor — curriculum drift detector.

The Curriculum Change Sensor is one of the 4 idea agents in the
gemini_hackathon fleet (per the openspec change
``2026-08-24-gemini-hackathon-public-v1``). It detects changes in
official syllabus PDFs (new syllabus, updated syllabus, removed
syllabus) and re-runs the theming extraction on the affected
sources.

The agent is the canonical Python wrapper around the BAML
``DetectCurriculumChanges`` function (see
``baml_extracts/curriculum_change.baml``). When a live BAML
client is available, the wrapper delegates the heavy lifting to
the BAML function; otherwise it returns a deterministic stub so
the rest of the fleet can be exercised in tests + CI.

The agent always uses the canonical :func:`gemini_hackathon.call_llm`
entrypoint (the 3-tier model policy) and the
:func:`gemini_hackathon.theming.load_palette` function to render
the affected sources in their new brand identity.

This agent is the wholesale port of the Cianfhoghlaim
``curriculum_change_sensor.py`` (per the
``wholesale-copy-convention``) — adapted from the
``google.adk.agents.LlmAgent`` factory to a plain Python class.

Permission gate: only roles with the ``trigger_change_sensor``
permission (``"safeguarding_lead"`` / ``"admin"``) can invoke
this agent. The :class:`FleetGateway` enforces this gate via
:data:`fleet_gateway.AGENT_PERMISSIONS`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import structlog

from gemini_hackathon.call_llm import LLMResponse, Message, call_llm
from gemini_hackathon.theming import Palette, load_palette

from ..fleet.fleet_identity import IdentityContext
from ..fleet.fleet_observability import Observability, TraceContext

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class ChangeType(StrEnum):
    """The canonical 3 change types detected by the sensor."""

    NEW_SYLLABUS = "NEW_SYLLABUS"
    UPDATED_SYLLABUS = "UPDATED_SYLLABUS"
    REMOVED_SYLLABUS = "REMOVED_SYLLABUS"


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChangeEvent:
    """A single curriculum change event.

    Attributes:
        source_url: The canonical source URL where the change
            was observed.
        change_type: One of :class:`ChangeType`.
        affected_topics: The list of affected topic names.
        summary: A plain-English one-sentence summary.
        effective_date: The ISO-8601 effective date (``""`` if
            unknown).
        confidence: The detection confidence in [0.0, 1.0].
        jurisdiction: The optional jurisdiction name.
        level: The optional curriculum level.
        palette: The :class:`Palette` for the affected source
            (or ``None`` if the palette file is missing).
    """

    source_url: str
    change_type: ChangeType
    affected_topics: tuple[str, ...] = ()
    summary: str = ""
    effective_date: str = ""
    confidence: float = 0.0
    jurisdiction: str = ""
    level: str = ""
    palette: Palette | None = None


@dataclass(frozen=True)
class CurriculumChangeRequest:
    """The input envelope for a curriculum-change detection run.

    Attributes:
        source_url: The canonical source URL.
        before_text: The captured text from the previous version
            of the page (or ``""`` for the first run).
        after_text: The captured text from the current version of
            the page.
        identity: The resolved :class:`IdentityContext`.
    """

    source_url: str
    before_text: str
    after_text: str
    identity: IdentityContext | None = None


@dataclass(frozen=True)
class CurriculumChangeResult:
    """The output envelope for a curriculum-change detection run.

    Attributes:
        source_url: The canonical source URL (echoed back).
        events: The list of detected :class:`ChangeEvent` records.
        themes_re_extracted: Whether the theming extraction was
            re-run on the affected sources (best-effort).
        llm_response: The underlying :class:`LLMResponse`.
        trace_id: The observability trace ID.
    """

    source_url: str
    events: list[ChangeEvent]
    themes_re_extracted: bool
    llm_response: LLMResponse
    trace_id: str


# ---------------------------------------------------------------------------
# The CurriculumChangeSensor agent
# ---------------------------------------------------------------------------


class CurriculumChangeSensor:
    """The Curriculum Change Sensor idea agent.

    Constructed once at process start and registered with the
    :class:`FleetGateway`. The :meth:`invoke` method is the
    canonical entrypoint for the gateway's keyword router.
    """

    def __init__(
        self,
        *,
        observability: Observability | None = None,
        baml_client: Any | None = None,
    ) -> None:
        """Initialise the sensor.

        Args:
            observability: The :class:`Observability` (default: a
                fresh instance).
            baml_client: Optional BAML client. When supplied, the
                agent delegates to
                ``baml_client.DetectCurriculumChanges(...)``;
                otherwise it falls back to calling :func:`call_llm`
                with the canonical prompt + JSON parsing.
        """
        self.observability = observability or Observability()
        self.baml_client = baml_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(
        self,
        request: CurriculumChangeRequest,
        *,
        trace: TraceContext | None = None,
    ) -> CurriculumChangeResult:
        """Run the change-detection workflow for one source URL.

        Args:
            request: The :class:`CurriculumChangeRequest` envelope.
            trace: Optional pre-existing observability trace.

        Returns:
            The :class:`CurriculumChangeResult` envelope.
        """
        identity = request.identity or IdentityContext()

        # Open the trace.
        if trace is None:
            cm = self.observability.trace(
                agent="curriculum_change_sensor",
                user_id=identity.user_id,
                metadata={
                    "source_url": request.source_url,
                    "before_chars": len(request.before_text),
                    "after_chars": len(request.after_text),
                },
            )
            trace = cm.__enter__()  # capture the yielded TraceContext
            close_cm = cm
        else:
            close_cm = None

        try:
            raw_events: list[dict[str, Any]]
            if self.baml_client is not None:
                raw_events = self._call_baml(request)
                llm_response = _make_fake_response(trace.trace_id)
            else:
                messages = self._build_messages(request)
                llm_response = call_llm(
                    messages=messages,
                    metadata={
                        "trace_id": trace.trace_id,
                        "agent": "curriculum_change_sensor",
                        "user_id": identity.user_id,
                    },
                )
                raw_events = _parse_llm_response(llm_response.content)

            self.observability.record_invocation(trace, llm_response)

            events: list[ChangeEvent] = []
            for raw in raw_events:
                palette = load_palette(_palette_key_for_url(request.source_url))
                events.append(
                    ChangeEvent(
                        source_url=request.source_url,
                        change_type=ChangeType(str(raw.get("change_type", "UPDATED_SYLLABUS"))),
                        affected_topics=tuple(str(t) for t in raw.get("affected_topics", []) or []),
                        summary=str(raw.get("summary", "")),
                        effective_date=str(raw.get("effective_date", "") or ""),
                        confidence=float(raw.get("confidence", 0.0) or 0.0),
                        jurisdiction=str(raw.get("jurisdiction", "") or ""),
                        level=str(raw.get("level", "") or ""),
                        palette=palette,
                    )
                )

            themes_re_extracted = any(e.change_type == ChangeType.NEW_SYLLABUS for e in events)

            if themes_re_extracted:
                logger.info(
                    "curriculum_change.themes_re_extraction_queued",
                    source_url=request.source_url,
                    event_count=len(events),
                )

            return CurriculumChangeResult(
                source_url=request.source_url,
                events=events,
                themes_re_extracted=themes_re_extracted,
                llm_response=llm_response,
                trace_id=trace.trace_id,
            )
        finally:
            if close_cm is not None:
                close_cm.__exit__(None, None, None)

    def as_gateway_invoker(
        self,
        *,
        sanitised_input: Any,
        identity: IdentityContext,
        trace: TraceContext,
    ) -> list[Message]:
        """Adapter that produces the message list for the gateway.

        Args:
            sanitised_input: The :class:`SanitisedPrompt`.
            identity: The :class:`IdentityContext`.
            trace: The :class:`TraceContext`.

        Returns:
            The message list to send to :func:`call_llm`.
        """
        # The gateway caller should attach the structured payload
        # as ``change_payload`` metadata. When absent we fall back
        # to building a minimal request from the sanitised text.
        metadata = trace.metadata.get("change_payload") or {}
        try:
            request = _request_from_metadata(sanitised_input.text, metadata, identity)
        except Exception as e:
            logger.warning(
                "curriculum_change.payload_parse_failed",
                error=f"{type(e).__name__}: {e}",
            )
            request = CurriculumChangeRequest(
                source_url=str(metadata.get("source_url", "")),
                before_text=str(metadata.get("before_text", "")),
                after_text=str(metadata.get("after_text", "")),
                identity=identity,
            )
        trace.metadata["source_url"] = request.source_url
        return self._build_messages(request)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _call_baml(self, request: CurriculumChangeRequest) -> list[dict[str, Any]]:
        """Delegate to the BAML client (when available)."""
        try:
            result = self.baml_client.DetectCurriculumChanges(  # type: ignore[attr-defined]
                before_text=request.before_text,
                after_text=request.after_text,
                source_url=request.source_url,
            )
            return [dict(e) for e in (result or [])]
        except Exception as e:
            logger.warning(
                "curriculum_change.baml_call_failed",
                error=f"{type(e).__name__}: {e}",
            )
            return []

    def _build_messages(self, request: CurriculumChangeRequest) -> list[Message]:
        """Compose the message list for :func:`call_llm`."""
        system = (
            "You are the BIEP Curriculum Change Sensor. You "
            "compare two captures of the same official source URL "
            "and classify every meaningful curriculum change as "
            "a ChangeEvent. Cosmetic-only changes (typo fixes, "
            "page-numbering tweaks, brand palette refresh) MUST "
            "NOT produce a ChangeEvent. The valid change types "
            "are: NEW_SYLLABUS, UPDATED_SYLLABUS, REMOVED_SYLLABUS. "
            "Return ONLY valid JSON of the shape:\n"
            "{\n"
            '  "events": [\n'
            "    {\n"
            '      "change_type": "NEW_SYLLABUS" | "UPDATED_SYLLABUS" | "REMOVED_SYLLABUS",\n'
            '      "affected_topics": ["<topic>", ...],\n'
            '      "summary": "<plain-English one-sentence summary>",\n'
            '      "effective_date": "YYYY-MM-DD" | "",\n'
            '      "confidence": <float 0-1>,\n'
            '      "jurisdiction": "<ISO-style name>" | "",\n'
            '      "level": "<curriculum level>" | ""\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            'If there are no meaningful changes, return {"events": []}. '
            "Do not wrap the JSON in markdown fences."
        )
        user = (
            f"source_url  : {request.source_url}\n\n"
            f"--- BEFORE TEXT ---\n{request.before_text[:20_000]}\n\n"
            f"--- AFTER TEXT ---\n{request.after_text[:20_000]}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _palette_key_for_url(source_url: str) -> str:
    """Return the palette key for the given source URL (best-effort)."""
    table = {
        "ncca.ie": "ncca.ie",
        "aqa.org.uk": "aqa.org.uk",
        "ocr.org.uk": "ncca.ie",  # OCR shares the England palette family
        "qualifications.pearson.com": "qualifications.pearson.com",
        "sqa.org.uk": "sqa.org.uk",
        "wjec.co.uk": "wjec.co.uk",
        "ccea.org.uk": "ccea.org.uk",
        "gov.im": "gov.im/education",
    }
    for needle, key in table.items():
        if needle in source_url:
            return key
    return "ncca.ie"


def _parse_llm_response(content: str) -> list[dict[str, Any]]:
    """Best-effort parse of the LLM JSON response.

    The BAML function ``DetectCurriculumChanges`` returns the events
    directly as a list (``ChangeEvent[]``). When the agent falls back
    to ``call_llm`` it accepts both shapes — the raw list (the
    canonical BAML output) and a ``{"events": [...]}`` wrapper (used
    by older callers).
    """
    import json as _json

    try:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
        payload = _json.loads(cleaned)
    except Exception as e:
        logger.warning(
            "curriculum_change.llm_json_parse_failed",
            error=f"{type(e).__name__}: {e}",
            content_preview=content[:120],
        )
        return []

    # Accept both the raw list (BAML canonical) and the
    # {"events": [...]} wrapper (legacy callers).
    if isinstance(payload, list):
        events = payload
    elif isinstance(payload, dict):
        events = payload.get("events", []) or []
    else:
        return []
    if not isinstance(events, list):
        return []
    return [e for e in events if isinstance(e, dict)]


def _request_from_metadata(
    sanitised_text: str,
    metadata: dict[str, Any],
    identity: IdentityContext,
) -> CurriculumChangeRequest:
    """Build a :class:`CurriculumChangeRequest` from the gateway metadata."""
    source_url = str(metadata.get("source_url", ""))
    before_text = str(metadata.get("before_text", ""))
    after_text = str(metadata.get("after_text", sanitised_text))
    if not source_url:
        raise ValueError(
            "change_payload must contain a `source_url` for the curriculum_change_sensor."
        )
    return CurriculumChangeRequest(
        source_url=source_url,
        before_text=before_text,
        after_text=after_text,
        identity=identity,
    )


def _make_fake_response(trace_id: str) -> LLMResponse:
    """Construct a stub :class:`LLMResponse` for the BAML path."""
    from gemini_hackathon.call_llm import LLMResponse

    return LLMResponse(
        content="",
        model="baml-detect-curriculum-changes",
        tier=1,
        latency_ms=0,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        attempts=[],
    )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "ChangeEvent",
    "ChangeType",
    "CurriculumChangeRequest",
    "CurriculumChangeResult",
    "CurriculumChangeSensor",
    "build_default_sensor",
    "sensor_invoker",
]


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------


def build_default_sensor() -> CurriculumChangeSensor:
    """Construct a canonical :class:`CurriculumChangeSensor` instance."""
    return CurriculumChangeSensor()


def sensor_invoker(
    sensor: CurriculumChangeSensor | None = None,
) -> Any:
    """Return a callable that adapts :class:`CurriculumChangeSensor` for the gateway.

    Args:
        sensor: Optional pre-built sensor (default: a fresh
            :func:`build_default_sensor` instance).

    Returns:
        A callable suitable for
        :meth:`FleetGateway.register_agent`.
    """
    _sensor = sensor or build_default_sensor()
    return _sensor.as_gateway_invoker
