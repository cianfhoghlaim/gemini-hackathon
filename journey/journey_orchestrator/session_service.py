"""session_service.py — the Journey orchestrator's session service.

Mirrors `docs/adk-examples/way-back-home/level_2/backend/api/routes/chat.py`
+ `support-memory-lab/r3_last_month/`: chooses between `VertexAiSessionService`
(when `AGENT_ENGINE_ID` is set) and `InMemorySessionService` (offline /
dev path). Always falls back gracefully so a workshop host running without
the Memory Bank setup still gets a working orchestrator.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def make_session_service() -> Any:
    """Return the configured ADK 2 session service.

    Order of preference:
      1. `VertexAiSessionService` — persistent, per-workshop, requires
         Agent Engine setup (DEPLOYED_AGENT_ENGINE_ID)
      2. `DatabaseSessionService` — persistent SQLite file (good enough
         for a local workshop; `gemini_hackathon/session/schema.py` already
         has the SQL schema patterns burned in)
      3. `InMemorySessionService` — the always-available fallback

    Returns an object with the ADK 2 SessionService interface (`create_session`,
    `get_session`, `append_event`, `close_session`).
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    agent_engine_id = os.environ.get("DEPLOYED_AGENT_ENGINE_ID", "")

    if project_id and agent_engine_id:
        try:
            from google.adk.sessions import VertexAiSessionService

            svc = VertexAiSessionService(project=project_id, agent_engine_id=agent_engine_id)
            logger.info("session_service: using VertexAiSessionService (Agent Engine %s)", agent_engine_id)
            return svc
        except Exception as exc:
            logger.warning(
                "session_service: VertexAiSessionService init failed (%s); falling back",
                exc,
            )

    try:
        from google.adk.sessions import DatabaseSessionService

        db_url = os.environ.get("JOURNEY_SESSION_DB_URL", "sqlite:///./data/journey_sessions.db")
        svc = DatabaseSessionService(db_url=db_url)
        logger.info("session_service: using DatabaseSessionService at %s", db_url)
        return svc
    except Exception as exc:
        logger.warning("session_service: DatabaseSessionService init failed (%s); using in-memory", exc)

    from google.adk.sessions import InMemorySessionService

    svc = InMemorySessionService()
    logger.info("session_service: using InMemorySessionService (no persistence)")
    return svc


__all__ = ["make_session_service"]


# Late import so the `os.environ` access is local to the call (and tests
# can monkeypatch the env without affecting module-level imports).
import os  # noqa: E402
