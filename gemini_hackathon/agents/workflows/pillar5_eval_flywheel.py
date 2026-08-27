"""gemini_hackathon.agents.workflows.pillar5_eval_flywheel — Pillar 5 (Eval + Flywheel).

Lifted from `loop-lab-table/` (the world.py + adk eval + adk optimize
patterns) and adapted: the canonical flywheel is a 5-stage loop that
runs every 24h to (1) harvest new exit cards from production, (2)
score them with `adk eval` + the per-stage custom metric, (3) GEPA-
rewrite the agent instruction from scored failures, (4) ship the
rewrite, (5) re-evaluate to confirm no regressions.

Used by:
  - gemini_hackathon.agents.stages.cross_subject (the competency
    mastery flywheel)
  - The marking-grader (W7) for the weekly instruction rewrite.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Pillar5EvalFlywheel:
    """The configured eval + flywheel loop."""

    eval_dataset_path: str = "data/eval/<stage>.evalset.json"
    custom_metric: str = "world_<stage>_cited_and_correct"
    max_iterations: int = 10
    min_improvement: float = 0.05  # 5% relative improvement required to ship
    schedule: str = "daily"  # "daily" | "weekly" | "monthly"


async def build_eval_flywheel(config: Pillar5EvalFlywheel) -> Any:
    """Build the eval flywheel orchestrator.

    Returns None if `adk eval` / `adk optimize` is unavailable.
    """
    try:
        # The actual orchestrator would shell out to `adk eval` + `adk optimize`.
        # Stub: just return a dataclass with the config + a `run()` method.
        from google.adk import Agent
    except ImportError:
        _log.warning("google-adk not installed; pillar5 returns None")
        return None

    class _FlywheelOrchestrator:
        def __init__(self, cfg: Pillar5EvalFlywheel):
            self.cfg = cfg
            self.iteration = 0

        async def run(self) -> dict:
            """Run one iteration of the flywheel.

            The real implementation would:
              1. Pull new exit cards from production (the W9 ledger)
              2. Run `adk eval` against the eval dataset
              3. Score with the custom metric
              4. If improvement < cfg.min_improvement, return early
              5. Otherwise run `adk optimize` (GEPA)
              6. Ship the rewritten instruction
              7. Re-evaluate

            Stub returns a no-op dict.
            """
            self.iteration += 1
            return {
                "iteration": self.iteration,
                "metric": self.cfg.custom_metric,
                "status": "no-op stub",
            }

    return _FlywheelOrchestrator(config)


__all__ = ["Pillar5EvalFlywheel", "build_eval_flywheel"]
