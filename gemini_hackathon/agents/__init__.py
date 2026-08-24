"""gemini_hackathon.agents — the 4 idea agents + the 7 Fleet primitives.

Re-exports the 4 idea agents (one module per agent) + the 7
Fleet primitives (the ``fleet`` subpackage).

The 4 idea agents:

1. :mod:`gemini_hackathon.agents.ideas.marking_grader_workflow` —
   the LC marking grader workflow.
2. :mod:`gemini_hackathon.agents.ideas.adaptive_tutor` —
   personalised tutoring aligned to the active source palette +
   jurisdiction.
3. :mod:`gemini_hackathon.agents.ideas.equivalency_generator` —
   cross-jurisdiction equivalency generator (NCCA → AQA / OCR /
   Pearson / SQA / WJEC / CCEA / IoM).
4. :mod:`gemini_hackathon.agents.ideas.curriculum_change_sensor` —
   detects new syllabus PDFs + re-runs the theming extraction.
"""

from __future__ import annotations

from . import fleet
from .ideas.adaptive_tutor import (
    AdaptiveTutor,
    TutorRequest,
    TutorResponse,
    build_default_tutor,
    tutor_invoker,
)
from .ideas.curriculum_change_sensor import (
    ChangeEvent,
    ChangeType,
    CurriculumChangeRequest,
    CurriculumChangeResult,
    CurriculumChangeSensor,
    build_default_sensor,
    sensor_invoker,
)
from .ideas.equivalency_generator import (
    ALL_TARGET_JURISDICTIONS,
    EquivalencyGenerator,
    EquivalencyRequest,
    EquivalencyResult,
    EquivalencyRow,
    JURISDICTION_AWARDING_BODY,
    build_default_generator,
    generator_invoker,
)
from .ideas.marking_grader_workflow import (
    DEFAULT_LC_GRADING_SCALE,
    MarkingBreakdown,
    MarkingGraderWorkflow,
    MarkingRequest,
    MarkingResult,
    MarkingSchemeQuestion,
    StudentAnswer,
    build_default_workflow,
    workflow_invoker,
)


def build_default_agents() -> dict[str, object]:
    """Return the canonical instance of each idea agent.

    Returns:
        A dict mapping the agent name (one of ``fleet_gateway.AGENT_NAMES``)
        to the corresponding agent instance.

    Example::

        from gemini_hackathon.agents import build_default_agents, FleetGateway
        agents = build_default_agents()
        gateway = FleetGateway()
        for name, agent in agents.items():
            gateway.register_agent(name, agent.as_gateway_invoker)
    """
    return {
        "marking_grader_workflow": build_default_workflow(),
        "adaptive_tutor": build_default_tutor(),
        "equivalency_generator": build_default_generator(),
        "curriculum_change_sensor": build_default_sensor(),
    }


__all__ = [
    "fleet",
    # Adaptive Tutor
    "AdaptiveTutor",
    "TutorRequest",
    "TutorResponse",
    "build_default_tutor",
    "tutor_invoker",
    # Equivalency Generator
    "ALL_TARGET_JURISDICTIONS",
    "EquivalencyGenerator",
    "EquivalencyRequest",
    "EquivalencyResult",
    "EquivalencyRow",
    "JURISDICTION_AWARDING_BODY",
    "build_default_generator",
    "generator_invoker",
    # Marking Grader Workflow
    "DEFAULT_LC_GRADING_SCALE",
    "MarkingBreakdown",
    "MarkingGraderWorkflow",
    "MarkingRequest",
    "MarkingResult",
    "MarkingSchemeQuestion",
    "StudentAnswer",
    "build_default_workflow",
    "workflow_invoker",
    # Curriculum Change Sensor
    "ChangeEvent",
    "ChangeType",
    "CurriculumChangeRequest",
    "CurriculumChangeResult",
    "CurriculumChangeSensor",
    "build_default_sensor",
    "sensor_invoker",
    # Convenience
    "build_default_agents",
]
