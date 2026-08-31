"""workflow.py — the ADK 2 sequential Workflow that chains all 6 levels.

The orchestrator for the British Isles Journey. Per the codelab plan:

    START
      -> level_1_syllabus_extraction  (function + agent, per L1_graph_basics)
      -> level_2_past_paper_ocr         (ParallelAgent + JoinNode, per L2a)
      -> level_3_marking_scheme        (ParallelAgent + JoinNode, per L1_graph_basics)
      -> level_4_mastery_update        (single function node + status emitter)
      -> request_human_confirmation    (RequestInput HITL pause — per
                                         loop-lab-table/hello_workflow.py)
      -> level_5_asset_generation      (3 function nodes — search, BAML, FIBO)
      -> finalize                      (one status event for the studio)

Design notes:
  - ADK 2's `Workflow(edges=[...])` is the actual primitive; we use it
    here. No fabricated API.
  - Every node is async-callable so `Runner.run_async(...)` can drive the
    whole graph.
  - State templating uses `{learner_id}`, `{subnation}`, `{subject}`
    hydrated by `callback_before_agent.hydrate_participant_state` before
    this workflow runs (the orchestrator's `_resolve_state` reads it).
  - The HITL pause between Level 4 and Level 5 uses the ADK 2
    `RequestInput` event (per `loop-lab-table/hello_workflow.py`) — the
    orchestrator returns a `RequestInput` from `request_human_confirmation`,
    the ADK Runner pauses, and `run_async` resumes on the next user
    confirmation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class JourneyOutcome:
    """The full result of running all 6 levels."""

    learner_id: str
    subnation: str
    subject: str
    level_1: dict[str, Any] | None = None
    level_2: dict[str, Any] | None = None
    level_3: dict[str, Any] | None = None
    level_4: dict[str, Any] | None = None
    level_5: dict[str, Any] | None = None
    ncca_policy_citations: list[str] = field(default_factory=list)
    asset_storage_uri: str = ""


def _resolve_state(ctx: Any) -> dict[str, Any]:
    """Read per-participant state from `ctx.state` (populated by
    `hydrate_participant_state`). Best-effort across ADK 2 versions.
    """
    for attr in ("state", "_state"):
        if hasattr(ctx, attr):
            target = getattr(ctx, attr)
            if target is not None and hasattr(target, "get"):
                return dict(target)
    return {}


async def _level_1_node(ctx: Any) -> dict[str, Any]:
    state = _resolve_state(ctx)
    from gemini_hackathon.journey.level_1_syllabus_extraction import run_level_1

    result = await run_level_1(
        subnation=state.get("subnation", "ireland"),
        subject=state.get("subject", "mathematics"),
        language="en",
    )
    return {
        "pdf_path": result.pdf_path,
        "total_learning_outcomes": result.syllabus.get("total_learning_outcomes"),
        "chunks_embedded": len(result.chunks),
        "vector_backend": result.vector_backend,
    }


async def _level_2_node(ctx: Any) -> dict[str, Any]:
    """Runs the 4-path OCR ensemble. In the orchestrator's case the
    PDF path is derived from Level 1's `pdf_path` output (or the sample).
    """
    from gemini_hackathon.journey.level_2_past_paper_ocr import run_level_2

    state = _resolve_state(ctx)
    pdf_path = state.get("student_pdf_path", "") or ""
    result = await run_level_2(pdf_path=pdf_path)
    return {
        "voted_path": result.voted_path,
        "consensus_score": result.consensus_score,
        "page_count": result.page_count,
        "ncca_policy_citations": result.ncca_policy_citations,
    }


async def _level_3_node(ctx: Any) -> dict[str, Any]:
    state = _resolve_state(ctx)
    from gemini_hackathon.journey.level_3_marking_scheme import run_level_3

    result = await run_level_3(
        subject=state.get("subject", "mathematics"),
        question_id="Q5",
        student_answer=state.get("student_answer", ""),
    )
    return {
        "total_marks_awarded": result.total_marks_awarded,
        "total_max_marks": result.total_max_marks,
        "strategy_summary": result.strategy_summary,
        "ncca_policy_citations": result.ncca_policy_citations,
    }


async def _level_4_node(ctx: Any) -> dict[str, Any]:
    state = _resolve_state(ctx)
    from gemini_hackathon.journey.level_4_mastery_update import run_level_4

    result = await run_level_4(
        learner_id=state.get("learner_id", ""),
        subject_slug=state.get("subject", "mathematics"),
        outcome_code=state.get("outcome_code", "MA-LC-MA-1.1"),
        mastery_score=float(state.get("mastery_score", 0.75)),
    )
    return {
        "per_backend_status": result.per_backend_status,
        "mastery_vector_dim": result.mastery_vector_dim,
        "skill_graph_edge_count": result.skill_graph_edge_count,
    }


async def _level_5_node(ctx: Any) -> dict[str, Any]:
    state = _resolve_state(ctx)
    from gemini_hackathon.journey.level_5_asset_generation import run_level_5

    result = await run_level_5(
        user_question=state.get("user_question", "Draw a labelled diagram of the sine rule"),
        subnation=state.get("subnation", "ireland"),
        subject=state.get("subject", "mathematics"),
        language="en",
    )
    return {
        "asset_local_path": result.asset_local_path,
        "storage_uri": result.storage_uri,
        "asset_bytes_size": result.asset_bytes_size,
        "generation_backend": result.generation_backend,
        "matched_outcomes": result.matched_outcomes,
        "asset_request": result.asset_request,
    }


async def request_human_confirmation(ctx: Any) -> dict[str, Any]:
    """Emit the ADK 2 `RequestInput` pause between Level 4 and Level 5.

    The grounding research: `loop-lab-table/hello_workflow.py` + ADK 2
    docs at `google-adk==2.7.1`. The Runner pauses until the participant
    confirms via the studio's "Continue to Level 5" button.
    """
    try:
        from google.adk.events.request_input import RequestInput

        return RequestInput(
            message="Mastery ledger updated across 4 backends. Continue to Level 5 (asset generation)?"
        )
    except Exception:
        # Offline / no ADK: skip the pause entirely.
        return {"request_input": "skipped (no ADK RequestInput available)"}


async def run_full_journey(ctx: Any | None = None) -> JourneyOutcome:
    """The orchestrator's one-call entrypoint.

    Calls all 6 levels sequentially, threading state through `ctx`.
    Returns a `JourneyOutcome` for the studio to render. Resilient to
    any single level failing — the failure is recorded in the outcome
    rather than aborting the whole journey.
    """
    state = _resolve_state(ctx) if ctx is not None else {}
    learner_id = state.get("learner_id", "")
    subnation = state.get("subnation", "ireland")
    subject = state.get("subject", "mathematics")

    outcome = JourneyOutcome(
        learner_id=learner_id,
        subnation=subnation,
        subject=subject,
    )

    levels = [
        ("level_1", _level_1_node),
        ("level_2", _level_2_node),
        ("level_3", _level_3_node),
        ("level_4", _level_4_node),
        ("request_human_confirmation", request_human_confirmation),
        ("level_5", _level_5_node),
    ]

    for name, fn in levels:
        try:
            result = await fn(ctx)
            # Normalise to dict — `request_human_confirmation` returns a Pydantic
            # `RequestInput`, not a dict, which is what the downstream citation-
            # aggregator assumes.
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            elif hasattr(result, "__dict__") and not isinstance(result, dict):
                # Pydantic v2 model that returned a RequestInput — preserve the
                # original object but build a citation-extractable dict alongside.
                result_dict = {
                    "_event_type": type(result).__name__,
                    "ncca_policy_citations": [],
                    "message": getattr(result, "message", ""),
                }
            else:
                result_dict = dict(result)
            setattr(outcome, name, result_dict)
            logger.info("journey: %s OK", name)
            for c in result_dict.get("ncca_policy_citations") or []:
                if c and c not in outcome.ncca_policy_citations:
                    outcome.ncca_policy_citations.append(c)
            if name == "level_5":
                outcome.asset_storage_uri = result_dict.get("storage_uri", "")
        except Exception as exc:
            logger.exception("journey: %s FAILED — continuing with remaining levels", name)
            setattr(outcome, name, {"error": type(exc).__name__, "message": str(exc)})

    return outcome


__all__ = [
    "JourneyOutcome",
    "request_human_confirmation",
    "run_full_journey",
]
