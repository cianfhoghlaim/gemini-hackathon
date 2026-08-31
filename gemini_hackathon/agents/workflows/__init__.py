"""gemini_hackathon.agents.workflows — the 5 ADK-2 workflow patterns.

Lifted + adapted from `adk2-tutorial/`:

  - pillar1_grading.py    — L2a_parallel_join pattern (3 parallel fetches
                            + JoinNode + synthesis). Used by the marking
                            grader workflow + the LC stage coordinator.
  - pillar2_collab_tutor.py — L3a_collaborative pattern (coordinator +
                            sub_agents + mode="single_turn"). Used by
                            the MeanScoil + Scoil Sinsearach coordinators
                            (subject specialists).
  - pillar3_dynamic_research.py — L4a/L4b patterns (parallel_worker
                            + recursive ctx.run_node). Used by the
                            cross-subject competency workflow + the
                            certificate pipeline (W14).
  - pillar4_long_running.py — monstertix pattern (LongRunningFunctionTool
                            + ResumabilityConfig + RequestInput). Used
                            for human-in-the-loop marking review.
  - pillar5_eval_flywheel.py — loop-lab-table pattern (adk optimize +
                            world.py + custom adk eval metric). Used by
                            the W9 skill-progression ledger's flywheel.

Each pillar is a standalone building block. The stage coordinators in
`gemini_hackathon.agents.stages.<stage>/` compose the pillars they need.
"""

from gemini_hackathon.agents.workflows.pillar1_grading import (
    Pillar1GradingWorkflow,
    build_pillar1_grading_workflow,
    grade_criterion,
    join_outputs,
)
from gemini_hackathon.agents.workflows.pillar2_collab_tutor import (
    Pillar2CollabTutorWorkflow,
    build_collab_tutor_workflow,
)
from gemini_hackathon.agents.workflows.pillar3_dynamic_research import (
    Pillar3DynamicResearchWorkflow,
    build_decompose_research_workflow,
    decompose_into_subquestions,
    synthesize_research,
)
from gemini_hackathon.agents.workflows.pillar4_long_running import (
    Pillar4LongRunningWorkflow,
    RequestInputInterrupt,
    ResumabilityConfig,
    build_long_running_workflow,
)
from gemini_hackathon.agents.workflows.pillar5_eval_flywheel import (
    Pillar5EvalFlywheel,
    build_eval_flywheel,
)

__all__ = [
    # Pillar 1: Graph workflow (parallel grading)
    "Pillar1GradingWorkflow",
    # Pillar 2: Collaborative tutor
    "Pillar2CollabTutorWorkflow",
    # Pillar 3: Dynamic research (parallel + recursive)
    "Pillar3DynamicResearchWorkflow",
    # Pillar 4: Long-running + ResumabilityConfig
    "Pillar4LongRunningWorkflow",
    # Pillar 5: Eval flywheel (loop-lab-table pattern)
    "Pillar5EvalFlywheel",
    "RequestInputInterrupt",
    "ResumabilityConfig",
    "build_collab_tutor_workflow",
    "build_decompose_research_workflow",
    "build_eval_flywheel",
    "build_long_running_workflow",
    "build_pillar1_grading_workflow",
    "decompose_into_subquestions",
    "grade_criterion",
    "join_outputs",
    "synthesize_research",
]
