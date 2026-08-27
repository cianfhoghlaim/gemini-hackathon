"""gemini_hackathon.agents.stages.primary — the Bunscoil stage coordinator.

ADK 2 Workflow for the Primary stage (ages 4-12, the 12 NCCA primary
curriculum areas: English / Gaeilge / Mathematics / SESE / Visual Arts
/ Music / Drama / PE / SPHE / Religion / Stand-alone Gaeilge / ...).

Mirrors the `adk2-tutorial/L2a_parallel_join` pattern: parallel fetches
for the 12 primary areas + a join node that synthesises the lesson.

The original `adaptive_tutor` idea agent is preserved as the fallback
tutor node for primary learners who don't fit the 12 NCCA buckets
(e.g. special educational needs tutors).
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


# The 12 NCCA primary curriculum areas (W5 lift)
PRIMARY_AREAS: tuple[str, ...] = (
    "english",
    "gaeilge",
    "mathematics",
    "sese_science",
    "sese_history",
    "sese_geography",
    "visual_arts",
    "music",
    "drama",
    "physical_education",
    "sphe",
    "religion",
)


async def fetch_primary_area_spec(node_input: Any) -> "Event":
    """Fetch the primary curriculum spec for one of the 12 areas."""
    return Event(output={"area_spec_id": "primary-area-stub"})


async def fetch_primary_outcomes(node_input: Any) -> "Event":
    """Fetch the primary learning outcomes for one of the 12 areas."""
    return Event(output={"outcomes_id": "primary-outcomes-stub"})


primary_join = JoinNode(name="primary_join")


async def synthesize_primary_lesson(node_input: Any) -> "Event":
    """Combine area spec + outcomes into a primary-level lesson."""
    return Event(output={"lesson_id": "primary-lesson-stub"})


async def route_primary_area(node_input: Any) -> "Event":
    """Pillar-1 router: pick the primary area specialist."""
    area = node_input.get("area", "english")
    return Event(output={"area": area}, route=area)


def build_primary_workflow() -> Any:
    """Build the ADK 2 Workflow for the Bunscoil (Primary) stage."""
    if Workflow is None:
        return None

    edges = [
        (START, fetch_primary_area_spec, primary_join),
        (START, fetch_primary_outcomes, primary_join),
        (primary_join, synthesize_primary_lesson, route_primary_area),
    ]

    return Workflow(
        name="primary_stage",
        description=(
            "ADK 2 stage coordinator for Bunscoil (Primary). "
            "Fetches area spec + outcomes in parallel, synthesises the "
            "primary lesson, routes to the area specialist."
        ),
        edges=edges,
    )


__all__ = [
    "build_primary_workflow",
    "PRIMARY_AREAS",
    "fetch_primary_area_spec",
    "fetch_primary_outcomes",
    "synthesize_primary_lesson",
]
