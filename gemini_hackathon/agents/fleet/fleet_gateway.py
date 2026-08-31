"""gemini_hackathon.agents.fleet.fleet_gateway — single entrypoint + routing.

The 1st Fleet primitive (per the openspec
``2026-08-24-gemini-hackathon-public-v1``). Provides the single
canonical entrypoint for every inbound request to the
gemini_hackathon fleet.

The :class:`FleetGateway` class:

1. Resolves the caller's identity via :class:`FleetIdentity`.
2. Sanitises the input via :class:`ModelArmor`.
3. Routes the request to one of the 4 idea agents based on a
   deterministic keyword map (see :data:`KEYWORD_TO_AGENT`).
4. Opens an observability trace via :class:`Observability`.
5. Returns the agent's response wrapped in an
   :class:`AgentInvocation` envelope.

The keyword map mirrors the Cianfhoghlaim
``agents/fleet/gateway.py`` routing pattern (per the
``wholesale-copy-convention``) with the gemini_hackathon-specific
additions for the 4 idea agents.

Routing precedence:

1. **Curriculum change** keywords (admin-only) — highest precedence.
2. **Marking grader** keywords (teacher-only).
3. **Equivalency** keywords.
4. **Adaptive tutor** keywords (the catch-all default).

If no keyword matches, the gateway falls through to the
``adaptive_tutor`` agent (the canonical default for the BIEP
"find a topic, get an explanation" use case).
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import structlog

from gemini_hackathon.call_llm import LLMResponse, Message, call_llm

from .fleet_identity import FleetIdentity, IdentityContext
from .fleet_model_armor import ModelArmor, SanitisedCompletion, SanitisedPrompt
from .fleet_observability import Observability

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Routing map
# ---------------------------------------------------------------------------


#: The canonical agent roster (the 4 idea agents).
AGENT_NAMES: tuple[str, ...] = (
    "marking_grader_workflow",
    "adaptive_tutor",
    "equivalency_generator",
    "curriculum_change_sensor",
)

AgentName = Literal[
    "marking_grader_workflow",
    "adaptive_tutor",
    "equivalency_generator",
    "curriculum_change_sensor",
]


#: Keyword → agent routing map. The gateway scans the user query
#: for any keyword in the list; the first matching agent wins.
#:
#: Order in the dict = routing precedence (first match wins).
KEYWORD_TO_AGENT: dict[str, AgentName] = {
    # Curriculum change sensor (admin-only) — highest precedence.
    "syllabus change": "curriculum_change_sensor",
    "syllabus update": "curriculum_change_sensor",
    "curriculum drift": "curriculum_change_sensor",
    "change detection": "curriculum_change_sensor",
    "diff syllabus": "curriculum_change_sensor",
    "new syllabus": "curriculum_change_sensor",
    # Marking grader workflow (teacher-only).
    "mark this": "marking_grader_workflow",
    "grade this": "marking_grader_workflow",
    "mark scheme": "marking_grader_workflow",
    "marking scheme": "marking_grader_workflow",
    "compare to marking": "marking_grader_workflow",
    "rubric": "marking_grader_workflow",
    "grade my": "marking_grader_workflow",
    # Equivalency generator.
    "equivalent in": "equivalency_generator",
    "equivalent topic": "equivalency_generator",
    "what's the equivalent": "equivalency_generator",
    "what is the equivalent": "equivalency_generator",
    "across jurisdictions": "equivalency_generator",
    "aqa equivalent": "equivalency_generator",
    "sqa equivalent": "equivalency_generator",
    "wjec equivalent": "equivalency_generator",
    "ccea equivalent": "equivalency_generator",
    "pearson equivalent": "equivalency_generator",
    "ocr equivalent": "equivalency_generator",
    "isle of man equivalent": "equivalency_generator",
    # Adaptive tutor — catch-all (see `_route`).
}


#: Permission required per agent. The gateway checks
#: ``ctx.has_permission(...)`` before invoking the agent.
AGENT_PERMISSIONS: dict[str, str] = {
    "marking_grader_workflow": "run_marking_grader",
    "adaptive_tutor": "view_personalisation",
    "equivalency_generator": "read_equivalencies",
    "curriculum_change_sensor": "trigger_change_sensor",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentInvocation:
    """The input envelope for a gateway invocation.

    Attributes:
        user_message: The user's natural-language message.
        bearer_token: Optional ``Authorization: Bearer <token>``.
        session_cookie: Optional session cookie.
        metadata: Free-form per-invocation metadata.
        force_agent: Optional agent name override — when set, the
            keyword routing is bypassed and the named agent is
            invoked directly (requires the caller to have
            permission for that agent).
    """

    user_message: str
    bearer_token: str | None = None
    session_cookie: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    force_agent: str | None = None


@dataclass(frozen=True)
class AgentResponse:
    """The output envelope from a gateway invocation.

    Attributes:
        agent: The resolved agent name.
        content: The agent's response text.
        tier: The LLM tier that served the request (1, 2, or 3).
        model: The LLM model that served the request.
        latency_ms: The total wall-clock latency.
        identity: The resolved :class:`IdentityContext`.
        sanitised_input: The :class:`SanitisedPrompt` summary.
        sanitised_output: The :class:`SanitisedCompletion` summary.
        llm_response: The full :class:`LLMResponse` (for callers
            that need token counts, cost, or per-attempt history).
        trace_id: The observability trace ID.
    """

    agent: str
    content: str
    tier: int
    model: str
    latency_ms: int
    identity: IdentityContext
    sanitised_input: SanitisedPrompt
    sanitised_output: SanitisedCompletion
    llm_response: LLMResponse
    trace_id: str


# ---------------------------------------------------------------------------
# The FleetGateway class
# ---------------------------------------------------------------------------


class FleetGateway:
    """The single entrypoint for the gemini_hackathon fleet.

    Constructed once at process start with the 3 fleet primitives
    (identity, armor, observability) wired in. The :meth:`invoke`
    method handles the full lifecycle:

    1. Resolve identity.
    2. Sanitise input.
    3. Route to the right agent.
    4. Check permission for the resolved agent.
    5. Open an observability trace.
    6. Invoke the agent (a callable that takes the sanitised
       prompt + the identity + the trace context and returns
       a list of :class:`gemini_hackathon.call_llm.Message`).
    7. Call the LLM through :func:`call_llm`.
    8. Sanitise the output.
    9. Return the :class:`AgentResponse`.
    """

    def __init__(
        self,
        *,
        identity: FleetIdentity | None = None,
        armor: ModelArmor | None = None,
        observability: Observability | None = None,
        agent_invokers: dict[str, Callable[..., list[Message]]] | None = None,
    ) -> None:
        """Initialise the gateway.

        Args:
            identity: The :class:`FleetIdentity` (default: a fresh
                instance with anonymous fallback enabled).
            armor: The :class:`ModelArmor` (default: a fresh
                instance with default policies).
            observability: The :class:`Observability` (default: a
                fresh instance — optional Langfuse / MLflow).
            agent_invokers: A dict mapping agent name → invoker
                callable. Each invoker receives the sanitised
                ``SanitisedPrompt`` + the :class:`IdentityContext`
                + the :class:`TraceContext` and returns the
                message list to send to the LLM.
        """
        self.identity = identity or FleetIdentity()
        self.armor = armor or ModelArmor()
        self.observability = observability or Observability()
        self.agent_invokers: dict[str, Callable[..., list[Message]]] = dict(agent_invokers or {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def invoke(self, invocation: AgentInvocation) -> AgentResponse:
        """Run the full request lifecycle.

        Args:
            invocation: The :class:`AgentInvocation` envelope.

        Returns:
            The :class:`AgentResponse` envelope.

        Raises:
            AuthenticationError: If identity resolution fails.
            AuthorisationError: If the resolved identity lacks
                permission for the resolved agent.
            ValueError: If the resolved agent has no registered
                invoker.
        """
        start = time.monotonic()

        # 1. Resolve identity.
        ctx = self.identity.resolve(
            bearer_token=invocation.bearer_token,
            session_cookie=invocation.session_cookie,
            user_id_hint=invocation.metadata.get("user_id_hint"),
        )

        # 2. Sanitise input.
        sanitised_input = self.armor.sanitise_input(invocation.user_message)

        # 3. Route.
        agent = self._route(sanitised_input.text, force=invocation.force_agent)

        # 4. Permission check.
        perm = AGENT_PERMISSIONS.get(agent)
        if perm:
            self.identity.require_permission(ctx, perm)

        # 5. Open observability trace.
        with self.observability.trace(
            agent=agent,
            user_id=ctx.user_id,
            session_id=ctx.session_id if hasattr(ctx, "session_id") else "",
            metadata={
                "invocation.metadata": dict(invocation.metadata),
                "identity.role": ctx.role,
                "identity.jurisdiction": ctx.jurisdiction,
                "identity.level": ctx.level,
                "identity.source_palette_key": ctx.source_palette_key,
            },
        ) as trace:
            # 6. Invoke the agent → messages.
            invoker = self.agent_invokers.get(agent)
            if invoker is None:
                raise ValueError(
                    f"No invoker registered for agent '{agent}'. "
                    f"Registered agents: {list(self.agent_invokers.keys())}"
                )
            messages = invoker(
                sanitised_input=sanitised_input,
                identity=ctx,
                trace=trace,
            )

            # 7. Call the LLM.
            llm_response = call_llm(
                messages=messages,
                metadata={
                    "trace_id": trace.trace_id,
                    "agent": agent,
                    "user_id": ctx.user_id,
                },
            )

            # 8. Sanitise output.
            sanitised_output = self.armor.sanitise_output(llm_response.content)

            # Record invocation on observability.
            self.observability.record_invocation(trace, llm_response)

        total_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "gateway.invocation_completed",
            trace_id=trace.trace_id,
            agent=agent,
            user_id=ctx.user_id,
            tier=llm_response.tier,
            model=llm_response.model,
            total_latency_ms=total_ms,
        )
        return AgentResponse(
            agent=agent,
            content=sanitised_output.text,
            tier=llm_response.tier,
            model=llm_response.model,
            latency_ms=total_ms,
            identity=ctx,
            sanitised_input=sanitised_input,
            sanitised_output=sanitised_output,
            llm_response=llm_response,
            trace_id=trace.trace_id,
        )

    def register_agent(
        self,
        agent_name: str,
        invoker: Callable[..., list[Message]],
    ) -> None:
        """Register an agent invoker.

        Args:
            agent_name: The agent's canonical name (must appear in
                :data:`AGENT_NAMES`).
            invoker: The callable that produces the message list.
        """
        if agent_name not in AGENT_NAMES:
            raise ValueError(f"Unknown agent '{agent_name}'. Must be one of {AGENT_NAMES}.")
        self.agent_invokers[agent_name] = invoker

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _route(self, query: str, *, force: str | None = None) -> str:
        """Route a sanitised query to the right agent name.

        Args:
            query: The (sanitised) user query.
            force: Optional explicit agent override.

        Returns:
            The resolved agent name (one of :data:`AGENT_NAMES`).
        """
        if force:
            if force not in AGENT_NAMES:
                raise ValueError(f"Forced agent '{force}' is not in AGENT_NAMES {AGENT_NAMES}.")
            return force

        lowered = query.lower()
        for keyword, agent in KEYWORD_TO_AGENT.items():
            if keyword in lowered:
                logger.debug(
                    "gateway.keyword_routed",
                    keyword=keyword,
                    agent=agent,
                )
                return agent

        # No keyword matched → default to adaptive_tutor.
        logger.debug("gateway.default_route", agent="adaptive_tutor")
        return "adaptive_tutor"


# ---------------------------------------------------------------------------
# Helpers (for testing + introspection)
# ---------------------------------------------------------------------------


def list_known_keywords() -> list[str]:
    """Return the flattened list of routing keywords (sorted)."""
    return sorted(KEYWORD_TO_AGENT.keys())


def agent_for_query(query: str) -> str | None:
    """Return the agent that would be selected for ``query``.

    Args:
        query: The raw user query.

    Returns:
        The agent name (or ``None`` if no keyword matches AND the
        caller has overridden the default — the canonical default
        is ``"adaptive_tutor"``).
    """
    lowered = query.lower()
    for keyword, agent in KEYWORD_TO_AGENT.items():
        if keyword in lowered:
            return agent
    return None  # caller should fall back to adaptive_tutor


def is_administrative_query(query: str) -> bool:
    """Return whether ``query`` matches any curriculum-change keyword.

    Useful for upstream layers that want to require elevated
    permissions before the request reaches the gateway.
    """
    lowered = query.lower()
    return any(
        re.search(rf"\b{re.escape(kw)}\b", lowered)
        for kw in KEYWORD_TO_AGENT
        if KEYWORD_TO_AGENT[kw] == "curriculum_change_sensor"
    )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "AGENT_NAMES",
    "AGENT_PERMISSIONS",
    "KEYWORD_TO_AGENT",
    "AgentInvocation",
    "AgentName",
    "AgentResponse",
    "FleetGateway",
    "agent_for_query",
    "is_administrative_query",
    "list_known_keywords",
]
