"""Shared pytest fixtures for the gemini_hackathon test suite.

The fixtures defined here are the canonical test-side counterparts
to the production code under :mod:`gemini_hackathon`. Every fixture
follows the ``dignified-python-312`` standards:

* Absolute imports (``from gemini_hackathon.X import Y``).
* Narrow exception handling (no bare ``except:``).
* Explicit ``tmp_path`` for filesystem fixtures (no hard-coded paths).
* ``monkeypatch`` for env-var + module-level state mutations.
* No real network access — every external surface is mocked.

Available fixtures:

* :func:`tmp_themes_dir` — a temp ``themes/`` directory with all 8
  jurisdiction + 5 safeguarding palette files.
* :func:`sample_palette` — a single canonical :class:`Palette` dict.
* :func:`mock_call_llm` — monkey-patches :func:`call_llm` with a
  canned :class:`LLMResponse` (no live API call).
* :func:`clean_env` — resets the canonical env vars for every test.
* :func:`fake_llm_router` — monkey-patches the LiteLLM router so
  :func:`call_llm` can exercise the 3-tier fallback semantics
  without real HTTP traffic.
* :func:`project_root` — the absolute path to the gemini_hackathon
  project root (the directory containing ``pyproject.toml``).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from gemini_hackathon.call_llm import LLMResponse, TierAttempt


# ---------------------------------------------------------------------------
# Markers — registered in pyproject.toml [tool.pytest.ini_options]
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register the project-specific markers used by the test suite.

    Pytest 8 requires markers to be declared up-front so the
    ``--strict-markers`` flag (set in ``pyproject.toml``) doesn't
    fail every test invocation.
    """
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a running network or "
        "live API (skipped by default; opt in with '-m integration')",
    )


# ---------------------------------------------------------------------------
# Project layout
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the absolute path to the gemini_hackathon project root.

    The project root is the directory that contains ``pyproject.toml``.
    This fixture is ``session``-scoped (computed once per pytest run).
    """
    # Walk up from this file until we find pyproject.toml.
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(
        f"Could not locate pyproject.toml from {current}; "
        "are you running pytest from inside the gemini_hackathon repo?"
    )


# ---------------------------------------------------------------------------
# Environment hygiene
# ---------------------------------------------------------------------------


#: Canonical env vars that the test suite should reset to known values.
#: Add new keys here when you introduce a new env-driven knob.
_RESET_ENV_KEYS: tuple[str, ...] = (
    "MINIMAX_API_KEY",
    "MINIMAX_BASE_URL",
    "MINIMAX_MODEL",
    "UNSLOTH_API_KEY",
    "UNSLOTH_BASE_URL",
    "UNSLOTH_MODEL",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "VERTEX_AI_MODEL",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",
    "MLFLOW_TRACKING_URI",
    "DEPLOYED_AGENT_ENGINE_ID",
    "GH_MEMORY_DIR",
    "GH_MEMORY_USER",
    "IDENTITY_JWT_SECRET",
    "DUCKDB_PATH",
    "LC_SUBJECTS_PATH",
    "LC_SUBJECTS_PATH_OVERRIDE",
    "FIRECRAWL_API_KEY",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset every canonical env var to `` None`` for each test.

    Pytest's ``monkeypatch`` automatically undoes every mutation
    after the test runs, so this fixture gives every test a clean
    slate without leaking state across tests.

    Yields:
        ``None`` — the fixture body is the side-effect of resetting
        env vars + removing cached router state.
    """
    for key in _RESET_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    # Also reset the cached LiteLLM router so the next call_llm
    # invocation rebuilds it from the (now-clean) env state.
    from gemini_hackathon import call_llm

    call_llm.reset_router()

    yield


# ---------------------------------------------------------------------------
# Theming fixtures
# ---------------------------------------------------------------------------


#: The canonical 13 theming sources (8 BI jurisdictions + 5 safeguarding).
ALL_SOURCE_KEYS: tuple[str, ...] = (
    # 8 jurisdictions
    "ncca.ie",
    "aqa.org.uk",
    "ocr.org.uk",
    "qualifications.pearson.com",
    "sqa.org.uk",
    "wjec.co.uk",
    "ccea.org.uk",
    "gov.im/education",
    # 5 safeguarding bodies
    "gov.ie/education",
    "gov.uk/dfe",
    "education.gov.scot",
    "gov.wales/education",
    "ccea.org.uk/safeguarding",
)

