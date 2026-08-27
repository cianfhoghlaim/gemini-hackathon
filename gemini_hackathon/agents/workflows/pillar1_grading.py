"""gemini_hackathon.agents.workflows.pillar1_grading — Pillar 1 (Graph Workflow).

Lifted from `adk2-tutorial/L2a_parallel_join/workflow.py` and adapted:
the canonical LC past-paper grading workflow runs 1 criterion grader
per marking criterion in parallel, then synthesises the final grade.

Used by:
  - gemini_hackathon.agents.stages.leaving_certificate (the
    Scoil Sinsearach marking step)
  - gemini_hackathon/gradio/an_scrudu/app.py (the studio's "grade
    paper" workflow — replaces the current sequential grading)

Mirrors the adk2-tutorial L2a pattern:

    START ─► grade_criterion_1 ──┐
    START ─► grade_criterion_2 ──┼─► JoinNode ─► synthesise_grade
    START ─► grade_criterion_3 ──┘
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Pillar1GradingWorkflow:
    """The configured grading workflow (declarative — no ADK dependency).

    Use this dataclass to describe the workflow + then `build_*` it
    into an actual ADK 2 `Workflow` (which requires google-adk).
    """

    subject: str
    marking_criteria: tuple[str, ...]
    max_tokens_per_call: int = 2048


async def grade_criterion(node_input: Any) -> dict:
    """Grade a single criterion. Returns a dict with criterion_id + marks."""
    criterion_id = node_input.get("criterion_id", "?")
    max_marks = node_input.get("max_marks", 100)
    student_answer = node_input.get("student_answer", "")

    # Stub: a real implementation calls
    # `baml_extracts/education/lc_subject/GradeMarkingCriterion()`.
    # The stub returns the half-credit shape for testability.
    return {
        "criterion_id": criterion_id,
        "marks_awarded": int(max_marks * 0.7),
        "max_marks": max_marks,
        "feedback": f"Stub feedback for criterion {criterion_id}",
        "ncca_policy_citations": ["SC-L1-L2, p.12"],
    }


async def join_outputs(node_input: Any) -> dict:
    """JoinNode: aggregate the per-criterion grade dicts into one record."""
    criterion_grades = node_input.get("criterion_grades", [])
    return {
        "criterion_grades": criterion_grades,
        "total_marks_awarded": sum(g.get("marks_awarded", 0) for g in criterion_grades),
        "total_max_marks": sum(g.get("max_marks", 0) for g in criterion_grades),
    }


def build_pillar1_grading_workflow(config: Pillar1GradingWorkflow) -> Any:
    """Build the ADK 2 Workflow from the declarative config.

    Returns None if google-adk is not installed.
    """
    try:
        from google.adk import Workflow, Event
        from google.adk.workflow import JoinNode, START
    except ImportError:
        _log.warning("google-adk not installed; pillar1_grading returns None")
        return None

    # Each criterion becomes a function node. ADK 2 requires
    # distinct closures per node (the Graph validator rejects duplicate
    # `__name__`), so we build each via `functools.partial` and a
    # naming helper.
    import functools

    def _make_grade_node(criterion_id: str):
        async def _grade_one(node_input):
            return Event(output={
                "criterion_grades": [
                    await grade_criterion({"criterion_id": criterion_id, **node_input})
                ]
            })
        _grade_one.__name__ = f"grade_{criterion_id}"
        _grade_one.__qualname__ = f"grade_{criterion_id}"
        return _grade_one

    criterion_nodes = [_make_grade_node(c) for c in config.marking_criteria]

    join_node = JoinNode(name="join_grades")

    edges = []
    for node in criterion_nodes:
        edges.append((START, node, join_node))

    # Synthesise step
    async def _synthesise(node_input):
        joined = await join_outputs(node_input)
        return Event(output=joined)
    edges.append((join_node, _synthesise))

    return Workflow(
        name=f"pillar1_grading_{config.subject}",
        description=(
            f"Pillar 1 (Graph Workflow) for {config.subject}: parallel "
            f"grade + synthesise."
        ),
        edges=edges,
    )


__all__ = ["Pillar1GradingWorkflow", "build_pillar1_grading_workflow", "grade_criterion", "join_outputs"]
