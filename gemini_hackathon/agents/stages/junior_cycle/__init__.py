"""gemini_hackathon.agents.stages.junior_cycle — the MeanScoil stage coordinator.

ADK 2 Workflow for the Junior Cycle stage (ages 12-15, the 18 NCCA JC
subjects + 16 short courses + 36 CBAs).

Mirrors the `adk2-tutorial/L2b_router` pattern: deterministic
if-else router that picks the right subject specialist.

The original `adaptive_tutor` idea agent (from `gemini_hackathon/agents/ideas/`)
is preserved as a fallback node for tutors that don't fit the 18 NCCA JC
buckets (e.g. learning-support teachers).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

try:
    from google.adk import Agent, Workflow, Event
    from google.adk.workflow import START
except ImportError:
    Agent = None  # type: ignore[assignment,misc]
    Workflow = None  # type: ignore[assignment,misc]
    Event = None  # type: ignore[assignment,misc]
    START = None  # type: ignore[assignment,misc]


_log = logging.getLogger(__name__)


async def fetch_jc_subject_spec(node_input: Any) -> "Event":
    """Fetch the JC subject specification for the active subnation + subject."""
    return Event(output={
        "spec_id": "jc-spec-stub",
        "stage": "junior_cycle",
        "ncca_policy_citations": ["SC-L1-L2, p.12", "key-competencies, p.7"],
    })


async def fetch_jc_cba_descriptors(node_input: Any) -> "Event":
    """Fetch the JC Classroom-Based Assessment descriptors (36 CBAs)."""
    return Event(output={"cba_id": "jc-cba-stub"})


async def fetch_jc_short_course(node_input: Any) -> "Event":
    """Fetch the JC short course content (16 short courses)."""
    return Event(output={"short_course_id": "jc-short-course-stub"})


async def route_jc_subject(node_input: Any) -> "Event":
    """Pillar-1 router: pick the JC subject specialist."""
    subject = node_input.get("subject", "english")
    return Event(output={"subject": subject}, route=subject)


def build_junior_cycle_workflow() -> Any:
    """Build the ADK 2 Workflow for the MeanScoil (JC) stage."""
    if Workflow is None:
        return None

    try:
        from gemini_hackathon.agents.registry import SUBJECT_WIRING_REGISTRY
    except ImportError:
        SUBJECT_WIRING_REGISTRY = {}

    # The JC bucket (10 subjects — subset of the 14 LC registry
    # that map to JC subjects). Built via the specialist_agent factory
    # so each subject becomes an ADK Agent (not a dataclass).
    from gemini_hackathon.agents.specialist_agent import build_specialist_agent
    jc_subject_slugs = (
        "english", "gaeilge", "mathematics", "history",
        "geography", "biology", "chemistry", "physics",
        "french", "irish_t2",
    )
    jc_subjects: dict[str, Any] = {}
    for slug in jc_subject_slugs:
        agent = build_specialist_agent(slug)
        if agent is not None:
            jc_subjects[slug] = agent

    edges = [
        (START, fetch_jc_subject_spec, route_jc_subject),
        (START, fetch_jc_cba_descriptors, route_jc_subject),
        (START, fetch_jc_short_course, route_jc_subject),
    ]
    if jc_subjects:
        edges.append((route_jc_subject, jc_subjects))

    return Workflow(
        name="junior_cycle_stage",
        description=(
            "ADK 2 stage coordinator for MeanScoil (Junior Cycle). "
            "Fetches the subject spec + CBA descriptors + short course "
            "content in parallel, routes to the subject specialist."
        ),
        edges=edges,
    )


__all__ = [
    "build_junior_cycle_workflow",
    "fetch_jc_subject_spec",
    "fetch_jc_cba_descriptors",
    "fetch_jc_short_course",
    "route_jc_subject",
]
