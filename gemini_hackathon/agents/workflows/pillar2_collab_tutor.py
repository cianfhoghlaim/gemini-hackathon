"""gemini_hackathon.agents.workflows.pillar2_collab_tutor — Pillar 2 (Collaborative Tutor).

Lifted from `adk2-tutorial/L3a_collaborative/concierge.py` and adapted:
the canonical collaborative-tutor pattern is a coordinator + N
specialist sub_agents in `mode="single_turn"`. The coordinator picks
the subset, ADK runs them in parallel, each returns its answer, the
coordinator synthesises.

Used by:
  - gemini_hackathon.agents.stages.leaving_certificate.subjects
  - gemini_hackathon.agents.stages.junior_cycle.subjects
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Pillar2CollabTutorWorkflow:
    """The configured collaborative tutor workflow."""

    coordinator_model: str = "gemini-2.0-flash"
    specialist_models: dict[str, str] = field(default_factory=dict)
    mode: str = "single_turn"  # the default — coordinator picks subset, ADK runs in parallel


async def build_collab_tutor_workflow(config: Pillar2CollabTutorWorkflow) -> Any:
    """Build the ADK 2 sub_agents-based collaborative tutor workflow.

    Returns None if google-adk is not installed.
    """
    try:
        from google.adk import Agent, LlmAgent
    except ImportError:
        _log.warning("google-adk not installed; pillar2_collab returns None")
        return None

    if not config.specialist_models:
        return None

    # Build the coordinator
    return LlmAgent(
        name="subject_coordinator",
        model=config.coordinator_model,
        description="Routes learner questions to subject specialists.",
        instruction=(
            "You are the gemini_hackathon subject coordinator. "
            "Route each learner question to the matching subject specialist. "
            "Synthesise their answers into one response."
        ),
        sub_agents=[
            LlmAgent(
                name=f"{slug}_specialist",
                model=model,
                description=f"Subject specialist for {slug}.",
                instruction=f"You are the {slug} subject specialist.",
                tools=[],
            )
            for slug, model in config.specialist_models.items()
        ],
    )


__all__ = ["Pillar2CollabTutorWorkflow", "build_collab_tutor_workflow"]
