"""Tests for the gemini_hackathon.call_llm dual-profile router."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Env setup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in (
        "MODEL_PROFILE", "UNSLOTH_BASE_URL", "UNSLOTH_API_KEY",
        "GOOGLE_CLOUD_PROJECT", "GEMINI_API_KEY",
        "MINIMAX_API_KEY", "MINIMAX_BASE_URL",
    ):
        monkeypatch.delenv(k, raising=False)
    from gemini_hackathon import call_llm
    call_llm.reset_router()


# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------


def test_call_llm_imports_resolve():
    from gemini_hackathon.call_llm import (
        HACKATHON_TIERS,
        DEV_TIERS,
        TIER_RETRY_BUDGETS,
        BACKOFF_BASE_SECONDS,
        TIER_TIMEOUT_SECONDS,
        call_llm,
        estimate_cost_usd,
        normalise_messages,
        parse_model_string,
        reset_router,
        ModelExcludedError,
    )
    assert HACKATHON_TIERS == (("text_llm", "default"), ("text_llm", "fallback"))
    assert DEV_TIERS == (
        ("text_llm", "default"),
        ("text_llm", "fallback"),
        ("text_llm", "dev_primary"),
    )
    assert TIER_RETRY_BUDGETS["default"] == 2


def test_active_profile_default(monkeypatch):
    monkeypatch.delenv("MODEL_PROFILE", raising=False)
    from gemini_hackathon.call_llm import _active_profile
    assert _active_profile() == "hackathon"


def test_active_profile_dev(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", "dev")
    from gemini_hackathon.call_llm import _active_profile
    assert _active_profile() == "dev"


def test_active_profile_unknown_falls_back(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", "garbage")
    from gemini_hackathon.call_llm import _active_profile
    assert _active_profile() == "hackathon"


# ---------------------------------------------------------------------------
# Exclusion guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [
    "@cf/meta/llama-3.1-8b-instruct",
    "@cf/mistralai/mistral-7b-instruct-v0.1",
    "qwen3-coder-32b-instruct",
    "openai/qwen3-coder-anything",
])
def test_excluded_models_rejected(bad):
    from gemini_hackathon.call_llm import _assert_model_allowed, ModelExcludedError
    with pytest.raises(ModelExcludedError):
        _assert_model_allowed(bad)


@pytest.mark.parametrize("good", [
    "gemini-3.5-flash",
    "gemma-4-26b-a4b",
    "minimax-m3",
    "vertex_ai/gemini-3.5-flash",
    "openai/gemma-4-26b-a4b",
    "openai/qwen3-vl-8b",
])
def test_allowed_models_accepted(good):
    from gemini_hackathon.call_llm import _assert_model_allowed
    _assert_model_allowed(good)  # should not raise


# ---------------------------------------------------------------------------
# ValueError on empty messages
# ---------------------------------------------------------------------------


def test_empty_messages_raises():
    from gemini_hackathon.call_llm import call_llm
    with pytest.raises(ValueError):
        call_llm([])


# ---------------------------------------------------------------------------
# Profile gating via the resolver
# ---------------------------------------------------------------------------


def test_hackathon_profile_default_resolves_to_gemini():
    from gemini_hackathon.models import model_for
    entry = model_for("text_llm", "default", profile="hackathon")
    assert entry is not None
    assert entry.key == "gemini-3.5-flash"
    assert entry.backend == "vertex"


def test_hackathon_profile_fallback_resolves_to_gemma():
    from gemini_hackathon.models import model_for
    entry = model_for("text_llm", "fallback", profile="hackathon")
    assert entry is not None
    assert entry.key == "gemma-4-26b-a4b"
    assert entry.backend == "unsloth_studio"


def test_dev_profile_third_tier_resolves_to_minimax(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", "dev")
    from gemini_hackathon.models import model_for
    entry = model_for("text_llm", "dev_primary", profile="dev")
    assert entry is not None
    assert entry.key == "minimax-m3"


def test_minimax_not_in_hackathon_profile(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", "hackathon")
    from gemini_hackathon.models import MODEL_REGISTRY
    hack = MODEL_REGISTRY.for_profile("hackathon")
    keys = [e.key for e in hack]
    assert "minimax-m3" not in keys


def test_qwen3_vl_in_hackathon_ocr_vision():
    from gemini_hackathon.models import MODEL_REGISTRY
    hack = MODEL_REGISTRY.for_profile("hackathon")
    ocr_keys = [e.key for e in hack if e.family == "ocr_vision"]
    assert "qwen3-vl-8b" in ocr_keys


# ---------------------------------------------------------------------------
# Pin mode (single (family, role) call)
# ---------------------------------------------------------------------------


def test_pin_mode_unknown_family_raises():
    from gemini_hackathon.call_llm import call_llm
    with pytest.raises(ValueError):
        call_llm(
            [{"role": "user", "content": "hi"}],
            family="text_llm",
            role="not_a_real_role",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_normalise_messages_validates():
    from gemini_hackathon.call_llm import normalise_messages
    out = normalise_messages([
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello."},
    ])
    assert len(out) == 2
    assert out[0]["role"] == "system"

    with pytest.raises(ValueError):
        normalise_messages([{"role": "user"}])

    with pytest.raises(ValueError):
        normalise_messages([{"role": "tool", "content": "x"}])


def test_estimate_cost_usd_rounds_to_six():
    from gemini_hackathon.call_llm import estimate_cost_usd
    cost = estimate_cost_usd("gemini-3.5-flash", tokens_in=1_000_000, tokens_out=500_000)
    # 1000 * 0.000075 + 500 * 0.0003 = 0.075 + 0.150 = 0.225
    assert cost == 0.225


def test_estimate_cost_usd_local_model_is_free():
    from gemini_hackathon.call_llm import estimate_cost_usd
    assert estimate_cost_usd("gemma-4-26b-a4b", tokens_in=1_000_000, tokens_out=1_000_000) == 0.0


def test_parse_model_string():
    from gemini_hackathon.call_llm import parse_model_string
    assert parse_model_string("vertex_ai/gemini-3.5-flash") == ("vertex_ai", "gemini-3.5-flash")
    assert parse_model_string("gemini-3.5-flash") == (None, "gemini-3.5-flash")
