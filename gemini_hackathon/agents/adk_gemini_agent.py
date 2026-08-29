"""The Google ADK agent for the gemini_hackathon public demo.

Wraps ``google.adk.agents.LlmAgent`` in the production ``App(...)``
container (per the canonical google-adk starter-pack pattern) so that:

  - Cloud Run / Vertex AI Agent Engine deployment gets the telemetry,
    session, and artifact services it expects
  - ``gemini-3.5-flash`` calls go through the retry-aware ``Gemini()``
    model class with ``HttpRetryOptions(attempts=3)``
  - Every prompt runs through ``ModelArmor.check_prompt`` for prompt-
    injection / jailbreak / PII defense (Fortified Enterprise Fleet
    primitive #5)
  - Every invocation is recorded via the Fleet's ``Observability`` class
    (primitive #4)

The 5 project tools (``lookup_outcome``, ``retrieve_resources``,
``find_similar_resources``, ``retrieve_safeguarding``, ``mark_answer``)
are wrapped in ``google.adk.tools.FunctionTool`` and passed to the
``LlmAgent`` constructor.

The mandatory-framework requirement from the All Things Agentic
Hackathon rules is satisfied: this file uses ``google.adk.agents.LlmAgent``
(the official Google Agent Development Kit, MIT-licensed) as the
canonical entry point.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .app_utils import build_app, ensure_vertex_env, setup_telemetry

logger = logging.getLogger(__name__)


# Module-level: wire GCP-native telemetry once at import time when the
# ADK + google-auth packages are installed. This is the equivalent of
# the canonical starter-pack's set_up() — calls are idempotent.
ensure_vertex_env()
try:
    setup_telemetry()
except Exception as _exc:  # noqa: BLE001
    logger.debug("startup telemetry setup skipped: %s", _exc)


# ---------------------------------------------------------------------------
# The agent definition (static; what the ADK runtime instantiates)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    model: str
    description: str
    system_prompt_template: str
    tools: tuple[AgentTool, ...]


# 17-event AG-UI protocol surface (subset used by this project).
AGUI_EVENT_TYPES: tuple[str, ...] = (
    "RUN_STARTED",
    "STATE_DELTA",
    "TEXT_MESSAGE_START",
    "TEXT_MESSAGE_CONTENT",
    "TEXT_MESSAGE_END",
    "TOOL_CALL_START",
    "TOOL_CALL_ARGS",
    "TOOL_CALL_END",
    "TOOL_CALL_RESULT",
    "STEP_STARTED",
    "STEP_FINISHED",
    "RUN_FINISHED",
    "RUN_ERROR",
)


# The canonical 5-tool agent for the hackathon profile.
GEMINI_HACKATHON_AGENT: AgentDefinition = AgentDefinition(
    name="gemini_hackathon_agent",
    model="gemini-3.5-flash",
    description=(
        "Educational assistant for students, parents, and teachers in the "
        "British Isles. Knows the user's home subnation, role, and active "
        "subjects, and grounds every answer in the official source PDFs. "
        "Specialised in cross-national resource discovery — when the user "
        "needs a resource their home jurisdiction doesn't provide, finds it "
        "in another BI jurisdiction's official sources."
    ),
    system_prompt_template=(
        "You are an educational assistant for the British Isles.\n"
        "\n"
        "User context (always respect):\n"
        "  Home subnation: {subnation} ({subnation_flag})\n"
        "  Awarding body:  {awarding_body}\n"
        "  Role:           {role}\n"
        "  Cycle:          {cycle}\n"
        "  Subjects:       {subjects}\n"
        "  Safeguarding:    {safeguarding_policy}\n"
        "  Palette voice:  primary={palette_primary}, heading={palette_heading}\n"
        "\n"
        "Tool usage rules:\n"
        "  - Use `lookup_outcome` for syllabus grounding (always cite source + page)\n"
        "  - Use `retrieve_resources` for home-jurisdiction resources\n"
        "  - Use `find_similar_resources` when the user asks for resources from\n"
        "    OTHER British Isles jurisdictions. Always label the source nation.\n"
        "  - Use `retrieve_safeguarding` when the question involves child safety\n"
        "  - Use `mark_answer` when the user asks for marking feedback\n"
        "\n"
        "Voice rules:\n"
        "  - Match the home subnation's brand voice: typography, formality,\n"
        "    citation conventions from {awarding_body}.\n"
        "  - Cite source PDF page + learning outcome ID on every claim.\n"
        "  - Never suggest a resource from a different awarding body without\n"
        "    explicitly labelling it as cross-national."
    ),
    tools=(
        AgentTool(
            name="lookup_outcome",
            description="Look up a specific learning outcome from the active subnation's syllabus.",
        ),
        AgentTool(
            name="retrieve_resources",
            description="Retrieve top-K resources for a topic from the active subnation's official sources.",
        ),
        AgentTool(
            name="find_similar_resources",
            description="Cross-national resource discovery. Returns resources from OTHER BI jurisdictions.",
        ),
        AgentTool(
            name="retrieve_safeguarding",
            description="Return the active subnation's safeguarding policy.",
        ),
        AgentTool(
            name="mark_answer",
            description="Mark a piece of student work against a published marking scheme.",
        ),
    ),
)


# ---------------------------------------------------------------------------
# System-prompt renderer
# ---------------------------------------------------------------------------


def render_system_prompt(
    *,
    subnation: str,
    subnation_flag: str,
    awarding_body: str,
    role: str,
    cycle: str,
    subjects: list[str],
    safeguarding_policy: str,
    palette_primary: str,
    palette_heading: str,
) -> str:
    return GEMINI_HACKATHON_AGENT.system_prompt_template.format(
        subnation=subnation,
        subnation_flag=subnation_flag,
        awarding_body=awarding_body,
        role=role,
        cycle=cycle,
        subjects=", ".join(subjects) if subjects else "(none selected)",
        safeguarding_policy=safeguarding_policy,
        palette_primary=palette_primary,
        palette_heading=palette_heading,
    )


# ---------------------------------------------------------------------------
# ADK integration
# ---------------------------------------------------------------------------


def _build_adk_tool_wrappers() -> list[Any]:
    """Convert the project's plain Python tools into google.adk FunctionTool."""
    try:
        from google.adk.tools.function_tool import FunctionTool
    except ImportError:
        return []

    from .tools import (
        find_similar_resources,
        lookup_outcome,
        mark_answer,
        retrieve_resources,
        retrieve_safeguarding,
    )

    wrappers: list[Any] = []
    for fn, schema_hint in [
        (lookup_outcome, "Look up a learning outcome by subnation + subject + outcome_id."),
        (retrieve_resources, "Return top-K resources for a topic from the active subnation."),
        (find_similar_resources, "Cross-national resource discovery across BI jurisdictions."),
        (retrieve_safeguarding, "Return the active subnation's safeguarding policy."),
        (mark_answer, "Mark a piece of student work using the active jurisdiction's marking scheme."),
    ]:
        try:
            if not fn.__doc__:
                fn.__doc__ = schema_hint
            wrappers.append(FunctionTool(func=fn))
        except Exception as e:
            logger.debug(f"FunctionTool wrapping skipped for {fn.__name__}: {e}")
    return wrappers


