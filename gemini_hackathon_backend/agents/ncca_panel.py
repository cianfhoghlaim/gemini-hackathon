"""gemini_hackathon_backend/agents/ncca_panel.py — the NCCA policy panel agent.

T1 #7 of the ADK + A2UI build.

The first working ADK agent. Demonstrates the canonical ADK 2 pattern
(per `adk2-tutorial/L0_first_agent/` + `adk.dev/integrations/ag-ui/`):

  - An `LlmAgent` with `gemini-3.5-flash` (placeholder — tests stub it)
  - Three tools: `cite_pdf`, `fetch_highlight`, `list_ncca_pdfs`
  - `before_agent_callback` seeds `{subnation, learning_outcome, active_pdf}`
    into `ctx.state` from the AG-UI RunAgentInput
  - `before_model_callback` re-injects the state into the system prompt
    so the model stays grounded across turns (per the Wave Back Home
    pattern at `webflow.copilotkit.ai/blog/build-a-frontend-for-your-adk-agents-with-ag-ui`)

A2UI emission: the agent surfaces A2UI JSONL inside AG-UI `Raw` events
(per `a2ui.org/specification/v0.8-a2ui/`). The frontend's
`@copilotkit/a2ui-renderer` consumes those `Raw` events and streams the
JSONL into the panels. Without A2UI, the agent still answers normally —
A2UI is a strict enhancement, not a hard dependency.

The BAML integration (`b.ExtractCurriculumSyllabus`) is wrapped in a
try/except so the agent still works offline / when the BAML client isn't
built (the repo's `baml_client/baml_client/__init__.py` currently fails
on import — see `docs/ideas/sourcing_integration.md` + the BAML
compatibility ticket for the upstream fix). When BAML is available the
tool returns the structured extraction; when it isn't the tool returns
a deterministic stub dict with the same shape.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from gemini_hackathon_backend.catalog.a2ui_emitter import (
    record_a2ui_raw_event,
    wrap_a2ui_in_raw_event,
)
from gemini_hackathon_backend.observability import (
    log_mlflow_metric,
)

logger = logging.getLogger(__name__)


# The 5 NCCA policy PDFs are the canonical source of truth. Their metadata
# is duplicated from `data/ireland/ncca_policy/INDEX.yaml` (the journey
# orchestrator already reads from there). When a citation tool needs to
# look up a PDF, this table is the lookup.
_NCCA_PDFS: list[dict[str, str]] = [
    {
        "pdf_id": "SC-L1-L2-Programme-Statement",
        "title": "Leaving Certificate Framework — L1 & L2 Programme Statement",
        "blurb": "The statutory programme statement for Senior Cycle Leaving Certificate (L1 & L2).",
    },
    {
        "pdf_id": "key-competencies-in-senior-cycle_en",
        "title": "Key Competencies in Senior Cycle",
        "blurb": "The five Key Competencies designed to be developed across all Senior Cycle subjects.",
    },
    {
        "pdf_id": "scr-advisory-report_en",
        "title": "Senior Cycle Review — Advisory Report",
        "blurb": "6-year statutory review of Senior Cycle leading to recommendations on curriculum, assessment, and reporting.",
    },
    {
        "pdf_id": "the-potential-of-online-learning-environments_en",
        "title": "The Potential of Online Learning Environments",
        "blurb": "Explores how online learning environments can support Senior Cycle delivery and assessment.",
    },
    {
        "pdf_id": "the-potential-of-technology-to-support-online-certification-and-reporting",
        "title": "The Potential of Technology to Support Online Certification and Reporting",
        "blurb": "Investigates technology-enabled certification and reporting pathways for Senior Cycle outcomes.",
    },
]


def _find_pdf(pdf_id: str) -> dict[str, str] | None:
    return next((p for p in _NCCA_PDFS if p["pdf_id"] == pdf_id), None)


def _baml_extract_or_stub(pdf_text: str, subject: str = "") -> dict[str, Any]:
    """Run the BAML ExtractCurriculumSyllabus call when available; otherwise
    return a deterministic stub dict that matches the LCSyllabusDocument shape.

    The BAML client is currently broken in the dev env (baml-py version
    mismatch with the generated 0.222.0 client — see repo's
    `baml_client/baml_client/__init__.py:33-34`). We always try the real
    import first; the stub is a clean deterministic fallback.
    """
    try:
        from baml_client.sync_client import b  # type: ignore

        return b.ExtractCurriculumSyllabus(
            pdf_text=pdf_text, subject=subject, language="en"
        ).model_dump()
    except Exception as exc:
        return {
            "_stub": True,
            "_stub_reason": str(exc),
            "subject": subject,
            "language": "en",
            "module_topics": [
                {
                    "title": "(stubbed) Learning outcomes for " + subject,
                    "learning_outcomes": [
                        {"lo_id": "STUB-1", "title": f"Understand core concepts in {subject}"},
                        {"lo_id": "STUB-2", "title": f"Apply core concepts in {subject}"},
                        {"lo_id": "STUB-3", "title": f"Analyse relationships in {subject}"},
                    ],
                },
            ],
            "total_learning_outcomes": 3,
        }


# ---------------------------------------------------------------------------
# Tools — these are the callable surfaces the LLM can call.
# Per the ADK 2 recipe: every tool is a plain function with a docstring +
# type hints. ADK reads the signature and hands the model a tool-call
# declaration.
# ---------------------------------------------------------------------------


def cite_pdf(pdf_id: str, page: int, snippet: str, tool_context) -> dict[str, Any]:
    """Record a citation against an NCCA policy PDF.

    The snippet is the verbatim quote from the PDF (≤ 200 chars). ADK
    tracks the call's `tool_context.state["citations"]` so the
    journey orchestrator's before_agent_callback can include the citation
    count in the system prompt on the next turn.

    In addition to the normal JSON return, the tool appends a single A2UI
    v0.9 Raw event to `tool_context.state["a2ui_raw_events"]` carrying a
    `NccaPdfCard` surface so the frontend can render the citation as a
    clickable card. The session-end helper `_flush_a2ui_surfaces` drains
    that buffer.

    Args:
        pdf_id: The PDF identifier (one of `_NCCA_PDFS[*].pdf_id`).
        page: The 1-indexed page number within the PDF.
        snippet: The verbatim text being cited (≤ 200 chars).
        tool_context: Injected by ADK — the LLM/agent context handle.

    Returns:
        dict with `status` + `recorded` confirmation.
    """
    pdf = _find_pdf(pdf_id)
    if pdf is None:
        return {
            "status": "error",
            "message": f"unknown pdf_id {pdf_id!r}; must be one of {[p['pdf_id'] for p in _NCCA_PDFS]}",
        }

    citations = tool_context.state.get("citations", [])
    citations.append(
        {
            "pdf_id": pdf_id,
            "title": pdf["title"],
            "page": page,
            "snippet": snippet[:200],
        }
    )
    tool_context.state["citations"] = citations
    tool_context.state["active_pdf"] = pdf_id
    log_mlflow_metric("ncca_panel.cite_pdf.invocations", 1)
    logger.info("tool.cite_pdf", pdf_id=pdf_id, page=page, session_citations=len(citations))

    # Emit an A2UI v0.9 surface so the frontend's a2ui-renderer can paint a
    # `NccaPdfCard` next to the citation. The `data` field binds the
    # `CitationPill` props to a JSON-Pointer-resolved data model so future
    # `updateDataModel` operations can patch the snippet without having to
    # resend the whole tree.
    surface_id = f"ncca-citation-{pdf_id}"
    components = [
        {"id": "root", "component": "Column", "children": ["title", "card", "pill"]},
        {"id": "title", "component": "Text", "text": "Citation recorded", "variant": "h3"},
        {
            "id": "card",
            "component": "NccaPdfCard",
            "pdf_id": {"path": "pdf_id"},
            "title": {"path": "title"},
            "blurb": {"path": "blurb"},
        },
        {
            "id": "pill",
            "component": "CitationPill",
            "pdf_id": {"path": "pill_pdf_id"},
            "page": {"path": "pill_page"},
            "snippet": {"path": "pill_snippet"},
        },
    ]
    data = {
        "pdf_id": pdf_id,
        "title": pdf["title"],
        "blurb": pdf["blurb"],
        "pill_pdf_id": pdf_id,
        "pill_page": page,
        "pill_snippet": snippet[:200],
    }
    record_a2ui_raw_event(tool_context, wrap_a2ui_in_raw_event(surface_id, components, data))

    return {
        "status": "success",
        "recorded": {
            "pdf_id": pdf_id,
            "page": page,
            "snippet": snippet[:200],
        },
        "citation_count_this_session": len(citations),
    }


def fetch_highlight(pdf_id: str, page: int, tool_context) -> dict[str, Any]:
    """Return the highlight text for a specific PDF page.

    In production this would call `gemini_hackathon/journey/sourcing/cache.py:read_bytes`
    + a PDF-page-extractor. Offline this returns the metadata stub.

    Args:
        pdf_id: The PDF identifier.
        page: The page number to highlight.
        tool_context: Injected by ADK.

    Returns:
        dict with `status` + `highlight` text (or `page_not_found`).
    """
    pdf = _find_pdf(pdf_id)
    if pdf is None:
        return {"status": "error", "message": f"unknown pdf_id {pdf_id!r}"}
    log_mlflow_metric("ncca_panel.fetch_highlight.invocations", 1)
    logger.info("tool.fetch_highlight", pdf_id=pdf_id, page=page)
    return {
        "status": "success",
        "pdf_id": pdf_id,
        "title": pdf["title"],
        "page": page,
        "highlight": f"(stub) Page {page} of '{pdf['title']}'.",  # offline stub
    }


def list_ncca_pdfs(tool_context) -> dict[str, Any]:
    """List all 5 NCCA policy PDFs the agent can cite.

    Emits a `ncca-overview` A2UI surface so the frontend can show the
    complete policy corpus as a `NccaPdfCard` gallery in one go (rather
    than waiting for the model to call `cite_pdf` 5 times).

    Args:
        tool_context: Injected by ADK.

    Returns:
        dict with `count` + `pdfs` (list of {pdf_id, title, blurb} dicts).
    """
    tool_context.state["last_pdf_list_query_ts"] = "now"
    log_mlflow_metric("ncca_panel.list_ncca_pdfs.invocations", 1)
    logger.info("tool.list_ncca_pdfs", pdf_count=len(_NCCA_PDFS))

    # Emit the canonical "ncca-overview" surface — mirrors
    # `catalog/ncca_v1.json:examples.overview_surface`.
    surface_id = "ncca-overview"
    components = [
        {"id": "root", "component": "Column", "children": ["title", "pdf-list"]},
        {
            "id": "title",
            "component": "Text",
            "text": "NCCA Senior Cycle policy corpus",
            "variant": "h1",
        },
        {
            "id": "pdf-list",
            "component": "List",
            "children": ["pdf-card-template"],
            "direction": "vertical",
        },
        {
            "id": "pdf-card-template",
            "component": "NccaPdfCard",
            "title": {"path": "title"},
            "blurb": {"path": "blurb"},
            "pdf_id": {"path": "pdf_id"},
        },
    ]
    data = {"pdfs": list(_NCCA_PDFS)}
    record_a2ui_raw_event(tool_context, wrap_a2ui_in_raw_event(surface_id, components, data))

    return {"count": len(_NCCA_PDFS), "pdfs": _NCCA_PDFS}


# ---------------------------------------------------------------------------
# ADK 2 LlmAgent + before_agent / before_model callbacks.
# ---------------------------------------------------------------------------


NCCA_PANEL_INSTRUCTION = """You are the British Isles Journey's NCCA policy panel assistant.

