"""agent.py — the ADK 2 SourcingCopilot.

Phase 2 of the GCP-first refactor. An ADK 2 agent that walks the
workshop host through deploying + running the sourcing pipeline. Built
on the canonical ADK 2 patterns (per `docs/adk-examples/adk2-tutorial/
L0_first_agent/` + `L1_graph_basics/` + `way-back-home/level_1/`):

  - A `root_agent` of `Agent` type with the copilot's overall instruction
  - 3 `FunctionTool` children (the 3 sub-agents' capabilities — each is
    a tool the root agent can call)
  - The same Gemini 3.5 Flash model as the journey orchestrator

The 3 sub-agent roles (one per FunctionTool):
  1. `SourcingStatusAgent` — answers "what's sourced? / how many
     normalised? / any failures?" Calls `get_status()` + `list_artefacts()`.
  2. `ExcludeDocumentAgent` — answers "should I exclude this?" / marks a
     doc excluded. Calls `mark_excluded(sha256, reason)`.
  3. `DeploymentAgent` — answers "what should I deploy next? / run the
     sourced step? / which services are deployed?". Calls
     `recommend_next_steps()` + `trigger_step()` +
     `list_cloud_run_services()` + `list_scheduled_jobs()`.

Usage:
    python -m gemini_hackathon.journey.sourcing_copilot.cli          # interactive REPL
    python -m gemini_hackathon.journey.sourcing_copilot.cli --status  # one-shot summary
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


# Default model — same as the journey orchestrator's Level 1-5.
DEFAULT_MODEL = os.environ.get("JOURNEY_COPILOT_MODEL", "gemini-3.5-flash")


def build_copilot_agent(model: str = DEFAULT_MODEL):
    """Construct the ADK 2 `Agent` for the SourcingCopilot.

    Lazily imports `google.adk` (the SDK may not be importable in the
    offline path — the copilot's REPL still works against an in-process
    fallback that doesn't need the SDK; this is the same pattern
    `gemini_hackathon/journey/level_0_pick_subnation/app.py` uses).
    """
    try:
        from google.adk.agents import Agent
        from google.adk.tools import FunctionTool
    except ImportError:
        logger.warning(
            "build_copilot_agent: google.adk not importable — copilot REPL will fall back to "
            "direct tool-call surface (the same offline path every other journey module uses)"
        )
        return None

    from gemini_hackathon.journey.sourcing_copilot import tools as _tools

    # The root agent's instruction is the workshop host's first impression
    # of the copilot — keep it short and directed at the host's daily actions.
    return Agent(
        name="sourcing_copilot",
        model=model,
        description=(
            "The British Isles Journey's sourcing-pipeline copilot. Reads the "
            "9-row status board, recommends the next step, lists Cloud Run "
            "services + Cloud Scheduler jobs, and marks docs excluded on "
            "request. Lives at the workshop host's elbow."
        ),
        instruction=(
            "You are the workshop host's sourcing-pipeline copilot. You help them:\n"
            "  1. See what's been sourced, normalised, BAML-extracted, OCR-consensus-done,\n"
            "     mastery-updated, and asset-generated (the 9-row status table).\n"
            "  2. Decide what to deploy next (recommend the single next step that\n"
            "     moves the workshop closest to 'ready for Level 1').\n"
            "  3. Mark documents excluded when they shouldn't be in scope\n"
            "     (one of: out_of_scope, corrupted, duplicate, superseded,\n"
            "     language_unsupported).\n"
            "  4. See what Cloud Run services + Cloud Scheduler jobs are deployed.\n\n"
            "Always answer in the host's language (English by default). Prefer\n"
            "the one-shot tool calls (--status, recommend_next_steps) over\n"
            "multi-turn dialog. Be concise: no preamble, no fluff.\n"
        ),
        tools=[
            FunctionTool(_tools.get_status),
            FunctionTool(_tools.list_artefacts),
            FunctionTool(_tools.mark_excluded),
            FunctionTool(_tools.list_cloud_run_services),
            FunctionTool(_tools.list_scheduled_jobs),
            FunctionTool(_tools.trigger_step),
            FunctionTool(_tools.recommend_next_steps),
        ],
    )


def build_runner(agent):
    """Build the ADK 2 `Runner` for the copilot (in-memory runner for the REPL).

    Returns None if `google.adk` is not importable.
    """
    try:
        from google.adk import Runner
        from google.adk.sessions import InMemorySessionService

        return Runner(
            agent=agent,
            app_name="sourcing_copilot",
            session_service=InMemorySessionService(),
            auto_create_session=True,
        )
    except ImportError:
        return None


__all__ = [
    "DEFAULT_MODEL",
    "build_copilot_agent",
    "build_runner",
]
