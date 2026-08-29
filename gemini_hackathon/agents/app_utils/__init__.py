"""gemini_hackathon.agents.app_utils — production wrappers around ADK primitives.

Lifted from the canonical google-adk starter-pack pattern (per
``research/agents/google-adk/app/agent.py`` + ``.../app/app_utils/telemetry.py``).

Public surface:
    - :func:`ensure_vertex_env` — set Vertex AI env vars before ADK init
    - :func:`setup_telemetry` — wire Cloud Trace + Cloud Logging + GCS NO_CONTENT
    - :func:`build_app` — wrap ``LlmAgent`` in the production ``App(...)`` shell
"""

from .telemetry import build_app, ensure_vertex_env, setup_telemetry

__all__ = ["build_app", "ensure_vertex_env", "setup_telemetry"]