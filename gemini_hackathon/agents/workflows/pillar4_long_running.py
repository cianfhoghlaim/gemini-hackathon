"""gemini_hackathon.agents.workflows.pillar4_long_running — Pillar 4 (Long-running + Human-in-the-Loop).

Lifted from `monstertix/agent/concert/nightly.py` (the `check_front`
RequestInput interrupt) and adapted: the canonical pattern for a
marking-review workflow that needs teacher approval before finalising a
borderline grade.

The 3 components:
  - `ResumabilityConfig`: at-least-once retries on resume (preserved
    across deploys / crashes / container restarts).
  - `LongRunningFunctionTool`: a tool that returns immediately with
    "pending" and resumes when a teacher approves.
  - `RequestInputInterrupt`: the interrupt that pauses the workflow
    and waits for a teacher decision.

Used by:
  - The marking-grader workflow (W7) when the borderline criterion
    matches a teacher-approval rule.
  - The certificate pipeline (W14) for the UNOFFICIAL → OFFICIAL
    approval step.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class ResumabilityConfig:
    """The at-least-once retry + checkpoint config (per ADK 2)."""

    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    backoff_factor: float = 2.0
    checkpoint_after_each_step: bool = True


@dataclass
class RequestInputInterrupt:
    """The interrupt payload sent to the human reviewer."""

    prompt: str = "Approve this grade?"
    options: tuple[str, ...] = ("approve", "reject", "edit")
    default: str = "approve"
    timeout_seconds: int = 3600  # 1 hour — teacher can review asynchronously


@dataclass(frozen=True)
class Pillar4LongRunningWorkflow:
    """The configured long-running + human-in-the-loop workflow."""

    resumability: ResumabilityConfig = field(default_factory=ResumabilityConfig)
    interrupt: RequestInputInterrupt = field(default_factory=RequestInputInterrupt)


async def build_long_running_workflow(config: Pillar4LongRunningWorkflow) -> Any:
    """Build the ADK 2 workflow with LongRunningFunctionTool + ResumabilityConfig."""
    try:
        from google.adk.tools import LongRunningFunctionTool
        from google.adk.apps.app import App, ResumabilityConfig as _ResumabilityConfig
    except ImportError:
        _log.warning("google-adk not installed; pillar4 returns None")
        return None

    async def request_teacher_review(question: str) -> dict:
        """The LongRunningFunctionTool entry point.

        Returns immediately with `status: "pending"`. The workflow is
        paused until a teacher approves / rejects / edits.
        """
        return {
            "status": "pending",
            "interrupt_id": f"req-{hash(question) & 0xFFFFFFFF:08x}",
            "options": config.interrupt.options,
        }

    return App(
        name="pillar4_long_running",
        resumbability=_ResumabilityConfig(
            max_attempts=config.resumability.max_attempts,
        ),
        tools=[LongRunningFunctionTool(func=request_teacher_review)],
    )


__all__ = [
    "ResumabilityConfig",
    "RequestInputInterrupt",
    "Pillar4LongRunningWorkflow",
    "build_long_running_workflow",
]
