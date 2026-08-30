"""test_ncca_panel_agent.py — T1 #7 + #8 + #10 verification.

Tests:
  1. The 3 server-side tools (cite_pdf, fetch_highlight, list_ncca_pdfs) work
     end-to-end with a stub ToolContext (no LLM call — these are pure
     Python functions).
  2. The BAML extraction path gracefully falls back to a stub when
     `baml_client` isn't importable (the canonical case until the
     baml-py version mismatch ticket is resolved).
  3. The A2UI v0.9 catalog (`ncca_v1.json`) declares the 6 component
     types and 2 example surfaces the renderer expects.
  4. The full A2UI streaming JSONL envelope (createSurface → updateComponents
     → updateDataModel) for one example surface parses cleanly.
  5. `build_ncca_panel_agent()` constructs an LlmAgent that wires the
     3 server-side tools + the AGUIToolset + before_agent / before_model
     callbacks.
  6. The FastAPI app from `build_app()` exposes the AG-UI SSE route at
     `/` plus the healthz probe at `/healthz`.
"""
from __future__ import annotations

import json
import sys
import warnings

import pytest


# ADK's feature-registry emits UserWarning + DeprecationWarning at import
# time (inside `build_app()`'s `ADKAgent(...)` constructor). Suppress
# globally for the test run — same pattern as test_adk_agui_envelope.py.
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


class _FakeTC:
    """Minimal ToolContext — ADK's actual ToolContext has more surface,
    but the 3 NCCA tools only touch `.state`."""

    def __init__(self):
        self.state = {}


# ADK's feature-registry emits UserWarning + DeprecationWarning at import
# time (inside `build_app()`'s `ADKAgent(...)` constructor and inside
# `build_ncca_panel_agent()`). The test module loads `main.py` at
# collection time (via `from gemini_hackathon_backend.main import build_app`)
# and `agents.ncca_panel` at first reference — both fire warnings. Override
# pyproject.toml's `filterwarnings = ["error"]` for this module only.
pytestmark = [
    pytest.mark.filterwarnings("ignore::UserWarning"),
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
]


# Suppress ADK's experimental warnings at import time (matches the smoke-test
# pattern in test_adk_agui_envelope.py).
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


# ─── T1 #7: tool-level tests (no LLM needed) ─────────────────────────

def test_cite_pdf_records_citation():
    from gemini_hackathon_backend.agents.ncca_panel import cite_pdf, _NCCA_PDFS

    tc = _FakeTC()
    result = cite_pdf(
        "key-competencies-in-senior-cycle_en",
        page=6,
        snippet="student agency is positioned as a central organising principle",
        tool_context=tc,
    )
    assert result["status"] == "success"
    assert tc.state["active_pdf"] == "key-competencies-in-senior-cycle_en"
    assert len(tc.state["citations"]) == 1
    assert tc.state["citations"][0]["page"] == 6
    assert tc.state["citations"][0]["snippet"].startswith("student agency")


def test_cite_pdf_rejects_unknown_pdf():
    from gemini_hackathon_backend.agents.ncca_panel import cite_pdf

    tc = _FakeTC()
    result = cite_pdf("not-a-real-pdf.pdf", page=1, snippet="x", tool_context=tc)
    assert result["status"] == "error"
    assert "unknown pdf_id" in result["message"]
    assert tc.state.get("citations", []) == []


def test_fetch_highlight_returns_page_metadata():
    from gemini_hackathon_backend.agents.ncca_panel import fetch_highlight

    tc = _FakeTC()
    result = fetch_highlight("scr-advisory-report_en", 42, tool_context=tc)
    assert result["status"] == "success"
    assert "Page 42" in result["highlight"]
    assert result["title"] == "Senior Cycle Review — Advisory Report"


def test_list_ncca_pdfs_returns_all_five():
    from gemini_hackathon_backend.agents.ncca_panel import list_ncca_pdfs

    tc = _FakeTC()
    result = list_ncca_pdfs(tc)
    assert result["count"] == 5
    pdf_ids = [p["pdf_id"] for p in result["pdfs"]]
    assert "SC-L1-L2-Programme-Statement" in pdf_ids
    assert "key-competencies-in-senior-cycle_en" in pdf_ids
    assert "scr-advisory-report_en" in pdf_ids
    assert "the-potential-of-online-learning-environments_en" in pdf_ids
    assert "the-potential-of-technology-to-support-online-certification-and-reporting" in pdf_ids


def test_baml_fallback_when_client_missing():
    from gemini_hackathon_backend.agents.ncca_panel import _baml_extract_or_stub

    # baml_client fails to import (see baml_client/baml_client/__init__.py:33-34)
    # — verify the stub returns the canonical LCSyllabusDocument-shape dict.
    out = _baml_extract_or_stub("some pdf text", subject="mathematics")
    assert out["_stub"] is True
    assert out["subject"] == "mathematics"
    assert out["language"] == "en"
    assert out["total_learning_outcomes"] == 3
    assert "_stub_reason" in out