#: Source-key → jurisdiction mapping (mirrors JURISDICTION_SOURCES + SAFEGUARDING_SOURCES).
SOURCE_JURISDICTION: dict[str, str] = {
    # Jurisdictions (7) + England boards (3) = 10 top-level files
    "ncca.ie": "Ireland",
    "aqa.org.uk": "England",
    "ocr.org.uk": "England",
    "qualifications.pearson.com": "England",
    "sqa.org.uk": "Scotland",
    "wjec.co.uk": "Wales",
    "ccea.org.uk": "Northern Ireland",
    "gov.im/education": "Isle of Man",
    "gov.je/education": "Jersey",
    "gov.gg/education": "Guernsey",
    # Safeguarding (5)
    "gov.ie/education": "Ireland",
    "gov.uk/dfe": "England",
    "education.gov.scot": "Scotland",
    "gov.wales/education": "Wales",
    "ccea.org.uk/safeguarding": "Northern Ireland",
}


def _make_palette_payload(source_key: str) -> dict[str, Any]:
    """Build a deterministic palette payload for ``source_key``.

    Matches the schema produced by :func:`gemini_hackathon.theming.load_palette`.

    Uses :func:`hashlib.sha256` (not :func:`hash`) so the colour codes
    are reproducible across Python sessions — :func:`hash` is randomised
    per process unless ``PYTHONHASHSEED`` is pinned.
    """
    import hashlib

    jurisdiction = SOURCE_JURISDICTION[source_key]
    # Deterministic hex codes per source (reproducible across runs).
    digest = int.from_bytes(
        hashlib.sha256(source_key.encode("utf-8")).digest()[:3],
        byteorder="big",
    )
    primary = f"#{digest:06X}"
    secondary = f"#{(digest * 7 % (1 << 24)):06X}"
    accent = f"#{(digest * 11 % (1 << 24)):06X}"
    return {
        "sourceKey": source_key,
        "sourceName": f"{jurisdiction} — {source_key}",
        "jurisdiction": jurisdiction,
        "level": "LC" if jurisdiction == "Ireland" else "A-Level",
        "officialUrl": f"https://example.com/{source_key}",
        "palette": {
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
            "background": "#FFFFFF",
            "text": "#1A1A1A",
        },
        "typography": {
            "heading": "Test Sans",
            "body": "Test Serif",
        },
        "iconography": {
            "logoUrl": f"https://example.com/{source_key}/logo.png",
        },
        "flag": "🏳️" if jurisdiction == "England" else "🏴",
    }


