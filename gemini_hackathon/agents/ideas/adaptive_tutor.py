"""gemini_hackathon.agents.ideas.adaptive_tutor — personalised tutoring agent.

The Adaptive Tutor is one of the 4 idea agents in the
gemini_hackathon fleet (per the openspec change
``2026-08-24-gemini-hackathon-public-v1``). It provides
personalised tutoring aligned to:

* The **active source palette** (``identity.source_palette_key``,
  e.g. ``"ncca.ie"`` or ``"sqa.org.uk"``) — drives the visual
  identity injected on the frontend.
* The **jurisdiction** (``identity.jurisdiction``, e.g. ``"Ireland"``
  / ``"Scotland"`` / ``"Wales"``) — anchors the tutor's
  curriculum source.
* The **level** (``identity.level``, e.g. ``"LC"`` / ``"A-Level"``
  / ``"GCSE"``) — selects the right syllabus.

The tutor uses the canonical ``call_llm()`` entrypoint (so every
invocation respects the 3-tier model policy) and the
``fleet_mcp_curriculum.lookup_topic`` tool to ground its answers
in the live syllabus PDFs.

Wholesale port of the Cianfhoghlaim
``agents/adk/celtic_tutor_agent.py`` (per the
``wholesale-copy-convention``) — adapted from the Celtic-language
tutor to the BIEP jurisdiction + level tutor:

1. Replaced the Irish / Scottish Gaelic / Welsh language features
   with British-Ireland cross-jurisdiction curriculum features.
2. Replaced the ``google.adk.agents.LlmAgent`` factory with a
   plain Python ``AdaptiveTutor`` class that uses
   :func:`gemini_hackathon.call_llm` directly.
3. Added the ``fleet_mcp_curriculum`` lookup as the canonical
   tool (instead of the historical
   ``tuatha_curriculum_search`` backend).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from gemini_hackathon.call_llm import LLMResponse, Message, call_llm
from gemini_hackathon.theming import Palette, load_palette

from ..fleet.fleet_identity import IdentityContext
from ..fleet.fleet_mcp_curriculum import (
    MCPCurriculumServer,
    TopicLookup,
)
from ..fleet.fleet_observability import Observability, TraceContext

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TutorRequest:
    """The input envelope for an adaptive-tutor invocation.

    Attributes:
        question: The pupil's natural-language question.
        topic_hint: An optional topic hint (skips the question
            classification step when supplied).
        identity: The resolved :class:`IdentityContext`.
    """

    question: str
    topic_hint: str = ""
    identity: IdentityContext | None = None


@dataclass(frozen=True)
class TutorResponse:
    """The output envelope from the adaptive tutor.

    Attributes:
        answer: The tutor's response text.
        topic: The resolved topic name (from the MCP lookup).
        topic_lookup: The :class:`TopicLookup` that grounded the
            answer (or ``None`` if the lookup was skipped).
        palette: The active :class:`Palette` (or ``None`` if the
            source key did not resolve).
        llm_response: The underlying :class:`LLMResponse`.
        trace_id: The observability trace ID.
    """

    answer: str
    topic: str
    topic_lookup: TopicLookup | None
    palette: Palette | None
    llm_response: LLMResponse
    trace_id: str


# ---------------------------------------------------------------------------
# The AdaptiveTutor agent
# ---------------------------------------------------------------------------


class AdaptiveTutor:
    """The Adaptive Tutor idea agent.

    Constructed once at process start and registered with the
    :class:`FleetGateway`. The :meth:`invoke` method is the
    canonical entrypoint for the gateway's keyword router.
    """

    def __init__(
        self,
        *,
        mcp_server: MCPCurriculumServer | None = None,
        observability: Observability | None = None,
    ) -> None:
        """Initialise the tutor.

        Args:
            mcp_server: The :class:`MCPCurriculumServer` (default:
                a fresh instance).
            observability: The :class:`Observability` (default: a
                fresh instance).
        """
        self.mcp_server = mcp_server or MCPCurriculumServer()
        self.observability = observability or Observability()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(
        self,
        request: TutorRequest,
        *,
        trace: TraceContext | None = None,
    ) -> TutorResponse:
        """Run the tutor lifecycle for one pupil question.

        Args:
            request: The :class:`TutorRequest` envelope.
            trace: Optional pre-existing observability trace
                (default: the tutor opens its own).

        Returns:
            The :class:`TutorResponse` envelope.
        """
        identity = request.identity or IdentityContext()
        topic_hint = (request.topic_hint or "").strip()
        question = request.question.strip()

        # Resolve topic + grounding context.
        if topic_hint:
            topic = topic_hint
            lookup = self.mcp_server.lookup_topic(
                topic=topic,
                jurisdiction=identity.jurisdiction,
                level=identity.level,
            )
        else:
            topic = self._classify_topic(question, identity)
            lookup = self.mcp_server.lookup_topic(
                topic=topic,
                jurisdiction=identity.jurisdiction,
                level=identity.level,
            )

        palette = load_palette(identity.source_palette_key)

        # Open the trace.
        if trace is None:
            cm = self.observability.trace(
                agent="adaptive_tutor",
                user_id=identity.user_id,
                metadata={
                    "topic": topic,
                    "jurisdiction": identity.jurisdiction,
                    "level": identity.level,
                    "source_palette_key": identity.source_palette_key,
                },
            )
            trace = cm.__enter__()  # capture the yielded TraceContext
            close_cm = cm
        else:
            close_cm = None

        try:
            messages = self._build_messages(
                question=question,
                topic=topic,
                lookup=lookup,
                palette=palette,
                identity=identity,
            )
            llm_response = call_llm(
                messages=messages,
                metadata={
                    "trace_id": trace.trace_id,
                    "agent": "adaptive_tutor",
                    "user_id": identity.user_id,
                },
            )
            self.observability.record_invocation(trace, llm_response)
            return TutorResponse(
                answer=llm_response.content,
                topic=topic,
                topic_lookup=lookup,
                palette=palette,
                llm_response=llm_response,
                trace_id=trace.trace_id,
            )
        finally:
            if close_cm is not None:
                close_cm.__exit__(None, None, None)

    # Convenience: the canonical gateway-invoker signature.
    def as_gateway_invoker(
        self,
        *,
        sanitised_input: Any,
        identity: IdentityContext,
        trace: TraceContext,
    ) -> list[Message]:
        """Adapter that produces the message list for the gateway.

        Args:
            sanitised_input: A :class:`SanitisedPrompt` (the
                ``text`` attribute holds the question).
            identity: The :class:`IdentityContext` resolved by
                :class:`FleetIdentity`.
            trace: The :class:`TraceContext` opened by
                :class:`Observability`.

        Returns:
            The message list to send to :func:`call_llm`.
        """
        # Resolve the topic + palette in advance (so the gateway
        # can record the lookup on the trace).
        question = sanitised_input.text
        topic = self._classify_topic(question, identity)
        lookup = self.mcp_server.lookup_topic(
            topic=topic,
            jurisdiction=identity.jurisdiction,
            level=identity.level,
        )
        palette = load_palette(identity.source_palette_key)

        # Cache the lookup on the trace metadata for later inspection.
        trace.metadata["resolved_topic"] = topic
        trace.metadata["source_palette_key"] = identity.source_palette_key

        return self._build_messages(
            question=question,
            topic=topic,
            lookup=lookup,
            palette=palette,
            identity=identity,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _classify_topic(self, question: str, identity: IdentityContext) -> str:
        """Cheap topic classifier (keyword + jurisdiction-aware).

        In production this would delegate to the BAML
        ``ExtractTopic`` function. For the demo / test path, we
        pick the longest question word as the topic stand-in.

        Args:
            question: The pupil's question.
            identity: The :class:`IdentityContext` (unused for
                now — reserved for jurisdiction-specific stop-
                word lists).

        Returns:
            The candidate topic name.
        """
        stop = {
            "what",
            "how",
            "why",
            "when",
            "where",
            "is",
            "are",
            "the",
            "a",
            "an",
            "of",
            "to",
            "in",
            "for",
            "do",
            "does",
            "can",
            "could",
            "should",
            "would",
            "tell",
            "me",
            "about",
            "explain",
            "please",
            "help",
            "i",
            "with",
            "this",
            "that",
            "it",
        }
        words = [
            w.strip("?,.")
            for w in question.split()
            if len(w.strip("?,.")) > 3 and w.lower() not in stop
        ]
        if not words:
            return identity.jurisdiction
        return max(words, key=len).capitalize()

    def _build_messages(
        self,
        *,
        question: str,
        topic: str,
        lookup: TopicLookup,
        palette: Palette | None,
        identity: IdentityContext,
    ) -> list[Message]:
        """Compose the message list for :func:`call_llm`."""
        palette_block = self._palette_block(palette)
        outcomes_block = "\n".join(f"- {lo}" for lo in lookup.learning_outcomes)

        system = (
            "You are an Adaptive Tutor for the British & Irish Education "
            "Pipeline (BIEP). You teach pupils preparing for "
            f"{identity.level} in {identity.jurisdiction}. "
            "You ground every answer in the active jurisdiction's "
            "official syllabus. You use the active source's brand voice "
            "(no slang, no US English). You cite the learning outcomes "
            "the pupil is working towards. You never invent topics or "
            "outcomes that are not in the canonical syllabus.\n\n"
            f"ACTIVE SOURCE PALETTE\n{palette_block}\n\n"
            f"CURRENT TOPIC: {topic}\n\n"
            f"CANONICAL LEARNING OUTCOMES\n{outcomes_block or '(none loaded)'}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]

    def _palette_block(self, palette: Palette | None) -> str:
        """Render the palette as a compact text block for the system prompt."""
        if palette is None:
            return "(no active palette)"
        return (
            f"- source_key      : {palette.source_key}\n"
            f"- source_name     : {palette.source_name}\n"
            f"- jurisdiction    : {palette.jurisdiction}\n"
            f"- level           : {palette.level}\n"
            f"- primary         : {palette.primary}\n"
            f"- secondary       : {palette.secondary}\n"
            f"- accent          : {palette.accent}\n"
            f"- heading_font    : {palette.heading_font}\n"
            f"- body_font       : {palette.body_font}\n"
            f"- flag            : {palette.flag or '(none)'}"
        )


# ---------------------------------------------------------------------------
# Public exports
# ------------------------------------------------------------------------__

__all__ = [
    "AdaptiveTutor",
    "TutorRequest",
    "TutorResponse",
]


# ---------------------------------------------------------------------------
# Convenience: build the tutor instance + the gateway invoker.
# ---------------------------------------------------------------------------


def build_default_tutor() -> AdaptiveTutor:
    """Construct a canonical :class:`AdaptiveTutor` instance."""
    return AdaptiveTutor()


def tutor_invoker(
    tutor: AdaptiveTutor | None = None,
) -> Any:
    """Return a callable that adapts :class:`AdaptiveTutor` for the gateway.

    Args:
        tutor: Optional pre-built tutor (default: a fresh
            :func:`build_default_tutor` instance).

    Returns:
        A callable suitable for
        :meth:`FleetGateway.register_agent`.
    """
    _tutor = tutor or build_default_tutor()
    return _tutor.as_gateway_invoker


# Convenience: add the invokers + JURISDICTION_SOURCES to the public API.
__all__ += ["build_default_tutor", "tutor_invoker"]
