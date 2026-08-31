"""Tests for `gemini_hackathon.agents.workflows.*` — the 5 ADK 2 Pillar
workflows (1: Graph, 2: Colab Tutor, 3: Dynamic Research, 4: Long-running,
5: Eval Flywheel).

Updated 2026-08-31 (Phase 6): each module is exercised with stub ADK
dependencies (the workflows fall back to `None` when google-adk isn't
installed). The plain-Python helpers (`grade_criterion`, `join_outputs`)
are tested for behavioral correctness.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Pillar 1 — Graph Workflow (parallel grading)
# ---------------------------------------------------------------------------


def test_pillar1_workflow_data_class_round_trip():
    """`Pillar1GradingWorkflow` is a frozen dataclass with 3 fields."""
    from gemini_hackathon.agents.workflows.pillar1_grading import (
        Pillar1GradingWorkflow,
    )

    wf = Pillar1GradingWorkflow(
        subject="chemistry_lc",
        marking_criteria=("C1", "C2", "C3"),
        max_tokens_per_call=4096,
    )
    assert wf.subject == "chemistry_lc"
    assert wf.marking_criteria == ("C1", "C2", "C3")
    assert wf.max_tokens_per_call == 4096


def test_pillar1_workflow_defaults_max_tokens_per_call():
    """The default `max_tokens_per_call` is 2048 (the canonical completion budget)."""
    from gemini_hackathon.agents.workflows.pillar1_grading import (
        Pillar1GradingWorkflow,
    )

    assert Pillar1GradingWorkflow(subject="x", marking_criteria=()).max_tokens_per_call == 2048


def test_pillar1_grade_criterion_returns_stub():
    """`grade_criterion(node_input)` returns the half-credit stub."""
    from gemini_hackathon.agents.workflows.pillar1_grading import grade_criterion

    out = asyncio.run(grade_criterion({
        "criterion_id": "C1", "max_marks": 100, "student_answer": "x"
    }))
    assert out["criterion_id"] == "C1"
    assert out["marks_awarded"] == 70  # stub: 70% of 100
    assert out["max_marks"] == 100
    assert out["ncca_policy_citations"] == ["SC-L1-L2, p.12"]


def test_pillar1_join_outputs_sums_marks():
    """`join_outputs` sums the per-criterion marks."""
    from gemini_hackathon.agents.workflows.pillar1_grading import join_outputs

    out = asyncio.run(join_outputs({
        "criterion_grades": [
            {"marks_awarded": 20, "max_marks": 30},
            {"marks_awarded": 40, "max_marks": 70},
        ]
    }))
    assert out["total_marks_awarded"] == 60
    assert out["total_max_marks"] == 100


def test_pillar1_join_outputs_with_no_grades():
    """`join_outputs` with empty grades returns 0 marks (degenerate path)."""
    from gemini_hackathon.agents.workflows.pillar1_grading import join_outputs

    out = asyncio.run(join_outputs({"criterion_grades": []}))
    assert out["total_marks_awarded"] == 0
    assert out["total_max_marks"] == 0


# ---------------------------------------------------------------------------
# Pillar 2 — Collaborative Tutor (memory-aware handoffs)
# ---------------------------------------------------------------------------


def test_pillar2_workflow_round_trip():
    """The Pillar 2 dataclass survives construction."""
    from gemini_hackathon.agents.workflows.pillar2_collab_tutor import (
        Pillar2CollabTutorWorkflow,
    )

    wf = Pillar2CollabTutorWorkflow(coordinator_model="gemini-2.5-pro")
    assert wf.coordinator_model == "gemini-2.5-pro"
    assert wf.mode == "single_turn"  # default


def test_pillar3_workflow_round_trip():
    """The Pillar 3 dataclass survives construction."""
    from gemini_hackathon.agents.workflows.pillar3_dynamic_research import (
        Pillar3DynamicResearchWorkflow,
    )

    wf = Pillar3DynamicResearchWorkflow(model="gemini-2.5-pro")
    assert wf.model == "gemini-2.5-pro"
    assert wf.min_subquestions == 3  # default
    assert wf.max_subquestions == 7  # default


def test_pillar3_subquestion_node_returns_three_items():
    """`decompose_into_subquestions` returns 3 sub-questions (the default)."""
    from gemini_hackathon.agents.workflows.pillar3_dynamic_research import (
        decompose_into_subquestions,
    )

    out = asyncio.run(decompose_into_subquestions({"question": "x"}))
    assert len(out["sub_questions"]) == 3


def test_pillar3_synthesize_research_uses_subanswer_count():
    """`synthesize_research` headline mentions the subanswer count."""
    from gemini_hackathon.agents.workflows.pillar3_dynamic_research import (
        synthesize_research,
    )

    out = asyncio.run(synthesize_research({"sub_answers": ["a", "b", "c"]}))
    assert "3" in out["headline"]
    assert out["sections"] == ["a", "b", "c"]


def test_pillar4_workflow_round_trip():
    """The Pillar 4 dataclass survives construction."""
    from gemini_hackathon.agents.workflows.pillar4_long_running import (
        Pillar4LongRunningWorkflow,
    )

    wf = Pillar4LongRunningWorkflow()
    assert wf.resumability is not None
    assert wf.interrupt is not None


def test_pillar5_workflow_round_trip():
    """The Pillar 5 dataclass survives construction."""
    from gemini_hackathon.agents.workflows.pillar5_eval_flywheel import (
        Pillar5EvalFlywheel,
    )

    wf = Pillar5EvalFlywheel(eval_dataset_path="data/eval/cao.yaml")
    assert wf.eval_dataset_path == "data/eval/cao.yaml"
    assert wf.max_iterations == 10  # default
    assert wf.min_improvement == 0.05  # default


# ---------------------------------------------------------------------------
# All Pillars — `build_*_workflow(...)` returns None when google-adk is missing
# ---------------------------------------------------------------------------


def _build_pillar_under_no_adk(pillar: str):
    """Helper that patches `google.adk` to fail to import."""
    import builtins

    real_import = builtins.__import__ if isinstance(builtins, type(builtins)) else builtins["__import__"]
    saved = real_import
    blocked_modules = {"google.adk", "google.adk.workflow"}

    def fake(name, *args, **kwargs):
        if name in blocked_modules or name.startswith("google.adk."):
            raise ImportError(f"blocked {name}")
        return saved(name, *args, **kwargs)

    builtins.__import__ = fake
    try:
        if pillar == "pillar1":
            from gemini_hackathon.agents.workflows.pillar1_grading import (
                Pillar1GradingWorkflow,
                build_pillar1_grading_workflow,
            )
            return build_pillar1_grading_workflow(
                Pillar1GradingWorkflow(subject="x", marking_criteria=())
            )
        raise ValueError(pillar)
    finally:
        builtins.__import__ = saved


def test_pillar1_build_returns_none_when_google_adk_missing():
    """`build_pillar1_grading_workflow` returns None when ADK is not installed."""
    out = _build_pillar_under_no_adk("pillar1")
    assert out is None
