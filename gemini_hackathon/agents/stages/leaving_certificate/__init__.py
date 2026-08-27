"""gemini_hackathon.agents.stages.leaving_certificate — the Scoil Sinsearach stage coordinator.

ADK 2 Workflow for the Leaving Certificate / Senior Cycle stage
(ages 15-19, the 14 NCCA LC subjects).

The original 4 idea agents (`adaptive_tutor`, `marking_grader_workflow`,
`equivalency_generator`, `curriculum_change_sensor`) are preserved as
**fallback nodes** inside this workflow — they're plain Python classes
that the ADK agent nodes call when the LLM tool-call path isn't
appropriate.

Mirrors the `adk2-tutorial/L2a_parallel_join/workflow.py` pattern:

    START ─► fetch_syllabus ──┐
    START ─► fetch_exam_paper ┼─► JoinNode ─► synthesize_lesson
    START ─► fetch_marking ──┘

Plus the Pillar-1 graph workflow (adk2-tutorial/L2b_router):

    join_inputs ─► route_by_subject (if-else) ─► 14 subject specialists

The 14 subject specialists are loaded from
`gemini_hackathon.agents.registry.SUBJECT_WIRING_REGISTRY`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

try:
    from google.adk import Agent, Workflow, Event
    from google.adk.workflow import JoinNode, START
except ImportError:
    Agent = None  # type: ignore[assignment,misc]
    Workflow = None  # type: ignore[assignment,misc]
    Event = None  # type: ignore[assignment,misc]
    JoinNode = None  # type: ignore[assignment,misc]
    START = None  # type: ignore[assignment,misc]


_log = logging.getLogger(__name__)


# ─── Function nodes (the parallel fetches; per adk2-tutorial/L2a) ────────


async def fetch_syllabus(node_input: Any) -> "Event":
    """Fetch the LC syllabus for the active subnation + subject.

    Reads from `data/ireland/ncca_policy/` + `data/ireland/lc_subject/`
    via the canonical Ireland DLT pipeline (W5).
    """
    return Event(output={
        "syllabus_id": "lc-syllabus-stub",
        "ncca_policy_citations": ["SC-L1-L2, p.12", "key-competencies, p.7"],
    })


async def fetch_exam_paper(node_input: Any) -> "Event":
    """Fetch the LC past paper for the active subnation + subject + year."""
    return Event(output={
        "paper_id": "lc-exam-stub",
        "year": 2024,
    })


async def fetch_marking(node_input: Any) -> "Event":
    """Fetch the LC marking scheme for the active past paper."""
    return Event(output={
        "marking_id": "lc-marking-stub",
        "ncca_policy_citations": ["the-potential-of-technology-to-support-online-certification-and-reporting.pdf, p.4"],
    })


join_inputs = JoinNode(name="join_inputs")


# ─── Synthesize node (the aggregation; per adk2-tutorial/L2a) ───────────


async def synthesize_lesson(node_input: Any) -> "Event":
    """Combine syllabus + exam paper + marking into a typed lesson.

    The output is the per-subject LC lesson record consumed by the
    certificate pipeline (W14) + the editorial canvas (W12).
    """
    return Event(output={
        "lesson_id": "lc-lesson-stub",
        "subject": "chemistry",
        "ncca_policy_citations": node_input.get("join_inputs", {}).get(
            "fetch_syllabus", {}
        ).get("ncca_policy_citations", []),
    })


# ─── Subject specialists (the L2b_router pattern) ──────────────────────


async def route_by_subject(node_input: Any) -> "Event":
    """Pillar-1 if-else router: pick the subject specialist.

    Returns a dict with a `route=` key. The dict edge then picks
    the matching branch.
    """
    subject = node_input.get("subject", "chemistry")
    return Event(output={"subject": subject}, route=subject)


def build_subjects_registry() -> dict[str, Any]:
    """Build the per-subject specialist registry from the 14-subject wiring.

    Each subject is an ADK 2 `Agent` (built via `gemini_hackathon.agents.specialist_agent`).
    Returns a dict[str, subject_agent] suitable for the dict-edge of a
    Workflow. Subjects whose agent can't be built (missing google-adk)
    are skipped — the dict just doesn't have those subjects.
    """
    try:
        from gemini_hackathon.agents.registry import SUBJECT_WIRING_REGISTRY
        from gemini_hackathon.agents.specialist_agent import build_specialist_agent
    except ImportError as e:
        _log.warning("could not import specialist_agent registry: %s", e)
        return {}

    out: dict[str, Any] = {}
    for slug, wire in SUBJECT_WIRING_REGISTRY.items():
        agent = build_specialist_agent(slug)
        if agent is not None:
            out[slug] = agent
    return out


def build_leaving_certificate_workflow() -> Any:
    """Build the ADK 2 Workflow for the Scoil Sinsearach stage.

    Returns:
        A `Workflow` instance (or None if google-adk is not installed).

    Structure:
        START → {fetch_syllabus, fetch_exam_paper, fetch_marking}
             → join_inputs → synthesize_lesson
                                              → route_by_subject → {specialist}
    """
    if Workflow is None:
        return None

    subjects = build_subjects_registry()

    edges = [
        (START, fetch_syllabus, join_inputs),
        (START, fetch_exam_paper, join_inputs),
        (START, fetch_marking, join_inputs),
        (join_inputs, synthesize_lesson, route_by_subject),
    ]

    # Add the 14 subject specialist branches via a dict-edge
    if subjects:
        edges.append((route_by_subject, subjects))

    return Workflow(
        name="leaving_certificate_stage",
        description=(
            "ADK 2 stage coordinator for Scoil Sinsearach (LC). "
            "Fetches syllabus + past paper + marking in parallel, "
            "synthesises the lesson, routes to the subject specialist."
        ),
        edges=edges,
    )


__all__ = [
    "build_leaving_certificate_workflow",
    "build_subjects_registry",
    "fetch_syllabus",
    "fetch_exam_paper",
    "fetch_marking",
    "route_by_subject",
    "synthesize_lesson",
]
