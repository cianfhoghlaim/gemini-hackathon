"""session_service.py — the Journey orchestrator's session service.

Mirrors `docs/adk-examples/way-back-home/level_2/backend/api/routes/chat.py`
+ `support-memory-lab/r3_last_month/`: chooses between `VertexAiSessionService`
(when `AGENT_ENGINE_ID` is set) and `InMemorySessionService` (offline /
dev path). Always falls back gracefully so a workshop host running without
the Memory Bank setup still gets a working orchestrator.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class _OfflineSessionService:
    """Minimal in-process SessionService that implements the subset of
    the ADK 2 SessionService interface the orchestrator actually uses
    (`create_session`, `get_session`, `append_event`, `close_session`).

    Used in offline mode when `google-adk` isn't installed or no
    Agent Engine / database is configured — keeps the Journey runnable
    end-to-end without any GCP credentials.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._next_id = 0

    def create_session(self, *, user_id: str, app_name: str, **kwargs: Any) -> Any:
        from types import SimpleNamespace

        self._next_id += 1
        session_id = f"offline-{self._next_id}"
        session = SimpleNamespace(
            id=session_id,
            user_id=user_id,
            app_name=app_name,
            events=[],
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, *, session_id: str, user_id: str, app_name: str, **kwargs: Any) -> Any:
        return self._sessions.get(session_id)

    def append_event(self, session, event: Any) -> None:
        if hasattr(session, "events") and session.events is not None:
            session.events.append(event)

    def close_session(self, session) -> None:
        if session.id in self._sessions:
            del self._sessions[session.id]


def make_session_service() -> Any:
    """Return the configured ADK 2 session service.

    Order of preference:
      1. `VertexAiSessionService` — persistent, per-workshop, requires
         Agent Engine setup (DEPLOYED_AGENT_ENGINE_ID)
      2. `DatabaseSessionService` — persistent SQLite file (good enough
         for a local workshop; `gemini_hackathon/session/schema.py` already
         has the SQL schema patterns burned in)
      3. `InMemorySessionService` — the always-available fallback
      4. `_OfflineSessionService` — bundled in-process fallback for
         environments where `google-adk` cannot be imported (e.g. the
         pre-existing google-adk/gradio pydantic version conflict documented
         in `docs/KNOWN_ISSUES.md` makes `uv sync` fail, so the dev
         environment runs without `google-adk`)

    Returns an object with the ADK 2 SessionService interface
    (`create_session`, `get_session`, `append_event`, `close_session`).
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    agent_engine_id = os.environ.get("DEPLOYED_AGENT_ENGINE_ID", "")

    if project_id and agent_engine_id:
        try:
            from google.adk.sessions import VertexAiSessionService

            svc = VertexAiSessionService(project=project_id, agent_engine_id=agent_engine_id)
            logger.info(
                "session_service: using VertexAiSessionService (Agent Engine %s)", agent_engine_id
            )
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
    except ImportError:
        logger.debug(
            "session_service: google.adk not importable (no DatabaseSessionService available)"
        )
    except Exception as exc:
        logger.warning(
            "session_service: DatabaseSessionService init failed (%s); using in-memory", exc
        )

    try:
        from google.adk.sessions import InMemorySessionService

        svc = InMemorySessionService()
        logger.info("session_service: using InMemorySessionService (no persistence)")
        return svc
    except ImportError:
        logger.debug(
            "session_service: google.adk not importable (no InMemorySessionService available); using bundled offline stub"
        )

    svc = _OfflineSessionService()
    logger.info("session_service: using bundled _OfflineSessionService (google.adk not importable)")
    return svc


__all__ = ["make_session_service"]