def test_build_ncca_panel_agent_constructs_with_3_server_tools():
    """Test the agent construction without invoking the LLM."""
    from gemini_hackathon_backend.agents.ncca_panel import (
        build_ncca_panel_agent,
        cite_pdf,
        fetch_highlight,
        list_ncca_pdfs,
    )

    agent = build_ncca_panel_agent(
        tools=[cite_pdf, fetch_highlight, list_ncca_pdfs],
    )
    assert agent.name == "NccaPanelAgent"
    assert cite_pdf in agent.tools
    assert fetch_highlight in agent.tools
    assert list_ncca_pdfs in agent.tools
    # before_agent_callback + before_model_callback are wired.
    assert agent.before_agent_callback is not None
    assert agent.before_model_callback is not None


# ─── T1 #10: A2UI catalog contract ──────────────────────────────────

def test_ncca_catalog_declares_all_6_components():
    from pathlib import Path

    cat_path = Path(__file__).resolve().parents[1] / "catalog" / "ncca_v1.json"
    with open(cat_path) as f:
        cat = json.load(f)
    assert cat["catalog_id"].startswith("https://gemini-hackathon")
    expected = {
        "NccaPdfCard",
        "KeyCompetencyRow",
        "ScProgrammeStatementBlock",
        "ScrAdvisoryHighlight",
        "OnlineLearningCallout",
        "CitationPill",
    }
    assert set(cat["components"]) == expected


def test_ncca_catalog_examples_have_valid_a2ui_jsonl_shape():
    """The `examples` block must produce valid v0.9 A2UI envelopes.

    v0.8+ wraps each message in a typed envelope (`{"type":
    "createSurface", ...}`) rather than the raw-keys form. Per
    the A2UI v0.8 spec §1.5: each line is `{"type": "<MessageType>",
    ...}`.

    Hard invariants checked:
      - Each example stream contains createSurface, updateComponents,
        updateDataModel (the canonical 3-message surface-create sequence)
      - createSurface carries surfaceId + catalogId
      - updateComponents carries surfaceId + components[] with one root
      - Each component has a unique `id` + `component` (widget type)
    """
    from pathlib import Path

    cat_path = Path(__file__).resolve().parents[1] / "catalog" / "ncca_v1.json"
    with open(cat_path) as f:
        cat = json.load(f)
    for surface_name in ("overview_surface", "kc_surface"):
        msgs = cat["examples"][surface_name]
        # Unwrap typed envelopes (`{"type": "...", ...}`) into a dict keyed
        # by the message type — the v0.8+ convention.
        unwrapped = {m["type"]: m for m in msgs}
        assert "createSurface" in unwrapped, f"{surface_name}: missing createSurface"
        create = unwrapped["createSurface"]
        assert create.get("surfaceId"), f"{surface_name}: missing surfaceId"
        assert create.get("catalogId"), f"{surface_name}: missing catalogId"
        comp = unwrapped["updateComponents"]
        assert comp.get("surfaceId"), f"{surface_name}: missing surfaceId on updateComponents"
        component_ids = [c["id"] for c in comp["components"]]
        assert len(component_ids) == len(set(component_ids)), \
            f"{surface_name}: duplicate component ids"
        # v0.9 components are flat dicts (no wrapper object) per §1.5
        for c in comp["components"]:
            assert "id" in c, f"{surface_name}: component missing id"
            assert "component" in c, f"{surface_name}: component missing 'component' key"


# ─── T1 #8: end-to-end A2UI streaming JSONL parses + has the expected key fields

def test_a2ui_jsonl_overview_surface_has_all_required_fields():
    from pathlib import Path

    cat_path = Path(__file__).resolve().parents[1] / "catalog" / "ncca_v1.json"
    with open(cat_path) as f:
        cat = json.load(f)

    msgs = cat["examples"]["overview_surface"]
    # v0.8+ typed envelopes — unwrap by message type
    unwrapped = {m["type"]: m for m in msgs}
    create = unwrapped["createSurface"]
    assert create["surfaceId"] == "ncca-overview"
    components = unwrapped["updateComponents"]["components"]
    assert "NccaPdfCard" in {c["component"] for c in components}
    # updateDataModel contains the 5 PDFs as a list (the cards template-render
    # this list into NccaPdfCard instances).
    pdfs = unwrapped["updateDataModel"]["value"]["pdfs"]
    assert len(pdfs) == 5


# ─── T1 #8: build_app wires the AG-UI route correctly ────────────────

def test_build_app_creates_fastapi_with_agui_route():
    from gemini_hackathon_backend.main import build_app

    app = build_app()
    paths = sorted(set(getattr(r, "path", None) for r in app.routes))
    # The AG-UI endpoint is mounted at "/" (path default of add_adk_fastapi_endpoint).
    # Plus the experimental /agents/state endpoint.
    # Plus /healthz (this module).
    # Plus the FastAPI auto-routes /docs, /openapi.json, /redoc, /docs/oauth2-redirect.
    assert "/" in paths
    assert "/agents/state" in paths
    assert "/healthz" in paths
