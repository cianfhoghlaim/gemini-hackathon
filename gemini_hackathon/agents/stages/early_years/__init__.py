"""gemini_hackathon.agents.stages.early_years — the Aistear stage coordinator.

ADK 2 Workflow for the Early Years stage (ages 0-6, the Aistear
framework).

This is the smallest coordinator (Aistear is a high-level framework
rather than a subject curriculum). The workflow handles the 4 Aistear
themes (Well-being / Identity & Belonging / Communicating / Exploring
& Thinking) and routes to the appropriate play-based learning
specialist.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from google.adk import Workflow, Event
    from google.adk.workflow import JoinNode, START
except ImportError:
    Workflow = None  # type: ignore[assignment,misc]
    Event = None  # type: ignore[assignment,misc]
    JoinNode = None  # type: ignore[assignment,misc]
    START = None  # type: ignore[assignment,misc]


_log = logging.getLogger(__name__)


# The 4 Aistear themes
AISTEAR_THEMES: tuple[str, ...] = (
    "wellbeing",
    "identity_and_belonging",
    "communicating",
    "exploring_and_thinking",
)


async def fetch_aistear_theme(node_input: Any) -> "Event":
    """Fetch the Aistear framework content for one of the 4 themes."""
    return Event(output={"theme_id": "aistear-theme-stub"})


async def synthesize_play_plan(node_input: Any) -> "Event":
    """Combine the 4 Aistear themes into a play-based learning plan."""
    return Event(output={"play_plan_id": "aistear-play-plan-stub"})


aistear_join = JoinNode(name="aistear_join")


async def route_aistear_theme(node_input: Any) -> "Event":
    """Route to the appropriate Aistear theme specialist."""
    theme = node_input.get("theme", "wellbeing")
    return Event(output={"theme": theme}, route=theme)


def build_early_years_workflow() -> Any:
    """Build the ADK 2 Workflow for the Aistear (Early Years) stage."""
    if Workflow is None:
        return None

    edges = [
        (START, fetch_aistear_theme, aistear_join),
        (aistear_join, synthesize_play_plan, route_aistear_theme),
    ]

    return Workflow(
        name="early_years_stage",
        description=(
            "ADK 2 stage coordinator for Aistear (Early Years). "
            "Fetches the 4 Aistear themes, synthesises the play plan, "
            "routes to the theme specialist."
        ),
        edges=edges,
    )


__all__ = [
    "build_early_years_workflow",
    "AISTEAR_THEMES",
    "fetch_aistear_theme",
    "synthesize_play_plan",
    "route_aistear_theme",
]
