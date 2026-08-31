"""gemini_hackathon.journey.level_3_marking_scheme — Level 3 body.

Level 3 of the British Isles Journey: per-criterion graders (one BAML
`ExtractMarkingSchemeGuideline` call per marking criterion) run in
parallel via `ParallelAgent`; `JoinNode` aggregates into the strategy
agent's input; the strategy agent writes the final grade.

Mirrors `gemini_hackathon/agents/workflows/pillar1_grading.py`'s
`Pillar1GradingWorkflow` (which already exists from W7), simplified for
the journey's per-question scope (one past-paper question at a time,
rather than a full LC exam paper).

The 4-node ADK 2 Workflow (per `adk2-tutorial/L2a_parallel_join/workflow.py`):

    START -> grade_criterion_1 ──┐
    START -> grade_criterion_2 ──┼─► join -> synthesise_grade
    START -> grade_criterion_3 ──┘

Each `grade_criterion_N` is the same function node parameterized by
the per-criterion metadata (criterion_id, max_marks, student_answer).
The strategy agent then writes a paragraph explaining the grade + cites
NCCA policy PDFs.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Level3Result:
    subject: str
    question_id: str
    criterion_grades: list[dict[str, Any]] = field(default_factory=list)
    total_marks_awarded: int = 0
    total_max_marks: int = 0
    strategy_summary: str = ""
    ncca_policy_citations: list[str] = field(default_factory=list)


# The 3 canonical marking criteria for an Irish LC Mathematics question
# (mirrors `gemini_hackathon/agents/workflows/pillar1_grading.py`'s shape,
# narrowed to a single question so the workshop demos in ~30 seconds).
DEFAULT_CRITERIA: tuple[dict[str, Any], ...] = (
    {
        "criterion_id": "AO1",
        "max_marks": 30,
        "description": "Mathematical reasoning + correct method",
    },
    {
        "criterion_id": "AO2",
        "max_marks": 30,
        "description": "Algebraic manipulation + simplification",
    },
    {"criterion_id": "AO3", "max_marks": 40, "description": "Final answer accuracy + units"},
)


async def grade_criterion_node(node_input: Any, criterion: dict[str, Any]) -> dict[str, Any]:
    """One per-criterion grader (the 3 parallel `grade_criterion_*` nodes).

    Per `pillar1_grading.grade_criterion`: returns marks_awarded + feedback
    + NCCA policy citations. In a real BAML extraction the `feedback`
    would come from `b.ExtractMarkingSchemeGuideline(text, criterion)`;
    the offline stub returns the canonical half-credit shape so the
    downstream JoinNode + strategy agent still have meaningful data.
    """
    student_answer = (node_input or {}).get("student_answer", "")
    criterion_id = criterion["criterion_id"]
    max_marks = criterion["max_marks"]

    marks_awarded = int(max_marks * 0.7) if student_answer else int(max_marks * 0.2)
    feedback = (
        f"Stub grader: the student's answer on {criterion_id} received "
        f"{marks_awarded}/{max_marks} for {criterion.get('description', '')}."
    )

    return {
        "criterion_id": criterion_id,
        "marks_awarded": marks_awarded,
        "max_marks": max_marks,
        "feedback": feedback,
        "ncca_policy_citations": ["SC-L1-L2-Programme-Statement.pdf"],
    }


async def join_criterion_grades(node_input: Any) -> dict[str, Any]:
    """JoinNode: bundle the 3 per-criterion grade dicts into one record."""
    grades = node_input.get("criterion_grades", [])
    return {
        "criterion_grades": grades,
        "total_marks_awarded": sum(g.get("marks_awarded", 0) for g in grades),
        "total_max_marks": sum(g.get("max_marks", 0) for g in grades),
    }


async def synthesise_strategy(node_input: Any) -> dict[str, Any]:
    """Strategy agent: write a paragraph explaining the grade + citing NCCA policy.

    In a real Workflow this would be an `Agent` node; since the
    `synthesis` is deterministic text on the joined inputs, we model it as
    a function node (per the pillar1_grading pattern).
    """
    awarded = node_input.get("total_marks_awarded", 0)
    maximum = node_input.get("total_max_marks", 0)
    grades = node_input.get("criterion_grades", [])

    pct = (awarded / maximum * 100.0) if maximum else 0.0
    per_criterion = ", ".join(
        f"{g['criterion_id']} {g['marks_awarded']}/{g['max_marks']}" for g in grades
    )
    citations = sorted({c for g in grades for c in g.get("ncca_policy_citations", [])})

    summary = (
        f"Total: {awarded}/{maximum} ({pct:.0f}%). Per criterion: {per_criterion}. "
        f"Cited: {', '.join(citations)}."
    )
    return {
        "strategy_summary": summary,
        "ncca_policy_citations": citations,
    }


async def run_level_3(
    *,
    subject: str = "mathematics",
    question_id: str = "Q5",
    student_answer: str = "",
    student_name: str = "",
) -> Level3Result:
    """The Level 3 entrypoint — runs the 4-node pipeline and returns the structured result.

    In the standalone-app path, the participant types a free-text
    student answer; the workflow grades it. In the orchestrator path, the
    student_answer comes from `ctx.state["student_answer"]` populated by
    the workshop host.
    """
    criteria = DEFAULT_CRITERIA
    grade_tasks = [grade_criterion_node({"student_answer": student_answer}, c) for c in criteria]
    grades = list(await asyncio.gather(*grade_tasks))
    joined = await join_criterion_grades({"criterion_grades": grades})
    strategy = await synthesise_strategy(joined)
    return Level3Result(
        subject=subject,
        question_id=question_id,
        criterion_grades=grades,
        total_marks_awarded=joined["total_marks_awarded"],
        total_max_marks=joined["total_max_marks"],
        strategy_summary=strategy["strategy_summary"],
        ncca_policy_citations=strategy["ncca_policy_citations"],
    )


__all__ = [
    "DEFAULT_CRITERIA",
    "Level3Result",
    "grade_criterion_node",
    "join_criterion_grades",
    "run_level_3",
    "synthesise_strategy",
]
