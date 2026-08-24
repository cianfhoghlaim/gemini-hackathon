"""Tests for the 3-tier model policy exclusion patterns.

5 tests:

* Cloudflare Workers AI model strings are rejected.
* Qwen3-coder model strings are rejected.
* The canonical 3-tier models are accepted.
* The :data:`TIER_ORDER` tuple + the 3-tier policy table is intact.
* BAML clients + canonical retry policies don't include excluded
  models.

These tests are the canary that detects any regression in the
model-exclusion enforcement (the per-model defense layer).
"""

from __future__ import annotations

import pytest

from gemini_hackathon.call_llm import (
    ModelExcludedError,
    TIER_1_MODEL,
    TIER_2_MODEL,
    TIER_3_MODEL,
    TIER_ORDER,
    TIER_RETRY_BUDGETS,
    _assert_model_allowed,
)


# ---------------------------------------------------------------------------
# Rejections
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden_model",
    [
        "@cf/meta/llama-3.1-8b-instruct",
        "@cf/mistralai/mistral-7b-instruct-v0.1",
        "@cf/meta/llama-2-7b-chat-int8",
    ],
)
def test_cloudflare_model_rejected(forbidden_model: str) -> None:
    """Cloudflare Workers AI models (``@cf/...``) raise :class:`ModelExcludedError`.

    Per the model policy spec: any model string containing the
    ``@cf/`` prefix is rejected at module-load time. The rejection
    message references the openspec change so an operator can audit
    the rationale.
    """
    with pytest.raises(ModelExcludedError) as exc_info:
        _assert_model_allowed(forbidden_model)

    msg = str(exc_info.value).lower()
    assert "excluded" in msg
    assert forbidden_model.lower() in msg or forbidden_model in str(exc_info.value)


@pytest.mark.parametrize(
    "forbidden_model",
    [
        "qwen3-coder-32b-instruct",
        "qwen3-coder-7b-instruct",
        "openai/qwen3-coder-32b-instruct",
        "huggingface/qwen3-coder-anything",
    ],
)
def test_qwen3_coder_model_rejected(forbidden_model: str) -> None:
    """Qwen3-coder models raise :class:`ModelExcludedError`.

    Per the model policy spec: any model string starting with
    ``qwen3-coder-`` (or carrying a ``/qwen3-coder-`` path segment)
    is rejected.
    """
    with pytest.raises(ModelExcludedError):
        _assert_model_allowed(forbidden_model)


def test_call_llm_with_excluded_model_raises(fake_llm_router) -> None:
    """Even when the router would succeed, an excluded model string raises.

    The exclusion is enforced at module-load time via
    :func:`_assert_model_allowed`. The router never sees an
    excluded model string. We verify the helper directly here
    (the :func:`call_llm` wrapper doesn't accept a model override
    parameter — only ``model_tier``, which is one of the canonical
    Tier 1 / 2 / 3 ints).
    """
    # Direct validation: excluded model strings raise immediately.
    with pytest.raises(ModelExcludedError):
        _assert_model_allowed("@cf/meta/llama-3.1-8b-instruct")

    # The Tier 1 / 2 / 3 models validate cleanly (defense-in-depth).
    for tier_model in (TIER_1_MODEL, TIER_2_MODEL, TIER_3_MODEL):
        _assert_model_allowed(tier_model)  # must not raise


# ---------------------------------------------------------------------------
# Acceptances (the canonical 3 tiers)
# ---------------------------------------------------------------------------


def test_minimax_model_accepted() -> None:
    """The Tier 1 model (``minimax-m3``) is accepted."""
    _assert_model_allowed(TIER_1_MODEL)  # must not raise


def test_unsloth_model_accepted() -> None:
    """The Tier 2 model (``unsloth/gemma-4-26B-A4B-it-GGUF``) is accepted."""
    _assert_model_allowed(TIER_2_MODEL)


def test_vertex_model_accepted() -> None:
    """The Tier 3 model (``vertex_ai/gemini-3.5-flash``) is accepted."""
    _assert_model_allowed(TIER_3_MODEL)


def test_all_three_canonical_tiers_in_order() -> None:
    """``TIER_ORDER`` is the ordered tuple ``(Tier 1, Tier 2, Tier 3)``.

    The ordering matters: it's the order the :func:`call_llm` router
    walks when the previous tier fails.
    """
    assert TIER_ORDER == (TIER_1_MODEL, TIER_2_MODEL, TIER_3_MODEL)
    # Each tier model has its own retry budget.
    assert TIER_RETRY_BUDGETS[TIER_1_MODEL] >= 1
    assert TIER_RETRY_BUDGETS[TIER_2_MODEL] >= 1
    assert TIER_RETRY_BUDGETS[TIER_3_MODEL] >= 1


# ---------------------------------------------------------------------------
# BAML client cross-check
# ---------------------------------------------------------------------------


def test_baml_clients_do_not_reference_excluded_models() -> None:
    """The BAML clients roster does not include Cloudflare or Qwen3-coder.

    Cross-checks that the BAML client roster (``clients.baml``) is
    aligned with the call_llm exclusion policy — i.e. no client
    accidentally references an excluded model.
    """
    from pathlib import Path

    clients_file = Path(__file__).resolve().parent.parent / "baml_extracts" / "clients.baml"
    if not clients_file.exists():
        pytest.skip("clients.baml not present")

    text = clients_file.read_text(encoding="utf-8")
    # No @cf/ references.
    assert "@cf/" not in text, "BAML clients.baml references a Cloudflare model"
    # No qwen3-coder references.
    assert "qwen3-coder" not in text, "BAML clients.baml references a Qwen3-coder model"