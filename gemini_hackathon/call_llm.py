"""gemini_hackathon.call_llm — the 3-tier LiteLLM router.

Every LLM call in the ``gemini_hackathon`` codebase MUST go through
:func:`call_llm`. The router enforces the **3-tier model policy**:

================== ============================================ ===========================================
Tier                Model                                        Provider / endpoint
================== ============================================ ===========================================
1 (primary)         ``minimax-m3``                               ``minimax.io`` (OpenAI-compatible)
2 (fallback)        ``unsloth/gemma-4-26B-A4B-it-GGUF``         ``unsloth-studio`` (local llama.cpp)
3 (last resort)     ``vertex_ai/gemini-3.5-flash``               Google Cloud Vertex AI
================== ============================================ ===========================================

Excluded (hard-coded rejection at module import time):

* Cloudflare Workers AI (``@cf/meta/llama-3.1-8b-instruct``, etc.)
* Qwen3-coder-anything (``qwen3-coder-32b-instruct``, etc.)

Each tier has retry logic with exponential backoff; the next tier
fires only after the previous tier has exhausted its retries. Every
invocation emits a structured log event (``llm.invocation``) with
the resolved tier, model, latency, and (when applicable) the
fallback reason.

Reference: ``openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md``.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import structlog

if TYPE_CHECKING:
    from litellm import Router

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Public constants — the 3-tier model policy
# ---------------------------------------------------------------------------

#: Tier 1 (primary) — MiniMax-M3 via api.minimax.io.
TIER_1_MODEL: str = "minimax-m3"

#: Tier 2 (fallback) — Unsloth Gemma 4 26B via local llama.cpp / Ollama.
TIER_2_MODEL: str = "unsloth/gemma-4-26B-A4B-it-GGUF"

#: Tier 3 (last resort) — Vertex AI Gemini 3.5 Flash.
TIER_3_MODEL: str = "vertex_ai/gemini-3.5-flash"

#: Canonical ordering of the tiers (low → high).
TIER_ORDER: tuple[str, ...] = (TIER_1_MODEL, TIER_2_MODEL, TIER_3_MODEL)

#: Per-tier retry budgets. The router walks Tier 1 → 2 → 3 only when the
#: current tier has exhausted its retries. After all three tiers fail,
#: :class:`LLMCallError` is raised.
TIER_RETRY_BUDGETS: dict[str, int] = {
    TIER_1_MODEL: 2,  # 1 attempt + 1 retry on 5xx/timeout
    TIER_2_MODEL: 1,  # 1 attempt only — local model is fast to recover
    TIER_3_MODEL: 1,  # 1 attempt only — Vertex is a paid endpoint
}

#: Base delay for exponential backoff, in seconds.
BACKOFF_BASE_SECONDS: float = 1.0

#: Maximum per-tier wall-clock budget, in seconds. If a single tier
#: takes longer than this, we cancel it and fall through.
TIER_TIMEOUT_SECONDS: float = 30.0

# ---------------------------------------------------------------------------
# Explicitly-excluded model patterns
# ---------------------------------------------------------------------------

#: Cloudflare Workers AI model prefix. Always rejected.
_CF_PREFIX: str = "@cf/"

#: Qwen3-coder model prefix. Always rejected.
_QWEN_CODER_PREFIX: str = "qwen3-coder-"


_EXCLUDED_HELP: str = (
    "is explicitly excluded by the gemini_hackathon model policy. "
    "See openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md"
)


def _assert_model_allowed(model: str) -> None:
    """Reject any model string that matches the exclusion patterns.

    Called by :func:`call_llm` before the request leaves the
    process. Raises :class:`ModelExcludedError` with a descriptive
    message.

    Args:
        model: The LiteLLM model string to validate.

    Raises:
        ModelExcludedError: If the model matches a forbidden prefix.
    """
    lowered = model.lower()
    if _CF_PREFIX in lowered:
        raise ModelExcludedError(f"Model {model} {_EXCLUDED_HELP}")
    if lowered.startswith(_QWEN_CODER_PREFIX) or f"/{_QWEN_CODER_PREFIX}" in lowered:
        raise ModelExcludedError(f"Model {model} {_EXCLUDED_HELP}")


# ---------------------------------------------------------------------------
# Exception types
# ---------------------------------------------------------------------------


class ModelExcludedError(ValueError):
    """Raised when a caller requests a model that is excluded by policy."""


class LLMCallError(RuntimeError):
    """Raised when all 3 tiers have failed for a ``call_llm()`` invocation.

    Attributes:
        last_error: The exception (or error message) from the final tier.
        attempts: The list of :class:`TierAttempt` records that were tried.
    """

    def __init__(self, message: str, *, attempts: Sequence[TierAttempt]) -> None:
        super().__init__(message)
        self.attempts: list[TierAttempt] = list(attempts)
        self.last_error: str = attempts[-1].error if attempts else ""


class TierTimeoutError(RuntimeError):
    """Raised internally when a single tier exceeds its wall-clock budget."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TierAttempt:
    """One attempt against a single tier.

    Attributes:
        tier: The tier number (1, 2, or 3).
        model: The LiteLLM model string that was invoked.
        latency_ms: The wall-clock latency for this attempt.
        error: The error string (empty if the attempt succeeded).
        succeeded: Whether the attempt returned a valid response.
    """

    tier: int
    model: str
    latency_ms: int
    error: str = ""
    succeeded: bool = False


