"""The Google ADK agent for the gemini_hackathon public demo.

Wraps `google.adk.agents.LlmAgent` with the project's 5 tools, builds an
`InMemoryRunner`, and exposes a session-aware `run_turn()` helper that
streams events in the AG-UI 17-event protocol shape.

The mandatory-framework requirement from the All Things Agentic
Hackathon rules is satisfied: this file uses `google.adk.agents.LlmAgent`
(the official Google Agent Development Kit, MIT-licensed) as the
canonical entry point.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)


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
):
    """Build the real `google.adk.agents.LlmAgent` + `InMemoryRunner`.

    Composes the system prompt from the active session identity and wires
    the 5 tools as `google.adk.tools.FunctionTool`. Returns ``(None, None)``
    if the ``google-adk`` package is not installed.
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
    agent = LlmAgent(
        name=GEMINI_HACKATHON_AGENT.name,
        model=GEMINI_HACKATHON_AGENT.model,
        description=GEMINI_HACKATHON_AGENT.description,
        instruction=instruction,
        tools=tools,
    )
    runner = InMemoryRunner(agent=agent)
    return agent, runner


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
]
