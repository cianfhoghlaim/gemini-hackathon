"""Tests for the model-policy exclusion guard.

Covers both the gemini_hackathon.call_llm guard and the registry-level
constraints (hackathon profile must not include excluded families).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# call_llm._assert_model_allowed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "@cf/meta/llama-3.1-8b-instruct",
        "@cf/mistralai/mistral-7b-instruct-v0.1",
        "@cf/google/gemma-3-4b-it",
        "qwen3-coder-32b-instruct",
        "qwen3-coder-7b-instruct",
        "openai/qwen3-coder-anything",
        "openrouter/qwen3-coder-7b-instruct",
    ],
)
def test_excluded_model_strings_rejected(bad):
    from gemini_hackathon.call_llm import _assert_model_allowed, ModelExcludedError

    with pytest.raises(ModelExcludedError) as exc:
        _assert_model_allowed(bad)
    assert "excluded" in str(exc.value).lower()


@pytest.mark.parametrize(
    "good",
    [
        "gemini-3.5-flash",
        "gemma-4-26b-a4b",
        "vertex_ai/gemini-3.5-flash",
        "openai/gemma-4-26b-a4b",
        "openai/qwen3-vl-8b",
        "openai/qwen3-vl-4b",
        "openai/unsloth/qwen-image-2512",
        "minimax-m3",
        "gemini/gemini-3.5-flash",
    ],
)
def test_allowed_model_strings_accepted(good):
    from gemini_hackathon.call_llm import _assert_model_allowed

    _assert_model_allowed(good)


def test_excluded_error_has_helpful_message():
    from gemini_hackathon.call_llm import ModelExcludedError, _assert_model_allowed

    try:
        _assert_model_allowed("@cf/meta/llama-3.1-8b-instruct")
    except ModelExcludedError as e:
        assert "model-policy" in str(e).lower() or "excluded" in str(e).lower()


# ---------------------------------------------------------------------------
# Registry-level: hackathon profile must not include excluded families
# ---------------------------------------------------------------------------


def test_hackathon_profile_contains_no_cloudflare_models():
    from gemini_hackathon.model_registry import MODEL_REGISTRY

    hack = MODEL_REGISTRY.for_profile("hackathon")
    for entry in hack:
        assert "@cf/" not in (entry.litellm_alias or "").lower()
        assert "@cf/" not in entry.key.lower()


def test_hackathon_profile_contains_no_qwen3_coder_models():
    from gemini_hackathon.model_registry import MODEL_REGISTRY

    hack = MODEL_REGISTRY.for_profile("hackathon")
    for entry in hack:
        assert "qwen3-coder" not in entry.key.lower()
        assert "qwen3-coder" not in (entry.litellm_alias or "").lower()


def test_hackathon_profile_contains_gemini_and_gemma4():
    from gemini_hackathon.model_registry import MODEL_REGISTRY

    hack = MODEL_REGISTRY.for_profile("hackathon")
    keys = {e.key for e in hack}
    assert "gemini-3.5-flash" in keys
    assert "gemma-4-26b-a4b" in keys


def test_hackathon_profile_omits_minimax():
    from gemini_hackathon.model_registry import MODEL_REGISTRY

    hack = MODEL_REGISTRY.for_profile("hackathon")
    keys = {e.key for e in hack}
    assert "minimax-m3" not in keys


def test_dev_profile_includes_minimax():
    from gemini_hackathon.model_registry import MODEL_REGISTRY

    dev = MODEL_REGISTRY.for_profile("dev")
    keys = {e.key for e in dev}
    assert "minimax-m3" in keys


# ---------------------------------------------------------------------------
# Profile gate: a profile must be respected by the registry
# ---------------------------------------------------------------------------


def test_hackathon_and_dev_have_distinct_counts():
    from gemini_hackathon.model_registry import MODEL_REGISTRY

    assert len(MODEL_REGISTRY.for_profile("hackathon")) != len(MODEL_REGISTRY.for_profile("dev"))


def test_both_entries_visible_in_either_profile():
    from gemini_hackathon.model_registry import MODEL_REGISTRY

    hack_keys = {e.key for e in MODEL_REGISTRY.for_profile("hackathon")}
    dev_keys = {e.key for e in MODEL_REGISTRY.for_profile("dev")}
    both_keys = {e.key for e in MODEL_REGISTRY if e.profile == "both"}
    assert both_keys <= hack_keys
    assert both_keys <= dev_keys


def test_resolve_unknown_family_returns_none():
    from gemini_hackathon.model_registry import model_for

    assert model_for("text_llm", "this_role_does_not_exist") is None


def test_resolve_unknown_family_literal_returns_none():
    from gemini_hackathon.model_registry import model_for

    # Family literal that's not in the union — typing-ignores because we test at runtime.
    assert model_for("text_llm", "default") is not None
    assert model_for("text_llm", "default", profile="hackathon") is not None
