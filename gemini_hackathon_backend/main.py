"""gemini_hackathon_backend/main.py — FastAPI entrypoint hosting the NCCA agent.

T1 #8 — wires `build_ncca_panel_agent()` + `add_adk_fastapi_endpoint(...)`
into a real FastAPI app at `/`. In dev (`GOOGLE_API_KEY` absent) the
real `LlmAgent.canonical_model` would fail at call-time, so the smoke
test in `tests/test_adk_agui_envelope.py` uses a stubbed LlmAgent.
This module is the production-style entrypoint; the tests verify the
lower-level AG-UI contract without booting this server.

Also exposes a tiny `GET /healthz` for Cloud Run health probes (the
`add_adk_fastapi_endpoint` only handles the AG-UI SSE stream; health
probes need a separate route).

Run:
    GEMINI_API_KEY=... uvicorn gemini_hackathon_backend.main:app --host 0.0.0.0 --port 8000

Or run inside the existing dev container — the same `gemini-hackathon`
artifact-registry image that hosts `gemini-hackathon-journey` can host
this, since both are FastAPI + ADK + the same venv.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_app():
    """Build the FastAPI app hosting the ADK AG-UI bridge for the NCCA panel agent.

    Lazy imports so the module loads even when `google-adk` or `ag-ui-adk`
    aren't importable (e.g. in CI or when running unit tests that don't
    need the runtime).
    """
    from fastapi import FastAPI

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            warnings.simplefilter("ignore", UserWarning)
            from google.adk.agents import LlmAgent  # noqa: F401  (validated by the runtime startup)
            from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint, AGUIToolset

            from gemini_hackathon_backend.agents.ncca_panel import (
                build_ncca_panel_agent,
                cite_pdf,
                fetch_highlight,
                list_ncca_pdfs,
            )
    except ImportError as exc:
        logger.warning(
            "build_app: google.adk / ag-ui-adk not importable (%s); the AG-UI bridge will be unavailable. "
            "Run `pip install google-adk ag-ui-adk` to enable.",
            exc,
        )
        app = FastAPI(title="gemini-hackathon-backend (stub)")

        @app.get("/healthz")
        async def _healthz():  # noqa: D401
            return {"status": "stub", "google_adk_available": False}

        return app

    app = FastAPI(title="gemini-hackathon-backend")

    @app.get("/healthz")
    async def _healthz():  # noqa: D401
        return {"status": "ok"}

    # The NCCA panel agent: 3 server-side tools (cite_pdf, fetch_highlight,
    # list_ncca_pdfs) + the AGUIToolset for client-side tools (when a CopilotKit
    # React client connects, it can register its own tools).
    llm_agent = build_ncca_panel_agent(
        tools=[cite_pdf, fetch_highlight, list_ncca_pdfs, AGUIToolset()],
    )
    adk_wrapper = ADKAgent(
        adk_agent=llm_agent,
        app_name="gemini_hackathon_ncca_panel",
        user_id="default_user",
        use_in_memory_services=True,
    )
    add_adk_fastapi_endpoint(
        app,
        adk_wrapper,
        path="/",
    )
    return app


app = build_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