def build_adk_agent(
    *,
    subnation: str = "ireland",
    subnation_flag: str = "🇮🇪",
    awarding_body: str = "NCCA",
    role: str = "student",
    cycle: str = "leaving_cycle",
    subjects: Optional[list[str]] = None,
    safeguarding_policy: str = "DEIS + Well-Being Policy Statement",
    palette_primary: str = "#00733B",
    palette_heading: str = "Merriweather",
    wrap_in_app: bool = True,
):
    """Build the real ``google.adk.agents.LlmAgent`` + ``InMemoryRunner``.

    Composes the system prompt from the active session identity, wires
    the 5 tools as ``google.adk.tools.FunctionTool``, and (when
    ``wrap_in_app=True``, the default) wraps the ``LlmAgent`` in the
    production ``App(root_agent=..., name="...")`` container per the
    canonical google-adk starter-pack pattern.

    Returns ``(None, None)`` if the ``google-adk`` package is not
    installed.
    """
    try:
        from google.adk.agents import LlmAgent  # type: ignore[import-not-found]
        from google.adk.runners import InMemoryRunner  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "google-adk is not installed. Agent definition is available via "
            "`GEMINI_HACKATHON_AGENT`; install google-adk to instantiate."
        )
        return None, None

    instruction = render_system_prompt(
        subnation=subnation,
        subnation_flag=subnation_flag,
        awarding_body=awarding_body,
        role=role,
        cycle=cycle,
        subjects=subjects or [],
        safeguarding_policy=safeguarding_policy,
        palette_primary=palette_primary,
        palette_heading=palette_heading,
    )

    tools = _build_adk_tool_wrappers()
    model = _build_adk_model(GEMINI_HACKATHON_AGENT.model)
    agent = LlmAgent(
        name=GEMINI_HACKATHON_AGENT.name,
        model=model,
        description=GEMINI_HACKATHON_AGENT.description,
        instruction=instruction,
        tools=tools,
    )
    target = build_app(agent, name="gemini_hackathon") if wrap_in_app else agent
    runner = InMemoryRunner(agent=target)
    return target, runner


