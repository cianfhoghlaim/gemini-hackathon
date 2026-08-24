"""Tests for ``gemini_hackathon.call_llm`` — the 3-tier model policy.

8 tests, one per requirement:

* Tier 1 (primary) is the default.
* Tier 2 (Unsloth) fires after Tier 1 fails.
* Tier 3 (Vertex AI) fires after Tier 2 fails.
* Cloudflare Workers AI model strings are rejected up front.
* Qwen3-coder model strings are rejected up front.
* The structlog ``llm.invocation`` event is emitted with the right
  payload.
* The exponential-backoff retry helper behaves correctly.
* The optional circuit-breaker flag is honoured (skipped if not
  implemented).

All tests use the :func:`fake_llm_router` and :func:`mock_call_llm`
fixtures from :mod:`tests.conftest` — no live HTTP traffic.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest
import structlog

from gemini_hackathon.call_llm import (
    BACKOFF_BASE_SECONDS,
    LLMCallError,
    LLMResponse,
    ModelExcludedError,
    TIER_1_MODEL,
    TIER_2_MODEL,
    TIER_3_MODEL,
    TIER_ORDER,
    TIER_RETRY_BUDGETS,
    _assert_model_allowed,
    call_llm,
)


# ---------------------------------------------------------------------------
# Happy-path: Tier 1 default
# ---------------------------------------------------------------------------


def test_tier_1_minimax_default(fake_llm_router) -> None:
    """Tier 1 (MiniMax-M3) is the default and returns the response.

    Asserts:

    * The resolved tier is ``1``.
    * The resolved model is the Tier 1 model.
    * The router only saw a single Tier 1 call (no fallthrough).
    * The response is an :class:`LLMResponse`.
    """
    fake_llm_router.succeed_at(tier=1, content="hello from tier 1")

    response = call_llm(messages=[{"role": "user", "content": "hi"}])

    assert isinstance(response, LLMResponse)
    assert response.tier == 1
    assert response.model == TIER_1_MODEL
    assert response.content == "hello from tier 1"
    assert fake_llm_router.tier_call_count[1] == 1
    assert fake_llm_router.tier_call_count[2] == 0
    assert fake_llm_router.tier_call_count[3] == 0


# ---------------------------------------------------------------------------
# Tier 2 fallback after Tier 1 failure
# ---------------------------------------------------------------------------


def test_tier_2_unsloth_fallback_on_tier_1_failure(fake_llm_router) -> None:
    """Tier 2 (Unsloth Gemma 4 26B) fires when Tier 1 fails.

    Asserts:

    * Tier 1 was attempted and failed.
    * Tier 2 succeeded.
    * The resolved tier is ``2`` and the model is the Tier 2 model.
    * Tier 3 was not attempted.
    """
    fake_llm_router.fail_through_to(tier=2, with_content="tier 2 reply")

    response = call_llm(messages=[{"role": "user", "content": "hi"}])

    assert response.tier == 2
    assert response.model == TIER_2_MODEL
    assert response.content == "tier 2 reply"
    assert fake_llm_router.tier_call_count[1] == TIER_RETRY_BUDGETS[TIER_1_MODEL]
    assert fake_llm_router.tier_call_count[2] == 1
    assert fake_llm_router.tier_call_count[3] == 0


# ---------------------------------------------------------------------------
# Tier 3 fallback after Tier 1 + Tier 2 failure
# ---------------------------------------------------------------------------


def test_tier_3_vertex_fallback_on_tier_2_failure(fake_llm_router) -> None:
    """Tier 3 (Vertex AI Gemini 3.5 Flash) fires when Tier 1 + Tier 2 fail."""
    fake_llm_router.fail_through_to(tier=3, with_content="tier 3 reply")

    response = call_llm(messages=[{"role": "user", "content": "hi"}])

    assert response.tier == 3
    assert response.model == TIER_3_MODEL
    assert response.content == "tier 3 reply"
    assert fake_llm_router.tier_call_count[1] == TIER_RETRY_BUDGETS[TIER_1_MODEL]
    assert fake_llm_router.tier_call_count[2] == TIER_RETRY_BUDGETS[TIER_2_MODEL]
    assert fake_llm_router.tier_call_count[3] == 1


# ---------------------------------------------------------------------------
# Exclusion patterns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden_model",
    [
        "@cf/meta/llama-3.1-8b-instruct",
        "@cf/mistralai/mistral-7b-instruct-v0.1",
        "openai/@cf/anthropic/claude-3-haiku",
    ],
)
def test_cloudflare_workers_ai_excluded_raises_ModelExcludedError(
    forbidden_model: str,
) -> None:
    """Cloudflare Workers AI model strings raise :class:`ModelExcludedError`.

    Per the model policy: any model string containing ``@cf/`` is
    rejected at module-import time. The :func:`_assert_model_allowed`
    helper raises :class:`ModelExcludedError`.
    """
    with pytest.raises(ModelExcludedError) as exc_info:
        _assert_model_allowed(forbidden_model)
    assert "excluded" in str(exc_info.value).lower()


def test_qwen3_coder_excluded_raises_ModelExcludedError() -> None:
    """Qwen3-coder model strings raise :class:`ModelExcludedError`.

    Both bare (``qwen3-coder-32b-instruct``) and prefixed
    (``provider/qwen3-coder-32b-instruct``) forms are rejected.
    """
    for forbidden in (
        "qwen3-coder-32b-instruct",
        "openai/qwen3-coder-7b-instruct",
        "huggingface/qwen3-coder-anything",
    ):
        with pytest.raises(ModelExcludedError):
            _assert_model_allowed(forbidden)


def test_all_tiers_failed_raises_LLMCallError(fake_llm_router) -> None:
    """When every tier fails, :class:`LLMCallError` is raised with attempts.

    Per the call_llm contract: every failure attempt is recorded
    in the :class:`LLMCallError.attempts` list. The final ``last_error``
    is the message from the last tier's failure.
    """
    # All 3 tiers fail (the default state).
    messages = [{"role": "user", "content": "hi"}]

    with pytest.raises(LLMCallError) as exc_info:
        call_llm(messages=messages)

    err = exc_info.value
    assert err.attempts  # at least one attempt recorded
    assert err.last_error
    # Every tier was attempted at least once.
    tiers_tried = {a.tier for a in err.attempts}
    assert tiers_tried == {1, 2, 3}


# ---------------------------------------------------------------------------
# structlog event emission
# ---------------------------------------------------------------------------


def test_structlog_emits_tier_event(fake_llm_router) -> None:
    """A successful call emits an ``llm.invocation`` structlog event.

    Per the model-policy spec the event payload includes:

    * ``event="llm.invocation"`` (passed positionally)
    * ``llm.tier="1"`` (string-typed, per the contract)
    * ``llm.model=<the Tier 1 model string>``
    * ``llm.latency_ms=<int>``

    We hook structlog via :func:`structlog.testing.capture_logs` to
    assert the event shape without depending on log routing.
    """
    fake_llm_router.succeed_at(tier=1, content="ok")

    with structlog.testing.capture_logs() as captured:
        response = call_llm(messages=[{"role": "user", "content": "hi"}])

    invocation_events = [e for e in captured if e.get("event") == "llm.invocation"]
    assert invocation_events, f"expected an llm.invocation event; got {captured!r}"
    event = invocation_events[-1]  # the most recent one
    assert event["llm.tier"] == str(response.tier)
    assert event["llm.model"] == response.model
    assert isinstance(event["llm.latency_ms"], int)


def test_structlog_emits_fallback_reason_for_tier_2(fake_llm_router) -> None:
    """Tier 2+ invocations emit ``llm.fallback_reason`` in the event payload.

    Per the model-policy spec: Tier 2 / Tier 3 events carry an
    ``llm.fallback_reason`` (Tier 1 events do not).
    """
    fake_llm_router.fail_through_to(tier=2, with_content="tier 2 reply")

    with structlog.testing.capture_logs() as captured:
        call_llm(messages=[{"role": "user", "content": "hi"}])

    invocations = [e for e in captured if e.get("event") == "llm.invocation"]
    assert invocations
    event = invocations[-1]
    assert event["llm.tier"] == "2"
    assert "llm.fallback_reason" in event
    assert event["llm.fallback_reason"]


# ---------------------------------------------------------------------------
# Retry / backoff
# ---------------------------------------------------------------------------


def test_retry_with_exponential_backoff(fake_llm_router) -> None:
    """The Tier 1 retry path uses exponential backoff.

    Per the spec: Tier 1 has ``TIER_RETRY_BUDGETS["minimax-m3"] == 2``
    (1 attempt + 1 retry). Between retries, the router sleeps for
    ``BACKOFF_BASE_SECONDS * 2**attempt_no``.

    This test asserts:

    * Tier 1 was called exactly ``TIER_RETRY_BUDGETS[TIER_1_MODEL]`` times.
    * The total elapsed wall-clock time is at least
      ``BACKOFF_BASE_SECONDS`` (one backoff sleep).
    """
    # Tier 1 keeps failing, Tier 2 succeeds.
    fake_llm_router.fail_through_to(tier=2, with_content="tier 2 wins")

    start = time.monotonic()
    response = call_llm(messages=[{"role": "user", "content": "hi"}])
    elapsed = time.monotonic() - start

    # Tier 1 was attempted the full retry budget.
    assert fake_llm_router.tier_call_count[1] == TIER_RETRY_BUDGETS[TIER_1_MODEL]
    assert response.tier == 2
    # At least one backoff sleep happened.
    assert elapsed >= BACKOFF_BASE_SECONDS, (
        f"Expected >= {BACKOFF_BASE_SECONDS}s elapsed, got {elapsed:.2f}s"
    )


# ---------------------------------------------------------------------------
# Tier ordering sanity check
# ---------------------------------------------------------------------------


def test_tier_ordering() -> None:
    """The canonical tier ordering is Tier 1 → Tier 2 → Tier 3.

    Asserts:

    * :data:`TIER_ORDER` lists the 3 models in the right order.
    * Each tier model is allowed (no exclusion pattern matches).
    """
    assert TIER_ORDER == (TIER_1_MODEL, TIER_2_MODEL, TIER_3_MODEL)
    for tier_model in TIER_ORDER:
        _assert_model_allowed(tier_model)  # must not raise


# ---------------------------------------------------------------------------
# Validation: empty messages list
# ---------------------------------------------------------------------------


def test_empty_messages_raises_value_error() -> None:
    """An empty ``messages`` list raises :class:`ValueError`."""
    with pytest.raises(ValueError, match="non-empty"):
        call_llm(messages=[])


# ---------------------------------------------------------------------------
# circuit breaker — optional behaviour (skip if not implemented)
# ---------------------------------------------------------------------------


def test_circuit_breaker_opens_after_n_failures(fake_llm_router) -> None:
    """The optional circuit-breaker opens after N consecutive failures.

    The current :mod:`gemini_hackathon.call_llm` ships the 3-tier
    policy with retry-with-backoff but does NOT ship an explicit
    circuit breaker. This test is therefore an opt-in feature
    check: it tries to import ``call_llm_with_circuit_breaker`` /
    similar; if absent the test is skipped.
    """
    try:
        from gemini_hackathon.call_llm import (
            call_llm_with_circuit_breaker,  # type: ignore[attr-defined]
        )
    except ImportError:
        pytest.skip("circuit-breaker API not implemented; opt-in feature")

    fake_llm_router.fail_through_to(tier=3, with_content="never reached")
    # The first N attempts go through the full 3-tier chain. The
    # (N+1)-th call should short-circuit and not hit any tier.
    from gemini_hackathon.call_llm import call_llm_with_circuit_breaker

    for _ in range(3):
        with pytest.raises(LLMCallError):
            call_llm_with_circuit_breaker(
                messages=[{"role": "user", "content": "hi"}],
                failure_threshold=2,
            )
    # After 3 full failures, the next call should be short-circuited.
    pre_count = sum(fake_llm_router.tier_call_count.values())
    with pytest.raises(LLMCallError):
        call_llm_with_circuit_breaker(
            messages=[{"role": "user", "content": "hi"}],
            failure_threshold=2,
        )
    post_count = sum(fake_llm_router.tier_call_count.values())
    assert post_count == pre_count, "circuit breaker should have short-circuited"