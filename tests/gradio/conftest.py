"""tests/gradio/conftest.py — shared fixtures for the Gradio studio tests.

Centralises the suppression of the Gradio 6.0 + Pydantic v2 + asyncio
deprecation warnings that fire when `build_app()` runs.
"""

from __future__ import annotations

import warnings

import pytest


@pytest.fixture(autouse=True)
def _suppress_gradio_deprecation() -> None:
    """Suppress warnings that fire when a Gradio studio's `build_app()` runs.

    The pyproject `filterwarnings = ["error", ...]` policy raises
    warnings as errors. We suppress:

      - The Gradio 6.0 `UserWarning` about `theme` + `css` kwargs moving to `launch()`.
      - The Pydantic v2 `DeprecationWarning` about class-based `config`.
      - The google.adk `BaseAgentConfig` `DeprecationWarning`.
      - The asyncio `ResourceWarning` about unclosed event loops / sockets
        (the async certificate pipeline handler runs an event loop per call).
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            message=r".*parameters have been moved from the Blocks constructor.*",
        )
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message=r".*class-based `config` is deprecated.*",
        )
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message=r".*BaseAgentConfig.*",
        )
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            message=r".*unclosed event loop.*",
        )
        warnings.filterwarnings(
            "ignore",
            category=ResourceWarning,
            message=r".*unclosed socket.*",
        )
        yield


@pytest.fixture(autouse=True)
def _offline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the canonical offline-mode env vars for every test."""
    monkeypatch.setenv("BAML_TEST_MODE", "true")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
