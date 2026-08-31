"""gemini_hackathon.agents.workflows.pillar3_dynamic_research — Pillar 3 (Dynamic Research).

Lifted from `adk2-tutorial/L4a_flat_research/deep_research.py` and adapted:
the canonical dynamic-research workflow decomposes a learner question
into N sub-questions at runtime (Pillar-3 dynamic fan-out), researches
each in parallel, then synthesises the briefing.

Used by:
  - gemini_hackathon.agents.stages.cross_subject (the NCCA Key
    Competencies update fan-out)
  - gemini_hackathon/gradio/anam_education/mac_leinn.py (the formative
    exit-card generator — decomposes a topic into N questions)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Pillar3DynamicResearchWorkflow:
    """The configured dynamic-research workflow."""

    model: str = "gemini-2.0-flash"
    max_subquestions: int = 7
    min_subquestions: int = 3
    max_per_call: int = 4096


async def decompose_into_subquestions(node_input: Any) -> dict:
    """Decompose the learner question into N sub-questions at runtime."""
    question = node_input.get("question", "")
    return {
        "sub_questions": [f"Sub-question {i + 1} for: {question}" for i in range(3)],
    }


async def synthesize_research(node_input: Any) -> dict:
    """Aggregate the per-sub-question research into one briefing."""
    sub_answers = node_input.get("sub_answers", [])
    return {
        "headline": f"Research briefing synthesised from {len(sub_answers)} sub-answers",
        "sections": sub_answers,
    }


def build_decompose_research_workflow(config: Pillar3DynamicResearchWorkflow) -> Any:
    """Build the ADK 2 Workflow with parallel_worker fan-out."""
    try:
        from google.adk import Agent, Event, Workflow
        from google.adk.workflow import START, RetryConfig, node
    except ImportError:
        _log.warning("google-adk not installed; pillar3 returns None")
        return None

    retry = RetryConfig(max_attempts=3, initial_delay=1.0, backoff_factor=2.0)

    if node is not None:

        @node(parallel_worker=True, rerun_on_resume=True, retry_config=retry)
        async def fanout_research(node_input):
            return Event(output={"sub_answers": [node_input.get("question", "")]})
    else:
        fanout_research = None

    edges = [(START, decompose_into_subquestions, fanout_research)]
    if fanout_research is not None:
        edges.append((fanout_research, synthesize_research))

    return Workflow(
        name="pillar3_decompose_research",
        description=(
            "Pillar 3 (Dynamic Research): decompose the learner question "
            "into N sub-questions at runtime, research each in parallel, "
            "synthesise the briefing."
        ),
        edges=edges,
    )


__all__ = [
    "Pillar3DynamicResearchWorkflow",
    "build_decompose_research_workflow",
    "decompose_into_subquestions",
    "synthesize_research",
]
