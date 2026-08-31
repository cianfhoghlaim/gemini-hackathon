"""test_agent.py — the `build_copilot_agent()` factory + tool-binding.

Tests:

  - `build_copilot_agent()` returns the ADK 2 `Agent` (or None when
    `google.adk` is not installed)
  - The 7 tools are registered as `FunctionTool`s
  - `build_runner()` returns the ADK 2 `Runner` (or None when adk is
    not installed)
  - `DEFAULT_MODEL` is the canonical "gemini-3.5-flash"

The pyproject.toml `filterwarnings = ["error", ...]` policy treats
warnings as errors. The `google.adk` package emits a `DeprecationWarning`
(from `BaseAgentConfig`) at import time. We use `pytest.warns()` (or
`warnings.catch_warnings`) to capture it so the import doesn't fail
the test. The pyproject `ignore::DeprecationWarning:google.adk.*`
pattern should already cover this — but Python attributes the warning
to `typing_extensions` (via `@warnings.warn` decorator), so we catch
it explicitly to be safe.
"""

from __future__ import annotations

import warnings

import pytest


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the offline mode for every test in this module."""
    monkeypatch.setenv("BAML_TEST_MODE", "true")
    monkeypatch.delenv("JOURNEY_COPILOT_MODEL", raising=False)


@pytest.fixture(autouse=True)
def _suppress_adk_deprecation() -> None:
    """Suppress the `google.adk` `BaseAgentConfig` deprecation warning.

    The warning is emitted at ADK import time but attributed to
    `typing_extensions.py:3125` (the `@warnings.warn` decorator), so
    pyproject's `ignore::DeprecationWarning:google.adk.*` pattern
    doesn't always match. We catch + ignore it here.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message=".*BaseAgentConfig.*",
        )
        yield


def test_default_model_is_canonical() -> None:
    """`DEFAULT_MODEL` is "gemini-3.5-flash" (overridable via env var)."""
    from gemini_hackathon.journey.sourcing_copilot.agent import DEFAULT_MODEL

    assert DEFAULT_MODEL == "gemini-3.5-flash"


def test_default_model_respects_env_override() -> None:
    """The `JOURNEY_COPILOT_MODEL` env var overrides `DEFAULT_MODEL`."""
    import importlib

    monkeypatch_env = pytest.MonkeyPatch()
    monkeypatch_env.setenv("JOURNEY_COPILOT_MODEL", "custom-model-xyz")
    try:
        module = importlib.reload(
            importlib.import_module("gemini_hackathon.journey.sourcing_copilot.agent")
        )
        assert module.DEFAULT_MODEL == "custom-model-xyz"
    finally:
        monkeypatch_env.undo()
        # Reload the module one more time so the env var reset
        # propagates to DEFAULT_MODEL — otherwise subsequent tests
        # inherit the overridden value.
        importlib.reload(importlib.import_module("gemini_hackathon.journey.sourcing_copilot.agent"))


def test_build_copilot_agent_returns_agent_or_none() -> None:
    """`build_copilot_agent()` returns the ADK 2 Agent OR None when adk is unavailable."""
    from gemini_hackathon.journey.sourcing_copilot.agent import build_copilot_agent

    agent = build_copilot_agent()
    # Either we get the real Agent, or None (when google.adk is missing).
    if agent is not None:
        assert agent.name == "sourcing_copilot"
        assert agent.model == "gemini-3.5-flash"
        assert hasattr(agent, "tools")
        # The 7 tools should be bound.
        assert len(agent.tools) == 7


def test_build_runner_returns_runner_or_none() -> None:
    """`build_runner(agent)` returns the ADK 2 Runner OR None when adk is missing."""
    from gemini_hackathon.journey.sourcing_copilot.agent import (
        build_copilot_agent,
        build_runner,
    )

    agent = build_copilot_agent()
    if agent is not None:
        runner = build_runner(agent)
        if runner is not None:
            assert runner.agent is agent


def test_agent_instruction_mentions_workshop_host() -> None:
    """The agent's instruction explicitly addresses the workshop host."""
    from gemini_hackathon.journey.sourcing_copilot.agent import build_copilot_agent

    agent = build_copilot_agent()
    if agent is not None:
        instruction = agent.instruction
        assert "workshop host" in instruction
        # The 5 closed-vocabulary reasons for exclusion are listed.
        for reason in (
            "out_of_scope",
            "corrupted",
            "duplicate",
            "superseded",
            "language_unsupported",
        ):
            assert reason in instruction


def test_agent_tools_match_canonical_list() -> None:
    """The 7 tools bound to the agent match the canonical list in tools.__all__."""
    from gemini_hackathon.journey.sourcing_copilot import tools as tools_module
    from gemini_hackathon.journey.sourcing_copilot.agent import build_copilot_agent

    agent = build_copilot_agent()
    if agent is None:
        pytest.skip("google.adk not installed — skipping tool-binding assertion")

    # The ADK 2 FunctionTool wraps the function — we check that every
    # canonical tool's function name appears in the bound tool set.
    bound_fn_names = {getattr(t, "name", None) or getattr(t, "__name__", None) for t in agent.tools}
    for canonical_name in tools_module.__all__:
        # FunctionTool usually sets `.name` to the underlying fn's __name__
        canonical_fn = getattr(tools_module, canonical_name)
        underlying_name = getattr(canonical_fn, "__name__", canonical_name)
        assert underlying_name in bound_fn_names, (
            f"canonical tool {canonical_name} (fn name={underlying_name}) "
            f"not in agent tools: {bound_fn_names}"
        )