@dataclass(frozen=True)
class LLMResponse:
    """The result of a successful :func:`call_llm` invocation.

    Attributes:
        content: The text content of the assistant message.
        model: The model that actually served the request (one of
            the 3 tier models).
        tier: The tier that served the request (1, 2, or 3).
        latency_ms: Total wall-clock latency across all attempts.
        tokens_in: Total prompt tokens (best-effort, may be 0).
        tokens_out: Total completion tokens (best-effort, may be 0).
        cost_usd: Estimated cost in USD (best-effort, may be 0).
        attempts: The list of :class:`TierAttempt` records.
    """

    content: str
    model: str
    tier: int
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    attempts: list[TierAttempt] = field(default_factory=list)


Message = dict[str, str]
"""The OpenAI-compatible message shape: ``{"role": ..., "content": ...}``."""


ModelTier = Literal["1", "2", "3"]
"""String literal for the 3 tiers (matches the spec log contract)."""


# ---------------------------------------------------------------------------
# LiteLLM router construction
# ---------------------------------------------------------------------------

_ROUTER: Router | None = None


def _build_router() -> Router:
    """Build (and cache) the LiteLLM router.

    The router uses a single ``model_group`` named ``"primary"``
    that wraps all three tiers as fallbacks. The 3-tier ordering
    is enforced by LiteLLM's native fallback chain — but our code
    ALSO walks the tiers manually (so we can emit per-tier
    ``llm.invocation`` events and retry with exponential backoff).

    Returns:
        A :class:`litellm.Router` instance configured with the 3
        tiers, in tier-order.

    Raises:
        ImportError: If ``litellm`` is not installed.
    """
    global _ROUTER  # noqa: PLW0603
    if _ROUTER is not None:
        return _ROUTER

    try:
        from litellm import Router  # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "litellm is required by gemini_hackathon.call_llm. "
            "Install with `uv add litellm`."
        ) from e

    # Per-model list entries. The order in `model_list` is the
    # routing order when `weight` is identical.
    model_list: list[dict[str, Any]] = [
        {
            "model_name": "primary",
            "litellm_params": {
                "model": TIER_1_MODEL,
                "api_key": os.getenv("MINIMAX_API_KEY", "sk-placeholder"),
                "api_base": os.getenv(
                    "MINIMAX_BASE_URL", "https://api.minimax.io/v1"
                ),
                "timeout": TIER_TIMEOUT_SECONDS,
            },
        },
        {
            "model_name": "fallback-1",
            "litellm_params": {
                "model": TIER_2_MODEL,
                "api_key": os.getenv("UNSLOTH_API_KEY", "ollama"),
                "api_base": os.getenv(
                    "UNSLOTH_BASE_URL", "http://localhost:11434/v1"
                ),
                "timeout": TIER_TIMEOUT_SECONDS,
            },
        },
        {
            "model_name": "fallback-2",
            "litellm_params": {
                "model": TIER_3_MODEL,
                "vertex_project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "vertex_location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
                "timeout": TIER_TIMEOUT_SECONDS,
            },
        },
    ]

    fallback_list: list[dict[str, str]] = [
        {"model": "primary"},
        {"model": "fallback-1"},
        {"model": "fallback-2"},
    ]

    _ROUTER = Router(
        model_list=model_list,
        fallbacks=fallback_list,
        num_retries=1,  # LiteLLM-internal retry budget per tier
        timeout=TIER_TIMEOUT_SECONDS,
        set_verbose=False,
    )
    return _ROUTER


