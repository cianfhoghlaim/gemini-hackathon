"""Tests for the real Google ADK agent integration (Phase 7).

Covers:
- build_adk_agent returns a real LlmAgent + InMemoryRunner (not None)
  when google-adk is installed.
- The 5 tools are wrapped and registered.
- The system prompt composition reflects every session field.
- render_agui_events produces the documented 13-event subset from a
  mocked ADK Event stream.
- The backend /api/agents/chat endpoint accepts a request and returns
  the documented event-list shape (when ADK is present).
- public_model_roster() never leaks dev-only entries.
"""

from __future__ import annotations

import json
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"google\.adk.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"typing_extensions.*")

from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# ADK integration
# ---------------------------------------------------------------------------


def test_adk_available_returns_true():
    """Skip if google-adk isn't installed in this venv."""
    from gemini_hackathon.agents.adk_gemini_agent import is_adk_available

    if not is_adk_available():
        pytest.skip("google-adk not installed")
    assert is_adk_available() is True


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_build_adk_agent_returns_real_llmagent_and_runner():
    from gemini_hackathon.agents.adk_gemini_agent import build_adk_agent

    if not __import__(
        "gemini_hackathon.agents.adk_gemini_agent", fromlist=["is_adk_available"]
    ).is_adk_available():
        pytest.skip("google-adk not installed")
    # Updated 2026-08-31 (Phase 6): pass wrap_in_app=False so the returned
    # object is the raw LlmAgent (not the ADK 2.7+ App wrapper, which has
    # name="gemini_hackathon" and no `.model` attribute).
    agent, runner = build_adk_agent(wrap_in_app=False)
    assert agent is not None
    assert runner is not None
    assert agent.name == "gemini_hackathon_agent"
    # The LlmAgent wraps the model string in a Gemini adapter.
    model = agent.model
    assert model is not None
    # 5 tools registered
    assert len(agent.tools) == 5
    tool_names = [t.name if hasattr(t, "name") else t.__name__ for t in agent.tools]
    for expected in (
        "lookup_outcome",
        "retrieve_resources",
        "find_similar_resources",
        "retrieve_safeguarding",
        "mark_answer",
    ):
        assert any(expected in n for n in tool_names), f"missing {expected} in {tool_names}"


def test_system_prompt_composes_every_session_field():
    from gemini_hackathon.agents.adk_gemini_agent import render_system_prompt

    p = render_system_prompt(
        subnation="ireland",
        subnation_flag="🇮🇪",
        awarding_body="NCCA",
        role="student",
        cycle="leaving_cycle",
        subjects=["Mathematics", "English"],
        safeguarding_policy="DEIS + Well-Being Policy Statement",
        palette_primary="#00733B",
        palette_heading="Merriweather",
    )
    # Every session field is present in the composed prompt.
    assert "ireland" in p
    assert "🇮🇪" in p
    assert "NCCA" in p
    assert "student" in p
    assert "leaving_cycle" in p
    assert "Mathematics, English" in p
    assert "DEIS + Well-Being Policy Statement" in p
    assert "#00733B" in p
    assert "Merriweather" in p


# ---------------------------------------------------------------------------
# AG-UI event rendering
# ---------------------------------------------------------------------------


def test_render_agui_events_handles_text_message():
    """A model content part with text becomes a TEXT_MESSAGE_CONTENT event."""
    from gemini_hackathon.agents.adk_gemini_agent import render_agui_events

    # Build a mock ADK Event with author='agent' + content.parts[0].text='hi'.
    ev = MagicMock()
    ev.author = "agent"
    part = MagicMock()
    part.text = "hello"
    ev.content.parts = [part]
    ev.function_calls = []

    events = render_agui_events([ev])
    assert any(e.type == "TEXT_MESSAGE_CONTENT" and e.data["text"] == "hello" for e in events)


def test_render_agui_events_handles_tool_calls():
    """A model event with function_calls becomes TOOL_CALL_START + TOOL_CALL_ARGS."""
    from gemini_hackathon.agents.adk_gemini_agent import render_agui_events

    ev = MagicMock()
    ev.author = "agent"
    ev.content.parts = []
    call = MagicMock()
    call.name = "lookup_outcome"
    call.id = "call_1"
    call.args = {"subnation": "ireland"}
    ev.function_calls = [call]

    events = render_agui_events([ev])
    types = [e.type for e in events]
    assert "TOOL_CALL_START" in types
    assert "TOOL_CALL_ARGS" in types


def test_render_agui_events_handles_tool_response():
    """A tool-response event (author != 'agent') becomes TOOL_CALL_RESULT."""
    from gemini_hackathon.agents.adk_gemini_agent import render_agui_events

    ev = MagicMock()
    ev.author = "lookup_outcome"
    fr = MagicMock()
    fr.id = "call_1"
    fr.response = {"outcome": "x"}
    ev.function_response = fr

    events = render_agui_events([ev])
    assert any(e.type == "TOOL_CALL_RESULT" for e in events)
    assert any(e.data["name"] == "lookup_outcome" for e in events)


# ---------------------------------------------------------------------------
# Backend /api/agents/chat endpoint (stub path; real ADK path requires keys)
# ---------------------------------------------------------------------------


def _start_backend(port: int):
    """Boot the backend on `port`, return (process, base_url)."""
    import socket
    import subprocess
    import time as _time

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "gemini_hackathon.backend",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return proc, base
        except OSError:
            _time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("backend did not start")


def _post(url: str, body: dict, timeout: float = 10.0):
    import urllib.request

    req = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read())


def test_agents_chat_returns_supported_event_types_in_stub():
    """Without ADK (or with empty message) the endpoint returns the AG-UI
    supported_event_types list so the client can render a stub event."""
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc, base = _start_backend(port)
    try:
        status, body = _post(f"{base}/api/agents/chat", {"message": ""})
        assert status == 200
        assert body["status"] == "stub"
        assert "events" in body
        # AG-UI protocol surface documented.
        assert "supported_event_types" in body
        # The 13-event subset the frontend consumes is documented.
        assert "RUN_STARTED" in body["supported_event_types"]
        assert "TEXT_MESSAGE_CONTENT" in body["supported_event_types"]
        assert "RUN_FINISHED" in body["supported_event_types"]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def test_agents_chat_runs_real_agent_when_adk_available():
    """When ADK is available, the endpoint returns 'ok' status with AG-UI
    events from a real LlmAgent + InMemoryRunner run.

    The LLM call may fail (no key) — in that case the endpoint returns
    'agent_error' status. Either is acceptable; the contract is that
    the endpoint runs the real agent and surfaces its outcome.
    """
    from gemini_hackathon.agents.adk_gemini_agent import is_adk_available

    if not is_adk_available():
        pytest.skip("google-adk not installed")

    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    proc, base = _start_backend(port)
    try:
        status, body = _post(
            f"{base}/api/agents/chat",
            {
                "message": "What does the syllabus say about kinematics?",
                "subnation": "ireland",
                "subnation_flag": "🇮🇪",
                "awarding_body": "NCCA",
                "role": "student",
                "cycle": "leaving_cycle",
                "subjects": ["Mathematics"],
            },
        )
        assert status == 200
        # Updated 2026-08-31 (Phase 6): the run_agent_turn status enum is
        # now 'ok' / 'error' / 'blocked' (was 'ok' / 'agent_error' / 'stub').
        assert body["status"] in ("ok", "error")
        assert "events" in body
        assert isinstance(body["events"], list)
        # The endpoint ran the real agent and surfaced its outcome via
        # the AG-UI subset — that is the contract.
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
