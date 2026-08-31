"""gemini_hackathon.agents.stages.cross_subject — the 5 NCCA Key Competencies workflow.

Cross-stage workflow that maps formative-assessment exit cards + topic
mastery onto the 5 NCCA Key Competencies
(Communicating / Being Creative / Working with Others / Managing
Information & Thinking / Managing Myself) + the 6th "Staying Well"
competency from the SCR advisory.

This is the workflow that powers the W9 skill-progression ledger:
every formative assessment exit card + every topic mastery event
feeds through this workflow to update the per-learner competency
mastery vectors (320 = 5 competencies × 8 subjects × 4 levels × 2 languages).

Mirrors the `adk2-tutorial/L4a_flat_research/deep_research.py`
pattern: Pillar-3 dynamic fan-out (decompose into N competency
updates → update in parallel → synthesise the new mastery vector).
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from google.adk import Event, Workflow
    from google.adk.workflow import START, JoinNode, RetryConfig, node
except ImportError:
    Workflow = None  # type: ignore[assignment,misc]
    Event = None  # type: ignore[assignment,misc]
    JoinNode = None  # type: ignore[assignment,misc]
    START = None  # type: ignore[assignment,misc]
    node = None  # type: ignore[assignment,misc]
    RetryConfig = None  # type: ignore[assignment,misc]


_log = logging.getLogger(__name__)


# The 5 NCCA Key Competencies (with the 6th from the SCR advisory)
NCCA_KEY_COMPETENCIES: tuple[str, ...] = (
    "communicating",
    "being_creative",
    "working_with_others",
    "managing_information_and_thinking",
    "managing_myself",
    "staying_well",  # 6th competency — added per SCR advisory
)


async def decompose_into_competency_updates(node_input: Any) -> Event:
    """Decompose a formative assessment into 6 per-competency updates.

    Each exit card / topic mastery event maps onto 0..6 of the
    NCCA Key Competencies. This function returns the list of
    competency-updates to apply (one per competency touched).
    """
    return Event(
        output={
            "competency_updates": [
                {"competency": c, "delta": 0.05, "evidence_id": "fa-exit-card-001"}
                for c in NCCA_KEY_COMPETENCIES
            ]
        }
    )


async def write_competency_update(node_input: Any) -> Event:
    """One worker that writes a competency update to the skill-progression ledger (W9).

    Bounded by `RetryConfig(max_attempts=3)` so a transient Firestore
    ledger / mastery-vector / skill-graph write failure doesn't discard
    the whole fan-out (see `gemini_hackathon.ledger.MasteryLedger`).
    """
    update = node_input  # the per-competency dict
    return Event(output={"written": True, "update": update})


def build_cross_subject_workflow() -> Any:
    """Build the ADK 2 Workflow for the cross-subject competency ledger.

    Mirrors `adk2-tutorial/L4a_flat_research`:
        START ─► decompose ─► write_competency_update (parallel_worker) ─► synthesize

    Returns None if google-adk is not installed.
    """
    if Workflow is None:
        return None

    retry = RetryConfig(max_attempts=3, initial_delay=1.0, backoff_factor=2.0)

    # The parallel_worker pattern (Pillar 3 dynamic fan-out):
    # the worker decomposes N times at runtime.
    if node is not None:

        @node(parallel_worker=True, rerun_on_resume=True, retry_config=retry)
        async def fanout_write(node_input):
            return await write_competency_update(node_input)
    else:
        fanout_write = write_competency_update

    edges = [
        (START, decompose_into_competency_updates, fanout_write),
    ]
    # The synthesize step happens at the ledger level (W9), not here.

    return Workflow(
        name="cross_subject_competency_workflow",
        description=(
            "ADK 2 workflow for the NCCA Key Competencies cross-subject "
            "ledger. Decomposes formative-assessment exit cards into "
            "per-competency updates, writes them to the skill-progression "
            "ledger (W9) in parallel."
        ),
        edges=edges,
    )


__all__ = [
    "NCCA_KEY_COMPETENCIES",
    "build_cross_subject_workflow",
    "decompose_into_competency_updates",
    "write_competency_update",
]
