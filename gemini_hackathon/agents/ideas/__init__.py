"""gemini_hackathon.agents.ideas — the 4 idea agents.

The 4 idea agents each implement one of the BIEP Hackathon v3
concepts (per the openspec change
``2026-08-24-gemini-hackathon-public-v1``):

1. :mod:`.marking_grader_workflow` — LC marking grader workflow.
2. :mod:`.adaptive_tutor` — personalised tutoring aligned to the
   active source palette + jurisdiction.
3. :mod:`.equivalency_generator` — cross-jurisdiction equivalency
   generator.
4. :mod:`.curriculum_change_sensor` — detects new syllabus PDFs +
   re-runs the theming extraction.
"""

from __future__ import annotations

from .adaptive_tutor import (
    AdaptiveTutor,
    TutorRequest,
    TutorResponse,
    build_default_tutor,
    tutor_invoker,
)
from .curriculum_change_sensor import (
    ChangeEvent,
    ChangeType,
    CurriculumChangeRequest,
    CurriculumChangeResult,
    CurriculumChangeSensor,
    build_default_sensor,
    sensor_invoker,
)
from .equivalency_generator import (
    ALL_TARGET_JURISDICTIONS,
    JURISDICTION_AWARDING_BODY,
    EquivalencyGenerator,
    EquivalencyRequest,
    EquivalencyResult,
    EquivalencyRow,
    build_default_generator,
    generator_invoker,
)
from .marking_grader_workflow import (
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

__all__ = [
    # Equivalency Generator
    "ALL_TARGET_JURISDICTIONS",
    # Marking Grader Workflow
    "DEFAULT_LC_GRADING_SCALE",
    "JURISDICTION_AWARDING_BODY",
    # Adaptive Tutor
    "AdaptiveTutor",
    # Curriculum Change Sensor
    "ChangeEvent",
    "ChangeType",
    "CurriculumChangeRequest",
    "CurriculumChangeResult",
    "CurriculumChangeSensor",
    "EquivalencyGenerator",
    "EquivalencyRequest",
    "EquivalencyResult",
    "EquivalencyRow",
    "MarkingBreakdown",
    "MarkingGraderWorkflow",
    "MarkingRequest",
    "MarkingResult",
    "MarkingSchemeQuestion",
    "StudentAnswer",
    "TutorRequest",
    "TutorResponse",
    "build_default_generator",
    "build_default_sensor",
    "build_default_tutor",
    "build_default_workflow",
    "generator_invoker",
    "sensor_invoker",
    "tutor_invoker",
    "workflow_invoker",
]
