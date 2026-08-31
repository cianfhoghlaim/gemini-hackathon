"""memory_service.py — long-term learner memory via Vertex AI Memory Bank.

Mirrors `docs/adk-examples/support-memory-lab/r3_last_month/`:
`VertexAiMemoryBankService` writes the participant's Level 4 + Level 5
outputs to a per-event Memory Bank so cross-workshop learner continuity
("your last workshop was about sine rule; today we're starting cosine
rule") is preserved across Cloud Run cold starts.

When `AGENT_ENGINE_ID` is unset (the offline + dev path), returns `None`
and every caller falls back to "memory not wired" — a deliberate
non-fatal degradation, not a hard error.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def make_memory_service() -> Any | None:
    """Return the configured Memory Bank service (or None if unavailable).

    Returns `None` in offline / dev / no-Agent-Engine mode — every caller
    should branch on `if memory_service is not None:` rather than raising.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    agent_engine_id = os.environ.get("DEPLOYED_AGENT_ENGINE_ID", "")

    if not (project_id and agent_engine_id):
        logger.info("memory_service: skipped (DEPLOYED_AGENT_ENGINE_ID unset — see codelab)")
        return None

    try:
        from google.adk.memory import VertexAiMemoryBankService

        svc = VertexAiMemoryBankService(project=project_id, agent_engine_id=agent_engine_id)
        logger.info(
            "memory_service: using VertexAiMemoryBankService (Agent Engine %s)", agent_engine_id
        )
        return svc
    except Exception as exc:
        logger.warning("memory_service: VertexAiMemoryBankService init failed (%s)", exc)
        return None


__all__ = ["make_memory_service"]
