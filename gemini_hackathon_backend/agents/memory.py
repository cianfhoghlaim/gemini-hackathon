"""gemini_hackathon_backend.agents.memory — env-gated ADK 2 memory service factory.

Phase 0 of the multi-stage plan (see AGENTS.md). Replaces the Letta-based
   `gemini_hackathon/agents/fleet/fleet_memory.py` with the canonical ADK 2
   pattern: one of three `BaseMemoryService` implementations selected by env.

Resolution order (first match wins):
  1. ``VertexAiMemoryBankService`` — production. Triggered when
     ``DEPLOYED_AGENT_ENGINE_ID`` is set. Uses the Vertex AI Agent Engine
     memory bank; LLM-extracted facts; per-``user_id`` scoping.
  2. ``MarkdownMemoryService`` — dev / offline / HF Spaces. Triggered when
     ``GH_MEMORY_DIR`` is set (default ``~/.gemini_hackathon/memory``).
     File-backed; one Markdown file per user. Implements the same
     ``BaseMemoryService`` 2-method interface.
  3. ``None`` — falls through to ``InMemoryMemoryService`` (ADK 2 default).
     Returned when neither env var is set (CI, fresh dev clone, offline tests).

Both service implementations share the ``BaseMemoryService`` contract:

  - ``add_session_to_memory(session: Session) -> None`` — persist the
    transcript + state for one session.
  - ``search_memory(app_name, user_id, query) -> SearchMemoryResponse`` —
    return matching memory entries as a list of ``MemoryEntry``.

The ADK 2 ``Runner`` handles both calls automatically when the service is
passed via the ``memory_service=`` constructor argument. The
``before_agent_callback`` in ``agents/ncca_panel.py`` triggers
``add_session_to_memory()`` after every completed turn so the bank stays
fresh.

Environment variables consumed:

  - ``GOOGLE_CLOUD_PROJECT`` (required for Vertex path; usually set by
    Cloud Run automatically)
  - ``GOOGLE_CLOUD_LOCATION`` (optional; defaults to ``us-central1``)
  - ``DEPLOYED_AGENT_ENGINE_ID`` (gates the Vertex path)
  - ``GH_MEMORY_DIR`` (gates the Markdown path; default
    ``~/.gemini_hackathon/memory``)
  - ``GH_MEMORY_USER`` (per-user override used by tests; default ``userx``)
"""

from __future__ import annotations

import logging
import os
import pathlib
from typing import Any

logger = logging.getLogger(__name__)


def build_memory_service() -> Any | None:
    """Return an ADK 2 ``BaseMemoryService`` based on env, or ``None``.

    Returns ``None`` when neither ``DEPLOYED_AGENT_ENGINE_ID`` nor
    ``GH_MEMORY_DIR`` is set — callers (the FastAPI app) pass this through
    to the ADK agent runner, which then falls back to the
    ``InMemoryMemoryService`` default.

    On ``ImportError`` (e.g. ADK not installed in a fresh test env), logs
    a warning and returns ``None`` so the backend can still boot.
    """
    agent_engine_id = os.environ.get("DEPLOYED_AGENT_ENGINE_ID", "").strip()
    # The Markdown path is opt-in (GH_MEMORY_DIR must be explicitly set).
    # The previous "~/.gemini_hackathon/memory" default made MarkdownMemoryService
    # the de-facto default in every dev env; this change makes the fallback
    # chain deterministic and explicit (production + dev with explicit opt-in
    # + none-set -> ADK InMemoryMemoryService default).
    memory_dir = os.environ.get("GH_MEMORY_DIR", "").strip()

    # Path 1 — Vertex AI Memory Bank (production).
    if agent_engine_id:
        try:
            from google.adk.memory import VertexAiMemoryBankService  # type: ignore[import-not-found]

            project = (
                os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
                or os.environ.get("GCP_PROJECT_ID", "").strip()
            )
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "").strip() or "us-central1"
            if not project:
                logger.warning(
                    "memory_service: DEPLOYED_AGENT_ENGINE_ID set but GOOGLE_CLOUD_PROJECT unset; "
                    "falling back to GH_MEMORY_DIR / in-memory"
                )
            else:
                service = VertexAiMemoryBankService(
                    project=project,
                    location=location,
                    agent_engine_id=agent_engine_id,
                )
                logger.info(
                    "memory_service: using VertexAiMemoryBankService "
                    "(project=%s, location=%s, agent_engine_id=%s)",
                    project, location, agent_engine_id,
                )
                return service
        except ImportError as exc:
            logger.warning(
                "memory_service: google.adk.memory.VertexAiMemoryBankService not importable (%s); "
                "falling back", exc,
            )
        except Exception as exc:
            logger.warning(
                "memory_service: VertexAiMemoryBankService init failed (%s); falling back", exc,
            )

    # Path 2 — MarkdownMemoryService (dev / offline).
    if memory_dir:
        try:
            from gemini_hackathon.memory.markdown import MarkdownMemoryService  # type: ignore[import-not-found]

            service = MarkdownMemoryService(root=memory_dir)
            logger.info(
                "memory_service: using MarkdownMemoryService (root=%s)",
                memory_dir,
            )
            return service
        except ImportError as exc:
            logger.warning(
                "memory_service: gemini_hackathon.memory.markdown.MarkdownMemoryService "
                "not importable (%s); falling back", exc,
            )

    # Path 3 — caller falls through to ADK's InMemoryMemoryService default.
    logger.info(
        "memory_service: neither DEPLOYED_AGENT_ENGINE_ID nor GH_MEMORY_DIR set; "
        "falling back to InMemoryMemoryService (ADK default)"
    )
    return None


def memory_user_id() -> str:
    """Return the per-user id used by the memory service.

    Reads ``GH_MEMORY_USER`` (default ``"userx"``). Kept as a helper so
    the agents + tests don't read the env directly.
    """
    return os.environ.get("GH_MEMORY_USER", "userx").strip() or "userx"


def memory_root() -> pathlib.Path | None:
    """Return the on-disk root for the Markdown memory service.

    Reads ``GH_MEMORY_DIR`` (default: not set). Returns ``None`` when unset
    (caller decides whether to skip the Markdown path).
    """
    raw = os.environ.get("GH_MEMORY_DIR", "").strip()
    if not raw:
        return None
    return pathlib.Path(raw).expanduser()