def reset_router() -> None:
    """Reset the cached router. Useful for tests."""
    global _ROUTER  # noqa: PLW0603
    _ROUTER = None


# ---------------------------------------------------------------------------
# The main entrypoint
# ---------------------------------------------------------------------------


def call_llm(
    messages: Sequence[Message],
    *,
    model_tier: ModelTier | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    metadata: dict[str, Any] | None = None,
) -> LLMResponse:
    """Call the LLM through the 3-tier router.

    Walks Tier 1 → Tier 2 → Tier 3 in order. Each tier has its own
    retry budget (see :data:`TIER_RETRY_BUDGETS`). The next tier
    fires when the current tier exhausts its retries, returns a
    5xx/timeout, or raises :class:`TierTimeoutError`.

    Every attempt emits a structured ``llm.invocation`` log event.
    The final log event (after all retries/fallbacks resolve)
    carries the resolved ``tier`` + ``model``.

    Args:
        messages: The OpenAI-compatible message list (must be
            non-empty; last message SHOULD be ``role=user``).
        model_tier: Optional tier pin. ``None`` = start at Tier 1
            and fall through. ``"1"`` = Tier 1 only, ``"2"`` =
            Tier 2 only, ``"3"`` = Tier 3 only.
        temperature: Sampling temperature in [0.0, 2.0]. Default 0.2.
        max_tokens: Max completion tokens. Default 1024.
        metadata: Optional dict merged into the log event (e.g.
            ``{"trace_id": "abc", "agent": "marking_grader"}``).

    Returns:
        An :class:`LLMResponse` with the assistant text content,
        the model that served the request, and telemetry.

    Raises:
        ModelExcludedError: If any tier model matches the exclusion
            patterns (defense-in-depth — should never fire since
            the 3 canonical tiers don't match the patterns).
        ValueError: If ``messages`` is empty.
        LLMCallError: If every tier has failed.

    Example:
        >>> response = call_llm(
        ...     [{"role": "user", "content": "What is 2+2?"}],
        ... )
        >>> response.tier
        1
        >>> response.model
        'minimax-m3'
    """
    if not messages:
        raise ValueError("call_llm() requires a non-empty `messages` list")

    # Validate every candidate tier at module-load time (cheap, fail-fast).
    for tier_model in TIER_ORDER:
        _assert_model_allowed(tier_model)

    # Choose the starting tier + the set of tiers to try.
    if model_tier is None:
        tiers_to_try: list[int] = [1, 2, 3]
    else:
        tiers_to_try = [int(model_tier)]

    # TIER_MODEL_BY_TIER — reverse lookup (model_tier int → model string).
    tier_model_by_idx: dict[int, str] = {1: TIER_1_MODEL, 2: TIER_2_MODEL, 3: TIER_3_MODEL}

    router = _build_router()

    attempts: list[TierAttempt] = []
    overall_start = time.monotonic()
    log_metadata: dict[str, Any] = dict(metadata or {})

    for tier_idx in tiers_to_try:
        model = tier_model_by_idx[tier_idx]
        retry_budget = TIER_RETRY_BUDGETS.get(model, 1)

        for attempt_no in range(retry_budget):
            attempt_start = time.monotonic()
            tier_router_name = "primary" if tier_idx == 1 else f"fallback-{tier_idx - 1}"
            error_msg = ""
            content = ""
            tokens_in = 0
            tokens_out = 0
            cost = 0.0

            try:
                response = router.completion(
                    model=tier_router_name,
                    messages=list(messages),
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content or ""
                # Best-effort usage extraction.
                usage = getattr(response, "usage", None)
                if usage is not None:
                    tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
                    tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
                attempt_ms = int((time.monotonic() - attempt_start) * 1000)
                attempts.append(
                    TierAttempt(
                        tier=tier_idx,
                        model=model,
                        latency_ms=attempt_ms,
                        succeeded=True,
                    )
                )
                # SUCCESS — emit log + return.
                total_ms = int((time.monotonic() - overall_start) * 1000)
                _emit_invocation_log(
                    tier=tier_idx,
                    model=model,
                    latency_ms=total_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost,
                    metadata=log_metadata,
                )
                return LLMResponse(
                    content=content,
                    model=model,
                    tier=tier_idx,
                    latency_ms=total_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost,
                    attempts=attempts,
                )

            except Exception as e:  # noqa: BLE001 — broad catch on purpose
                attempt_ms = int((time.monotonic() - attempt_start) * 1000)
                error_msg = f"{type(e).__name__}: {e}"
                attempts.append(
                    TierAttempt(
                        tier=tier_idx,
                        model=model,
                        latency_ms=attempt_ms,
                        error=error_msg,
                        succeeded=False,
                    )
                )
                logger.warning(
                    "llm.invocation_failed",
                    llm_tier=str(tier_idx),
                    llm_model=model,
                    llm_latency_ms=attempt_ms,
                    llm_attempt=attempt_no + 1,
                    llm_retry_budget=retry_budget,
                    llm_error=error_msg,
                    **log_metadata,
                )

                # Exponential backoff between retries within the same tier.
                if attempt_no + 1 < retry_budget:
                    backoff = BACKOFF_BASE_SECONDS * (2**attempt_no)
                    logger.info(
                        "llm.retry_scheduled",
                        llm_tier=str(tier_idx),
                        llm_model=model,
                        llm_backoff_seconds=backoff,
                        **log_metadata,
                    )
                    time.sleep(backoff)
                    continue

                # Out of retries on this tier — fall through to next tier.
                logger.info(
                    "llm.tier_exhausted",
                    llm_tier=str(tier_idx),
                    llm_model=model,
                    **log_metadata,
                )
                break

    # All tiers exhausted.
    total_ms = int((time.monotonic() - overall_start) * 1000)
    logger.error(
        "llm.all_tiers_failed",
        llm_latency_ms=total_ms,
        llm_tiers_attempted=[str(t) for t in tiers_to_try],
        **log_metadata,
    )
    raise LLMCallError(
        f"All {len(tiers_to_try)} tier(s) failed for call_llm(); "
        f"see attempts[] for details.",
        attempts=attempts,
    )


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------


def _emit_invocation_log(
    *,
    tier: int,
    model: str,
    latency_ms: int,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    metadata: dict[str, Any],
) -> None:
    """Emit the canonical ``llm.invocation`` structlog event.

    Matches the contract in ``model-policy/spec.md:163-184``:
    ``event=llm.invocation`` + ``llm.tier`` + ``llm.model`` +
    ``llm.latency_ms`` + (optionally) ``llm.fallback_reason`` +
    ``llm.tokens_in``/``llm.tokens_out`` + ``llm.cost_usd``.

    Args:
        tier: The resolved tier (1, 2, or 3).
        model: The resolved model string.
        latency_ms: The wall-clock latency in milliseconds.
        tokens_in: Prompt tokens consumed.
        tokens_out: Completion tokens produced.
        cost_usd: Estimated cost (best-effort, may be 0.0).
        metadata: Optional caller metadata merged into the log.
    """
    # NB: the "event" key is set positionally below via logger.info("llm.invocation").
    # We intentionally do NOT include "event" in payload, otherwise structlog 25+
    # raises TypeError: "got multiple values for argument 'event'".
    payload: dict[str, Any] = {
        "llm.tier": str(tier),
        "llm.model": model,
        "llm.latency_ms": latency_ms,
        "llm.tokens_in": tokens_in,
        "llm.tokens_out": tokens_out,
        "llm.cost_usd": cost_usd,
    }
    if tier > 1:
        payload["llm.fallback_reason"] = _fallback_reason_for(tier)
    payload.update(metadata)
    logger.info("llm.invocation", **payload)


def _fallback_reason_for(tier: int) -> str:
    """Best-effort fallback reason string."""
    return {
        2: "primary_5xx_or_timeout",
        3: "primary_5xx_or_timeout+secondary_unreachable",
    }.get(tier, "unknown")


# ---------------------------------------------------------------------------
# Utility helpers (exported for fleet_observability + tests)
# ---------------------------------------------------------------------------


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    """Return the estimated cost in USD for a model invocation.

    Best-effort pricing (USD per 1k tokens, as of 2026-Q3). The
    canonical source-of-truth pricing table lives in
    ``docs/MODEL_POLICY.md``; this is a conservative fallback.

    Args:
        model: The LiteLLM model string.
        tokens_in: Prompt tokens consumed.
        tokens_out: Completion tokens produced.

    Returns:
        Estimated cost in USD (0.0 if the model is unknown).
    """
    pricing = {
        TIER_1_MODEL: (0.0002, 0.0006),  # MiniMax-M3
        TIER_2_MODEL: (0.0, 0.0),  # local — electricity only
        TIER_3_MODEL: (0.000075, 0.0003),  # Vertex Gemini 3.5 Flash
    }
    in_rate, out_rate = pricing.get(model, (0.0, 0.0))
    return round((tokens_in / 1000.0) * in_rate + (tokens_out / 1000.0) * out_rate, 6)


def normalise_messages(messages: Iterable[Message]) -> list[Message]:
    """Coerce an iterable of message dicts into a list, validating roles.

    Args:
        messages: Any iterable of message dicts.

    Returns:
        A list of message dicts with ``role`` ∈
        {``system``, ``user``, ``assistant``}.

    Raises:
        ValueError: If any message is missing ``role`` or ``content``.
    """
    out: list[Message] = []
    for msg in messages:
        if "role" not in msg or "content" not in msg:
            raise ValueError(f"Message must have `role` and `content` keys; got {msg!r}")
        if msg["role"] not in {"system", "user", "assistant"}:
            raise ValueError(f"Invalid message role: {msg['role']!r}")
        out.append({"role": msg["role"], "content": str(msg["content"])})
    return out


def parse_model_string(model: str) -> tuple[str, str | None]:
    """Split a LiteLLM model string into ``(provider, name)``.

    Args:
        model: The LiteLLM model string (e.g. ``"vertex_ai/gemini-3.5-flash"``).

    Returns:
        A 2-tuple ``(provider, name)``. For unprefixed names the
        provider is ``None``.
    """
    if "/" in model:
        provider, _, name = model.partition("/")
        return provider, name
    return model, None


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "BACKOFF_BASE_SECONDS",
    "LLMCallError",
    "LLMResponse",
    "Message",
    "ModelExcludedError",
    "ModelTier",
    "TIER_1_MODEL",
    "TIER_2_MODEL",
    "TIER_3_MODEL",
    "TIER_ORDER",
    "TIER_RETRY_BUDGETS",
    "TIER_TIMEOUT_SECONDS",
    "TierAttempt",
    "TierTimeoutError",
    "_assert_model_allowed",
    "call_llm",
    "estimate_cost_usd",
    "normalise_messages",
    "parse_model_string",
    "reset_router",
]