@pytest.fixture
def tmp_themes_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temp ``themes/`` directory with all 13 palette files.

    Writes:

    * 8 ``*_palette.json`` files in the top-level dir (one per
      jurisdiction).
    * 5 ``*_palette.json`` files in the ``safeguarding/`` subdir
      (one per safeguarding body).

    Then patches :data:`gemini_hackathon.theming.THEMES_DIR` to
    point at the temp dir so :func:`load_palette` /
    :func:`list_all_palettes` resolve against the temp fixtures.

    Args:
        tmp_path: The pytest-provided temp directory.
        monkeypatch: The pytest monkeypatch fixture (auto-undone).

    Returns:
        The :class:`Path` to the new ``themes/`` directory.
    """
    from gemini_hackathon import theming

    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()

    # Jurisdiction + England-board palettes (each at its canonical path).
    # 7 jurisdictions + 3 England boards = 10 top-level jurisdiction files.
    jurisdiction_canonical = {
        "ncca.ie":     "ncca_palette.json",
        "aqa.org.uk":  "aqa_palette.json",
        "ocr.org.uk":  "ocr_palette.json",
        "qualifications.pearson.com": "pearson_palette.json",
        "sqa.org.uk":  "sqa_palette.json",
        "wjec.co.uk":  "wjec_palette.json",
        "ccea.org.uk": "ccea_palette.json",
        "gov.im/education": "iom_palette.json",
    }
    for source_key, filename in jurisdiction_canonical.items():
        (themes_dir / filename).write_text(
            json.dumps(_make_palette_payload(source_key), indent=2),
            encoding="utf-8",
        )

    # 2 Crown Dependencies (Jersey + Guernsey) under crown_dependencies/.
    (themes_dir / "crown_dependencies").mkdir()
    for stem, source_key in (("jersey", "gov.je/education"), ("guernsey", "gov.gg/education")):
        (themes_dir / "crown_dependencies" / f"{stem}_palette.json").write_text(
            json.dumps(_make_palette_payload(source_key), indent=2),
            encoding="utf-8",
        )

    # 5 safeguarding palettes live in the subdir.
    safeguarding_keys = (
        "gov.ie/education",
        "gov.uk/dfe",
        "education.gov.scot",
        "gov.wales/education",
        "ccea.org.uk/safeguarding",
    )
    safeguarding_dir = themes_dir / "safeguarding"
    safeguarding_dir.mkdir()
    safeguarding_filenames = {
        "gov.ie/education": "ie_dept_education_palette",
        "gov.uk/dfe": "uk_dfe_palette",
        "education.gov.scot": "scotland_gov_palette",
        "gov.wales/education": "wales_gov_palette",
        "ccea.org.uk/safeguarding": "ni_ccea_palette",
    }
    for source_key in safeguarding_keys:
        filename = safeguarding_filenames[source_key] + ".json"
        (safeguarding_dir / filename).write_text(
            json.dumps(_make_palette_payload(source_key), indent=2),
            encoding="utf-8",
        )

    # Patch THEMES_DIR so load_palette + list_all_palettes resolve
    # against the temp fixtures.
    monkeypatch.setattr(theming, "THEMES_DIR", themes_dir)

    return themes_dir


@pytest.fixture
def sample_palette() -> dict[str, Any]:
    """Return a canonical sample palette dict (for unit tests).

    The shape matches what :func:`load_palette` returns: a
    :class:`gemini_hackathon.theming.Palette` dataclass. Tests that
    need the raw JSON shape should use :func:`sample_palette_json`
    instead.
    """
    from gemini_hackathon.theming import Palette

    palette = Palette(
        source_key="ncca.ie",
        source_name="NCCA",
        jurisdiction="Ireland",
        level="LC",
        primary="#00733B",
        secondary="#0E2D5C",
        accent="#FFB81C",
        background="#FFFFFF",
        text="#1A1A1A",
        heading_font="Barlow",
        body_font="Georgia",
        logo_url="https://example.com/logo.png",
        flag="🇮🇪",
    )
    return {
        "palette": palette,
        "css_variables": palette.css_variables,
    }


@pytest.fixture
def sample_palette_json() -> dict[str, Any]:
    """Return a sample palette as a raw JSON dict (matches the on-disk schema)."""
    return _make_palette_payload("ncca.ie")


# ---------------------------------------------------------------------------
# LLM mocking
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_call_llm(monkeypatch: pytest.MonkeyPatch) -> Callable[..., LLMResponse]:
    """Monkey-patch :func:`call_llm` to return a canned :class:`LLMResponse`.

    Returns a callable ``fake`` so individual tests can override the
    canned response (e.g. to simulate a Tier 2 fallback or to make
    the canned call return malformed JSON for parsing tests).

    Usage::

        def test_x(mock_call_llm: Callable[..., LLMResponse]) -> None:
            mock_call_llm.return_content = '{"breakdown": []}'
            response = call_llm(messages=[...])
            assert response.content == '{"breakdown": []}'

    Returns:
        A :class:`_FakeCallLLM` instance with a mutable
        ``return_content`` attribute.
    """
    fake = _FakeCallLLM()

    def _patched(
        messages: Any,
        *,
        model_tier: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        return fake(messages, model_tier=model_tier, metadata=metadata)

    # Patch every module that imported ``call_llm`` at module-load
    # time — otherwise the idea agents would still call the real
    # ``call_llm`` (which requires litellm).
    monkeypatch.setattr("gemini_hackathon.call_llm.call_llm", _patched)
    for module_path in (
        "gemini_hackathon.agents.fleet.fleet_gateway",
        "gemini_hackathon.agents.ideas.marking_grader_workflow",
        "gemini_hackathon.agents.ideas.adaptive_tutor",
        "gemini_hackathon.agents.ideas.equivalency_generator",
        "gemini_hackathon.agents.ideas.curriculum_change_sensor",
    ):
        try:
            monkeypatch.setattr(f"{module_path}.call_llm", _patched)
        except AttributeError:  # pragma: no cover — module may be missing
            pass

    return fake


class _FakeCallLLM:
    """The backing object for the :func:`mock_call_llm` fixture.

    Attributes:
        return_content: The canned LLM response text. Defaults to a
            well-formed JSON document so parsing tests pass.
        call_count: The number of times the fake was invoked.
        call_history: The list of (messages, kwargs) tuples recorded.
    """

    def __init__(self) -> None:
        """Initialise the canned response + bookkeeping."""
        self.return_content: str = json.dumps(
            {
                "breakdown": [
                    {
                        "question_id": "Q1",
                        "awarded_marks": 8.0,
                        "max_marks": 10,
                        "justification": "Mostly correct",
                        "rubric_alignment": ["a"],
                        "confidence": 0.9,
                    }
                ]
            }
        )
        self.call_count: int = 0
        self.call_history: list[tuple[Any, dict[str, Any]]] = []

    def __call__(
        self,
        messages: Any,
        *,
        model_tier: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Record the invocation and return the canned response."""
        self.call_count += 1
        self.call_history.append((messages, {"model_tier": model_tier, "metadata": metadata}))
        return LLMResponse(
            content=self.return_content,
            model="minimax-m3",
            backend="minimax",
            tier=1,
            family="text_llm",
            role="default",
            latency_ms=42,
            tokens_in=128,
            tokens_out=64,
            cost_usd=0.0001,
            attempts=[TierAttempt(
                tier=1,
                family="text_llm",
                role="default",
                model="minimax-m3",
                backend="minimax",
                latency_ms=42,
                succeeded=True,
            )],
        )


