"""gemini_hackathon_backend.agents.gemini_deep_research — Google Deep Research tool.

Per the openspec change
`2026-09-06-adk-gemini-deep-research-control-plane-v1`. Adds the
Gemini Deep Research API as an ADK ``FunctionTool`` to the
gemini_hackathon_backend Cloud Run service.

The tool calls the Gemini Deep Research API
(https://ai.google.dev/gemini-api/docs/deep-research) and streams
the per-step ``interactions`` to AG-UI consumers.
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator

GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
DEFAULT_DEEP_RESEARCH_MODEL = "gemini-2.5-pro-deep-research"


async def deep_research(query: str, *, max_sources: int = 10) -> dict[str, Any]:
    """Run a Gemini Deep Research query and return a structured report.

    Args:
        query: The long-form research query.
        max_sources: Maximum sources to consult.

    Returns:
        ``dict`` with ``success``, ``synthesized_report``,
        ``interactions``, ``citations``, ``key_findings``,
        ``urls_visited``, ``tokens_used``, ``error``.
    """
    api_key = os.environ.get(GOOGLE_API_KEY_ENV)
    if not api_key:
        return {
            "success": False,
            "query": query,
            "synthesized_report": "",
            "interactions": [],
            "citations": [],
            "key_findings": [],
            "urls_visited": 0,
            "tokens_used": None,
            "backend_used": "gemini_deep_research",
            "error": f"{GOOGLE_API_KEY_ENV} not configured",
        }

    model = os.environ.get("BROWSER_GEMINI_DEEP_RESEARCH_MODEL", DEFAULT_DEEP_RESEARCH_MODEL)

    try:
        from google import genai
    except ImportError as exc:
        return {
            "success": False,
            "query": query,
            "error": f"google-genai not installed: {exc}",
        }

    client = genai.Client(api_key=api_key)
    interactions: list[dict[str, Any]] = []
    synthesized_chunks: list[str] = []
    citations: list[dict[str, Any]] = []
    key_findings: list[str] = []
    urls_visited = 0
    error: str | None = None

    try:
        response = await client.aio.deep_research(
            model=model,
            query=query,
            max_urls=max_sources,
            stream=True,
        )

        async for event in response:
            kind = getattr(event, "kind", None)
            if kind == "interaction":
                interactions.append(
                    {
                        "interaction_id": getattr(event, "interaction_id", None),
                        "action": getattr(event, "action", None),
                        "target": getattr(event, "target", None),
                        "rationale": getattr(event, "rationale", None),
                    }
                )
            elif kind == "url_visited":
                urls_visited += 1
            elif kind == "content_chunk":
                synthesized_chunks.append(getattr(event, "text", ""))
            elif kind == "citation":
                citations.append(
                    {
                        "url": getattr(event, "url", None),
                        "title": getattr(event, "title", None),
                        "claim": getattr(event, "claim", None),
                    }
                )
            elif kind == "key_finding":
                key_findings.append(getattr(event, "text", ""))
            elif kind == "error":
                error = getattr(event, "message", "unknown error")

    except Exception as exc:
        error = str(exc)

    return {
        "success": error is None,
        "query": query,
        "synthesized_report": "".join(synthesized_chunks),
        "interactions": interactions,
        "citations": citations,
        "key_findings": key_findings,
        "urls_visited": urls_visited,
        "tokens_used": None,
        "backend_used": "gemini_deep_research",
        "model": model,
        "error": error,
    }


async def stream_interactions(
    query: str, *, max_sources: int = 10
) -> AsyncIterator[dict[str, Any]]:
    """Yield Gemini Deep Research interaction events as they happen."""
    api_key = os.environ.get(GOOGLE_API_KEY_ENV)
    if not api_key:
        yield {"kind": "error", "message": f"{GOOGLE_API_KEY_ENV} not configured"}
        return

    from google import genai

    client = genai.Client(api_key=api_key)
    model = os.environ.get("BROWSER_GEMINI_DEEP_RESEARCH_MODEL", DEFAULT_DEEP_RESEARCH_MODEL)

    response = await client.aio.deep_research(
        model=model,
        query=query,
        max_urls=max_sources,
        stream=True,
    )

    async for event in response:
        yield {
            "kind": getattr(event, "kind", None),
            "interaction_id": getattr(event, "interaction_id", None),
            "action": getattr(event, "action", None),
            "target": getattr(event, "target", None),
            "rationale": getattr(event, "rationale", None),
            "text": getattr(event, "text", None),
            "url": getattr(event, "url", None),
            "title": getattr(event, "title", None),
            "claim": getattr(event, "claim", None),
            "message": getattr(event, "message", None),
        }