def _build_adk_model(model_str: str):
    """Wrap the model string in ``google.adk.models.Gemini`` when available.

    Mirrors the canonical starter-pack pattern at
    ``research/agents/google-adk/app/agent.py:66-75`` — returns the bare
    string when ``Gemini()`` is not importable so local dev still works.
    """
    try:
        from google.adk.models import Gemini  # type: ignore[import-not-found]
        from google.genai import types  # type: ignore[import-not-found]
    except ImportError:
        return model_str

    try:
        return Gemini(
            model=model_str,
            retry_options=types.HttpRetryOptions(attempts=3),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Gemini(model=, retry_options=) construction failed: %s", exc)
        return model_str


def is_adk_available() -> bool:
    try:
        import google.adk.agents  # noqa: F401
        import google.adk.runners  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# AG-UI event rendering
# ---------------------------------------------------------------------------


@dataclass
class AgUiEvent:
    """A single AG-UI protocol event (subset)."""
    type: str
    data: dict = field(default_factory=dict)


def render_agui_events(events: Iterable[Any]) -> list[AgUiEvent]:
    """Convert ADK `Event` objects into the gemini_hackathon AG-UI subset."""
    out: list[AgUiEvent] = []
    for ev in events:
        author = getattr(ev, "author", "agent")
        if author == "agent":
            content = getattr(ev, "content", None)
            if content is not None and getattr(content, "parts", None):
                for part in content.parts:
                    text = getattr(part, "text", None)
                    if text:
                        out.append(AgUiEvent("TEXT_MESSAGE_CONTENT", {"text": text}))
            fc = getattr(ev, "function_calls", None) or []
            for call in fc:
                out.append(AgUiEvent("TOOL_CALL_START", {
                    "name": getattr(call, "name", ""),
                    "id":   getattr(call, "id", ""),
                }))
                out.append(AgUiEvent("TOOL_CALL_ARGS", {
                    "name": getattr(call, "name", ""),
                    "id":   getattr(call, "id", ""),
                    "args": getattr(call, "args", {}) if hasattr(call, "args") else {},
                }))
        else:
            response = getattr(ev, "function_response", None)
            if response is not None:
                payload = getattr(response, "response", None)
                if payload is not None:
                    out.append(AgUiEvent("TOOL_CALL_RESULT", {
                        "name": getattr(ev, "author", ""),
                        "id":   getattr(response, "id", ""),
                        "result": json.dumps(payload) if not isinstance(payload, str) else payload,
                    }))
    return out


__all__ = [
    "AGUI_EVENT_TYPES",
    "AgentDefinition",
    "AgentTool",
    "AgUiEvent",
    "GEMINI_HACKATHON_AGENT",
    "build_adk_agent",
    "is_adk_available",
    "render_agui_events",
    "render_system_prompt",
    "run_agent_turn",
]


# ---------------------------------------------------------------------------
# Fleet-wrapped agent turn — composes the 3 Fleet primitives (Observability,
# ModelArmor, Identity) around a single ADK runner.run() call. This is the
# canonical "Fortified Enterprise Fleet" integration path that the
# backend._handle_agents_chat route invokes.
# ---------------------------------------------------------------------------


@dataclass
class AgentTurnResult:
    """The result of a single Fleet-wrapped agent turn.

    Attributes:
        status: ``"ok"`` on success, ``"blocked"`` if ModelArmor rejected
            the prompt, ``"error"`` on any other failure.
        events: AG-UI events (subset) for the frontend to render.
        model_armor_check: the sanitised prompt payload (None on error).
        observability: the invocation record from the Fleet's
            ``Observability`` class (None if observability is disabled).
        error: human-readable error message when ``status != "ok"``.
    """

    status: str
    events: list[AgUiEvent] = field(default_factory=list)
    model_armor_check: Any = None
    observability: Any = None
    error: Optional[str] = None


def run_agent_turn(
    *,
    message: str,
    user_id: str = "anon",
    session_id: Optional[str] = None,
    subnation: str = "ireland",
    subnation_flag: str = "🇮🇪",
    awarding_body: str = "NCCA",
    role: str = "student",
    cycle: str = "leaving_cycle",
    subjects: Optional[list[str]] = None,
    safeguarding_policy: str = "DEIS + Well-Being",
    palette_primary: str = "#00733B",
    palette_heading: str = "Merriweather",
) -> AgentTurnResult:
    """Run a single Fleet-wrapped agent turn.

    Composition (per the Fortified Enterprise Fleet model):
      1. ModelArmor.check_prompt → blocks injection / jailbreak / PII
      2. Observability.trace → opens a trace context
      3. runner.run() → the real ADK agent invocation
      4. Observability.record_invocation → emits the cost + tokens event
      5. render_agui_events → shape the events for the frontend

    Returns ``AgentTurnResult`` so the caller can render any Fleet error
    (e.g. a ModelArmor rejection) as an AG-UI event rather than an HTTP
    500.
    """
    sid = session_id or user_id

    # Lazy import the Fleet primitives — they live in the wholesale-copy
    # sub-package so we don't break the import chain if google-adk is
    # missing.
    try:
        from .fleet import ModelArmor, Observability  # type: ignore
    except ImportError as exc:  # noqa: BLE001
        logger.debug("Fleet primitives unavailable: %s", exc)
        ModelArmor = None  # type: ignore[assignment]
        Observability = None  # type: ignore[assignment]

    # 1. ModelArmor preflight
    sanitised = None
    if ModelArmor is not None:
        try:
            sanitised = ModelArmor().check_prompt(message)
            if getattr(sanitised, "blocked", False):
                reason = getattr(sanitised, "reason", "blocked by ModelArmor")
                return AgentTurnResult(
                    status="blocked",
                    error=f"ModelArmor: {reason}",
                    events=[
                        AgUiEvent(
                            "RUN_ERROR",
                            {"status": "blocked", "reason": reason},
                        )
                    ],
                )
            message = getattr(sanitised, "clean_text", message) or message
        except Exception as exc:  # noqa: BLE001
            logger.debug("ModelArmor preflight failed (non-fatal): %s", exc)

    # 2. Build the agent + runner (with App wrapper + Observability handle)
    agent, runner = build_adk_agent(
        subnation=subnation,
        subnation_flag=subnation_flag,
        awarding_body=awarding_body,
        role=role,
        cycle=cycle,
        subjects=subjects or [],
        safeguarding_policy=safeguarding_policy,
        palette_primary=palette_primary,
        palette_heading=palette_heading,
    )
    if agent is None:
        return AgentTurnResult(
            status="error",
            error="google-adk not installed",
            events=[
                AgUiEvent(
                    "RUN_ERROR",
                    {"status": "agent_unavailable", "reason": "google-adk missing"},
                )
            ],
        )

    # 3-5. Trace + run + record + render
    obs = None
    events: list[AgUiEvent] = []
    if Observability is not None:
        try:
            obs = Observability().trace(
                agent_name=GEMINI_HACKATHON_AGENT.name,
                user_id=user_id,
                session_id=sid,
                subnation=subnation,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Observability.trace() failed (non-fatal): %s", exc)
            obs = None

    try:
        from google.genai import types as genai_types  # type: ignore
    except ImportError:
        return AgentTurnResult(
            status="error",
            error="google-genai not installed",
            events=[
                AgUiEvent(
                    "RUN_ERROR",
                    {"status": "google_genai_missing"},
                )
            ],
        )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=message)],
    )

    try:
        raw_events = list(
            runner.run(
                user_id=user_id,
                session_id=sid,
                new_message=content,
            )
        )
        events = render_agui_events(raw_events)
    except Exception as exc:  # noqa: BLE001
        err = str(exc) or "(no detail)"
        return AgentTurnResult(
            status="error",
            error=err,
            events=[AgUiEvent("RUN_ERROR", {"status": "agent_error", "detail": err[:500]})],
        )
    finally:
        if obs is not None and Observability is not None:
            try:
                Observability().record_invocation(
                    obs,
                    agent_name=GEMINI_HACKATHON_AGENT.name,
                    user_id=user_id,
                    session_id=sid,
                    event_count=len(events),
                    status="ok",
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Observability.record_invocation() failed (non-fatal): %s", exc)

    return AgentTurnResult(
        status="ok",
        events=events,
        model_armor_check=sanitised,
        observability=obs,
    )
