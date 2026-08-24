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
    EquivalencyGenerator,
    EquivalencyRequest,
    EquivalencyResult,
    EquivalencyRow,
    JURISDICTION_AWARDING_BODY,
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
]