# ---------------------------------------------------------------------------
# LiteLLM router mocking (for the tier-fallback tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_llm_router(monkeypatch: pytest.MonkeyPatch) -> "_FakeRouter":
    """Replace the LiteLLM router with a fully-deterministic fake.

    The fake lets individual tests decide which tier succeeds / fails
    via :attr:`_FakeRouter.tier_responses`. Use the per-tier response
    helpers (:meth:`_FakeRouter.fail_through_to` /
    :meth:`_FakeRouter.succeed_at`) to control the fallback semantics.

    Usage::

        def test_fallback(fake_llm_router: _FakeRouter) -> None:
            fake_llm_router.fail_through_to(tier=2, with_content="tier-2 reply")
            response = call_llm(messages=[{"role": "user", "content": "hi"}])
            assert response.tier == 2
            assert response.content == "tier-2 reply"
    """
    fake = _FakeRouter()
    monkeypatch.setattr("gemini_hackathon.call_llm._build_router", lambda: fake)
    return fake


class _FakeRouter:
    """A deterministic stand-in for the LiteLLM :class:`Router`.

    Attributes:
        tier_responses: A dict mapping ``tier_int`` (1/2/3) → either
            a string content (success) or an exception instance
            (failure).
        tier_call_count: A dict counting how many times each tier
            was invoked.
    """

    def __init__(self) -> None:
        """Initialise the router with all 3 tiers set to fail by default."""
        self.tier_responses: dict[int, str | BaseException] = {
            1: RuntimeError("Tier 1 simulated failure"),
            2: RuntimeError("Tier 2 simulated failure"),
            3: RuntimeError("Tier 3 simulated failure"),
        }
        self.tier_call_count: dict[int, int] = {1: 0, 2: 0, 3: 0}

    def succeed_at(self, tier: int, content: str) -> None:
        """Configure ``tier`` to succeed and return ``content``."""
        self.tier_responses[tier] = content

    def fail_through_to(self, tier: int, with_content: str) -> None:
        """Make every tier before ``tier`` fail, then succeed at ``tier``.

        Example::

            fake_router.fail_through_to(tier=2, with_content="tier-2 wins")
            # Tier 1 raises, Tier 2 returns the content.
        """
        for t in range(1, tier):
            self.tier_responses[t] = RuntimeError(f"Tier {t} simulated failure")
        self.succeed_at(tier, with_content)

    def completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Any:
        """Mimic `` ``litellm.Router.completion``.

        Maps the LiteLLM router model name (``"primary"`` /
        ``"fallback-1"`` / ``"fallback-2"``) back to a tier int.
        """
        tier_map = {"primary": 1, "fallback-1": 2, "fallback-2": 3}
        tier = tier_map[model]
        self.tier_call_count[tier] = self.tier_call_count.get(tier, 0) + 1

        response_or_exc = self.tier_responses[tier]
        if isinstance(response_or_exc, BaseException):
            raise response_or_exc

        # Return a minimal stand-in for litellm.ModelResponse.
        return _FakeModelResponse(content=response_or_exc)


class _FakeModelResponse:
    """A minimal stand-in for ``litellm.ModelResponse``.

    Only the attributes used by :func:`call_llm` are populated.
    """

    def __init__(self, content: str) -> None:
        """Initialise with the response content + dummy usage data."""
        self.choices: list[_FakeChoice] = [_FakeChoice(content)]
        self.usage: _FakeUsage = _FakeUsage()


class _FakeChoice:
    """The single :class:`Choice` row in the fake response."""

    def __init__(self, content: str) -> None:
        """Initialise with the canned message content."""
        self.message: _FakeMessage = _FakeMessage(content)


class _FakeMessage:
    """The assistant message in the fake response."""

    def __init__(self, content: str) -> None:
        """Initialise with the canned content."""
        self.content: str = content


class _FakeUsage:
    """The usage block on the fake response."""

    def __init__(self) -> None:
        """Initialise with zero token counts."""
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0


# ---------------------------------------------------------------------------
# Public re-exports for the tests that want a fully-decoupled LLM stub.
# ---------------------------------------------------------------------------


__all__ = [
    "ALL_SOURCE_KEYS",
    "SOURCE_JURISDICTION",
    "_FakeCallLLM",
    "_FakeRouter",
    "fake_llm_router",
    "mock_call_llm",
    "project_root",
    "sample_palette",
    "sample_palette_json",
    "tmp_themes_dir",
]


# Re-export the helpers so tests can do:
#   from tests.conftest import ALL_SOURCE_KEYS, _FakeRouter  # noqa: F401
# The `_` prefix on _FakeRouter is intentional (test-only API).