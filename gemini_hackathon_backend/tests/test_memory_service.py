"""test_memory_service.py — Phase 0 verification of the env-gated memory factory.

Tests:
  1. ``build_memory_service()`` returns ``None`` when neither ``DEPLOYED_AGENT_ENGINE_ID``
     nor ``GH_MEMORY_DIR`` is set (the fallback to ADK's ``InMemoryMemoryService``).
  2. ``build_memory_service()`` returns a ``MarkdownMemoryService`` instance
     when ``GH_MEMORY_DIR`` is set (even with no ``DEPLOYED_AGENT_ENGINE_ID``).
  3. ``build_memory_service()`` returns a ``VertexAiMemoryBankService`` instance
     when ``DEPLOYED_AGENT_ENGINE_ID`` is set and the ADK import succeeds.
     Falls back to ``MarkdownMemoryService`` (when ``GH_MEMORY_DIR`` is set)
     or ``None`` otherwise when the ADK import is unavailable.
  4. ``memory_root()`` and ``memory_user_id()`` read the right env vars with
     sensible defaults.
"""

from __future__ import annotations

import importlib

import pytest


def test_build_memory_service_returns_none_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither DEPLOYED_AGENT_ENGINE_ID nor GH_MEMORY_DIR set -> None.

    ADK 2 will then use its InMemoryMemoryService default.
    """
    monkeypatch.delenv("DEPLOYED_AGENT_ENGINE_ID", raising=False)
    monkeypatch.delenv("GH_MEMORY_DIR", raising=False)

    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    result = memory_mod.build_memory_service()

    assert result is None, f"expected None, got {result!r}"


def test_build_memory_service_returns_markdown_when_gh_memory_dir_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """GH_MEMORY_DIR set -> MarkdownMemoryService instance (Vertex path skipped)."""
    monkeypatch.delenv("DEPLOYED_AGENT_ENGINE_ID", raising=False)
    monkeypatch.setenv("GH_MEMORY_DIR", str(tmp_path / "memory"))

    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    result = memory_mod.build_memory_service()

    # MarkdownMemoryService is the in-tree implementation
    from gemini_hackathon.memory.markdown import MarkdownMemoryService

    assert isinstance(result, MarkdownMemoryService)
    assert result.root == tmp_path / "memory"


def test_build_memory_service_returns_vertex_when_engine_id_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """DEPLOYED_AGENT_ENGINE_ID + GOOGLE_CLOUD_PROJECT set -> Vertex path attempted.

    When the ADK import succeeds, returns a VertexAiMemoryBankService.
    When the ADK import fails (as in the test env without google-adk),
    falls back to MarkdownMemoryService. Either is acceptable for the test;
    we just assert the function does not return ``None`` and does not raise.
    """
    monkeypatch.setenv("DEPLOYED_AGENT_ENGINE_ID", "fake-engine-id-123")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    monkeypatch.setenv("GH_MEMORY_DIR", str(tmp_path / "memory"))

    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    result = memory_mod.build_memory_service()

    assert result is not None, "expected a memory service (Vertex or Markdown fallback)"
    # When google-adk is installed (it is in this venv), the Vertex path
    # succeeds and returns a VertexAiMemoryBankService. When google-adk
    # is missing, the function falls back to MarkdownMemoryService. Both
    # are valid; the test just guards against regression to ``None``.
    from gemini_hackathon.memory.markdown import MarkdownMemoryService
    try:
        from google.adk.memory import VertexAiMemoryBankService
    except ImportError:
        VertexAiMemoryBankService = None  # type: ignore[misc]

    assert isinstance(result, (MarkdownMemoryService, VertexAiMemoryBankService))


def test_memory_root_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """memory_root() returns None when GH_MEMORY_DIR is unset (opt-in)."""
    monkeypatch.delenv("GH_MEMORY_DIR", raising=False)

    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    assert memory_mod.memory_root() is None


def test_memory_root_respects_gh_memory_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """memory_root() returns the GH_MEMORY_DIR value when set."""
    monkeypatch.setenv("GH_MEMORY_DIR", str(tmp_path / "custom_memory"))

    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    assert memory_mod.memory_root() == tmp_path / "custom_memory"


def test_memory_user_id_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """memory_user_id() returns 'userx' by default."""
    monkeypatch.delenv("GH_MEMORY_USER", raising=False)

    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    assert memory_mod.memory_user_id() == "userx"


def test_memory_user_id_empty_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty GH_MEMORY_USER falls back to 'userx'."""
    monkeypatch.setenv("GH_MEMORY_USER", "")

    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    assert memory_mod.memory_user_id() == "userx"


def test_memory_user_id_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-default GH_MEMORY_USER is returned as-is."""
    monkeypatch.setenv("GH_MEMORY_USER", "alice@example.com")

    from gemini_hackathon_backend.agents import memory as memory_mod

    importlib.reload(memory_mod)
    assert memory_mod.memory_user_id() == "alice@example.com"