You answer questions about the 5 NCCA Senior Cycle policy PDFs.

RULES:
  1. ALWAYS ground your answer in a citation. Before answering, call
     `cite_pdf(pdf_id, page, snippet)` with the verbatim text. The
     frontend renders the citation as a clickable link to the source PDF.
  2. If the user asks for a list of available policies, call
     `list_ncca_pdfs()` first and then offer to dive into any of them.
  3. If the user asks for a specific page quote, call
     `fetch_highlight(pdf_id, page)` to get the text, then summarise.
  4. Never invent a pdf_id or page number — only cite what the tools
     returned.
  5. Keep answers in plain text with a citation footer. Do not generate
     images (Level 5 does that with FIBO).
  6. When the user asks for an asset (infographic, summary card, or
     illustrative diagram) tied to an NCCA policy PDF, call
     `generate_asset(pdf_id, asset_type, topic)` to emit the
     `NccaPdfCard` A2UI surface that the studio renders as the
     end-to-end certificate-flow showcase at `/agents`.
"""


def generate_asset(
    pdf_id: str,
    asset_type: str,
    topic: str,
    tool_context,
) -> dict[str, Any]:
    """Emit an NccaPdfCard A2UI surface tied to one of the 5 NCCA policy PDFs.

    Phase E (`2026-08-31-submission-scope-realignment-v1`) — the 4th tool
    in the NCCA panel. Renders a `NccaPdfCard` next to the agent's text
    response so the certificate flow is end-to-end visible at `/agents`.

    Args:
        pdf_id: The PDF identifier (one of `_NCCA_PDFS[*].pdf_id`).
        asset_type: The asset kind — one of {"infographic", "summary",
            "diagram"}. Determines the title emoji + sub-blurb the
            `NccaPdfCard` displays.
        topic: The user-supplied topic the asset is being generated for
            (e.g. "Differentiation", "Senior Cycle Mathematics").
        tool_context: Injected by ADK.

    Returns:
        dict with `status` + `pdf_id` + `asset_type` + `topic` + the
        A2UI surface_id emitted.
    """
    pdf = _find_pdf(pdf_id)
    if pdf is None:
        return {
            "status": "error",
            "message": f"unknown pdf_id {pdf_id!r}; must be one of {[p['pdf_id'] for p in _NCCA_PDFS]}",
        }

    asset_label = {
        "infographic": "📊 Infographic",
        "summary": "📝 Summary",
        "diagram": "🗺 Diagram",
    }.get(asset_type, "Asset")

    tool_context.state["last_asset_request"] = {
        "pdf_id": pdf_id,
        "asset_type": asset_type,
        "topic": topic,
    }
    log_mlflow_metric("ncca_panel.generate_asset.invocations", 1)
    logger.info(
        "tool.generate_asset",
        pdf_id=pdf_id,
        asset_type=asset_type,
        topic=topic,
    )

    surface_id = f"ncca-asset-{pdf_id}-{asset_type}"
    components = [
        {"id": "root", "component": "Column", "children": ["heading", "card"]},
        {
            "id": "heading",
            "component": "Text",
            "text": f"{asset_label}: {topic}",
            "variant": "h2",
        },
        {
            "id": "card",
            "component": "NccaPdfCard",
            "pdf_id": {"path": "pdf_id"},
            "title": {"path": "title"},
            "blurb": {"path": "blurb"},
        },
    ]
    data = {
        "pdf_id": pdf_id,
        "title": pdf["title"],
        "blurb": f"{asset_label} on '{topic}' drawn from {pdf['title']}",
    }
    record_a2ui_raw_event(tool_context, wrap_a2ui_in_raw_event(surface_id, components, data))

    return {
        "status": "success",
        "pdf_id": pdf_id,
        "asset_type": asset_type,
        "topic": topic,
        "surface_id": surface_id,
    }


def _seed_participant_state(callback_context) -> None:
    """before_agent_callback — seed `{subnation, learning_outcome, active_pdf}`.

    ADK's before_agent_callback runs ONCE when the agent starts processing.
    We seed the per-participant state from the AG-UI RunAgentInput
    (passed in via `callback_context.invocation_context`).

    For NCCA panel the state needs the subnation (default "ireland" — the
    NCCA's jurisdiction) and a stub learning_outcome so the agent has a
    hook to reference if the user doesn't provide one.
    """
    # `callback_context.invocation_context` is the runtime context; ADK
    # exposes the AG-UI input via the same path as the user's message.
    # For now we seed defaults; a future iteration reads from the
    # AG-UI message's `state` payload (the frontend passes per-turn state).
    state = callback_context.state
    state.setdefault("subnation", "ireland")
    state.setdefault("learning_outcome", None)
    state.setdefault("active_pdf", None)
    state.setdefault("citations", [])


def _reinject_state_into_prompt(callback_context, llm_request) -> None:
    """before_model_callback — re-inject state into the system prompt.

    ADK's model client only sees `llm_request.config.system_instruction`.
    We prepend a JSON block with the current state so the model stays
    grounded across turns (per the Wave Back Home pattern).
    """
    state = callback_context.state
    payload = json.dumps(
        {
            "subnation": state.get("subnation"),
            "learning_outcome": state.get("learning_outcome"),
            "active_pdf": state.get("active_pdf"),
            "citations": state.get("citations", []),
        },
        indent=2,
    )
    prefix = (
        "You are the NCCA policy panel assistant. The user's current session state is:\n"
        f"{payload}\n"
        "Always cite a source before answering. Use cite_pdf() to record a citation.\n"
    )
    original = getattr(llm_request.config, "system_instruction", None)
    if original is None:
        return  # no system instruction to augment
    if hasattr(original, "parts") and original.parts:
        # AG-UI / Google-genai Content object
        original.parts[0].text = prefix + (original.parts[0].text or "")
    elif isinstance(original, str):
        llm_request.config.system_instruction = prefix + original


def build_ncca_panel_agent(model: str = "gemini-3.5-flash", *, tools: list | None = None) -> Any:
    """Construct the NCCA panel LlmAgent.

    `tools` defaults to the 3 NCCA-specific tools; pass `None` to use
    the ADKToolset + AGUIToolset (for HITL / client-tool scenarios).
    """
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", UserWarning)
        from google.adk.agents import LlmAgent

    if tools is None:
        tools = [cite_pdf, fetch_highlight, list_ncca_pdfs, generate_asset]

    return LlmAgent(
        name="NccaPanelAgent",
        model=model,
        instruction=NCCA_PANEL_INSTRUCTION,
        tools=tools,
        before_agent_callback=_seed_participant_state,
        before_model_callback=_reinject_state_into_prompt,
        after_agent_callback=_persist_session_to_memory,
    )


async def _persist_session_to_memory(callback_context) -> object:
    """Phase 0 — persist the completed session to the configured memory service.

    Fires after each completed turn. ADK 2's Runner handles the call to
    ``callback_context.add_session_to_memory()`` against whichever
    ``BaseMemoryService`` the agent runner was constructed with (set in
    ``gemini_hackathon_backend/main.py:build_memory_service()``).

    No-op when no memory service is configured (the default
    ``InMemoryMemoryService`` is still set up by the Runner, but
    ``add_session_to_memory`` on it is harmless).
    """
    try:
        await callback_context.add_session_to_memory()
    except Exception as exc:
        logger.warning(
            "ncca_panel: add_session_to_memory failed (%s); memory not persisted",
            exc,
        )
    return None


def _flush_a2ui_surfaces(tool_context) -> list[dict[str, Any]]:
    """Drain the per-turn A2UI Raw-event buffer from `tool_context.state`.

    Re-export of `gemini_hackathon_backend.catalog.a2ui_emitter.flush_a2ui_surfaces`
    so the agent module owns the public surface (callers don't have to
    import the catalog submodule directly).

    Args:
        tool_context: ADK `ToolContext` (or anything with a `.state` dict).

    Returns:
        A list of AG-UI `Raw` events recorded during the turn.
    """
    from gemini_hackathon_backend.catalog.a2ui_emitter import flush_a2ui_surfaces

    return flush_a2ui_surfaces(tool_context)


__all__ = [
    "NCCA_PANEL_INSTRUCTION",
    "_NCCA_PDFS",
    "_baml_extract_or_stub",
    "_find_pdf",
    "_flush_a2ui_surfaces",
    "_persist_session_to_memory",
    "_reinject_state_into_prompt",
    "_seed_participant_state",
    "build_ncca_panel_agent",
    "cite_pdf",
    "fetch_highlight",
    "generate_asset",
    "list_ncca_pdfs",
]
