"""The Google ADK agent for the gemini_hackathon public demo.

Uses `google.adk.agents.LlmAgent` (the official Google Agent Development
Kit) — satisfies the "at least one Google Agent Framework" requirement
from the All Things Agentic Hackathon rules.

The agent has 5 tools:
    1. `lookup_outcome`           - BAML ExtractOutcome from a syllabus PDF page
    2. `retrieve_resources`       - RAG top-K over the chunked + embedded index
    3. `retrieve_safeguarding`    - returns the active subnation's policy
    4. `mark_answer`              - per-question mark breakdown via the
                                   Marking Grader Workflow
    5. `find_similar_resources`   - cross-national resource discovery
                                   ("an Irish Maths student asks: find me
                                   English AQA mechanics papers that cover
                                   vectors"). Uses the RAG index scoped to
                                   the user's subnation + a topic query,
                                   then ranks by syllabus-outcome overlap.

The agent's system prompt composes the active session identity
(subnation, role, subjects, cycle, palette, safeguarding) so the
response voice matches the user's home awarding body.

This file is intentionally framework-only: it uses the ADK's
LlmAgent + tool registry. The tool implementations live in
`gemini_hackathon/agents/tools.py` and the RAG index in
`gemini_hackathon/retrieval/`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# The agent definition
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentTool:
    """One tool the agent can call."""

    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentDefinition:
    """The static agent definition — used by the ADK runtime."""

    name: str
    model: str
    description: str
    system_prompt_template: str
    tools: tuple[AgentTool, ...]


# The canonical 5-tool ADK agent for the hackathon profile.
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
            description=(
                "Look up a specific learning outcome from the active subnation's "
                "syllabus. Returns the outcome text + page + outcome_id."
            ),
        ),
        AgentTool(
            name="retrieve_resources",
            description=(
                "Retrieve top-K resources (textbook chapters, exam papers, "
                "marking schemes) for a topic from the active subnation's "
                "official sources."
            ),
        ),
        AgentTool(
            name="find_similar_resources",
            description=(
                "Cross-national resource discovery. Given a topic, returns "
                "resources from OTHER British Isles jurisdictions that may "
                "help the user. Each result is labelled with source nation + "
                "resource type + reason for relevance."
            ),
        ),
        AgentTool(
            name="retrieve_safeguarding",
            description=(
                "Return the active subnation's safeguarding policy. Use when "
                "the question involves child safety, parent communications, "
                "or curriculum planning."
            ),
        ),
        AgentTool(
            name="mark_answer",
            description=(
                "Mark a piece of student work against a published marking scheme. "
                "Returns per-question mark breakdown using the NCCA / SQA / "
                "AQA / WJEC / CCEA descriptor vocabulary."
            ),
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
    """Render the ADK agent's system prompt for the active session."""
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
# ADK integration (degrades gracefully if the ADK package is not installed)
# ---------------------------------------------------------------------------


def build_adk_agent() -> Any:
    """Build the actual `google.adk.agents.LlmAgent` instance.

    Returns None if the `google-adk` package is not installed. The CLI
    smoke test verifies the agent definition is well-formed regardless.
    """
    try:
        # The official Google Agent Development Kit (Python).
        # https://github.com/google/adk-python
        from google.adk.agents import LlmAgent  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "google-adk is not installed. The agent definition is available "
            "via `GEMINI_HACKATHON_AGENT`; install google-adk to instantiate "
            "the LlmAgent."
        )
        return None

    from .tools import build_adk_tools

    tools = build_adk_tools()
    return LlmAgent(
        name=GEMINI_HACKATHON_AGENT.name,
        model=GEMINI_HACKATHON_AGENT.model,
        description=GEMINI_HACKATHON_AGENT.description,
        instruction=GEMINI_HACKATHON_AGENT.system_prompt_template,
        tools=tools,
    )


def is_adk_available() -> bool:
    try:
        import google.adk.agents  # noqa: F401
        return True
    except ImportError:
        return False


__all__ = [
    "AgentDefinition",
    "AgentTool",
    "GEMINI_HACKATHON_AGENT",
    "build_adk_agent",
    "is_adk_available",
    "render_system_prompt",
]
