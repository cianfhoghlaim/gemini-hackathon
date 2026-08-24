"""gemini_hackathon.call_llm — the dual-profile LiteLLM router.

Every LLM call in the gemini_hackathon codebase MUST go through :func:`call_llm`.
The router enforces a 2-tier policy that depends on ``MODEL_PROFILE``:

==================  ============  ===========================================  ==========================================
Tier (hackathon)    Model         Backend                                       Notes
==================  ============  ===========================================  ==========================================
1 (primary)         gemini-3.5    Vertex AI (default) / AI Studio (env switch) Promotes Google Cloud usage
2 (fallback)        gemma-4-26B   Unsloth Studio (:8888)                       Same family as the text Tier 1's sibling
==================  ============  ===========================================  ==========================================

Dev profile adds minimax-m3 (Tier 3) and the wider Unsloth Studio text set
for harness comparisons. The hackathon profile is the only one docs, UI,
or submission ever reference; dev-only models are gated by ``MODEL_PROFILE=dev``.

Excluded (hard rejection at module-import time):
- Cloudflare Workers AI (``@cf/meta/llama-3.1-8b-instruct`` etc.)
- Qwen3-coder-* (any model starting with that prefix)

The router is built on top of :class:`gemini_hackathon.models.MODEL_REGISTRY`;
model strings are resolved via :func:`model_for(family, role)` rather than
hardcoded. Adding a new model is a registry change, not a router change.

Reference: openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import structlog

from .models import MODEL_REGISTRY, ModelFamily, ModelProfile, ModelRegistryEntry, model_for

if TYPE_CHECKING:
    from litellm import Router

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Excluded-model patterns — these cannot be routed, ever.
# ---------------------------------------------------------------------------

_CF_PREFIX: str = "@cf/"
_QWEN_CODER_PREFIX: str = "qwen3-coder-"
_EXCLUDED_HELP: str = (
    "is explicitly excluded by the gemini_hackathon model policy. "
    "See openspec/changes/2026-08-24-gemini-hackathon-public-v1/specs/model-policy/spec.md"
)


def _assert_model_allowed(model: str) -> None:
    """Reject any model string that matches the exclusion patterns."""
    lowered = model.lower()
    if _CF_PREFIX in lowered:
        raise ModelExcludedError(f"Model {model} {_EXCLUDED_HELP}")
    if lowered.startswith(_QWEN_CODER_PREFIX) or f"/{_QWEN_CODER_PREFIX}" in lowered:
        raise ModelExcludedError(f"Model {model} {_EXCLUDED_HELP}")


# ---------------------------------------------------------------------------
# Per-tier retry budgets + backoff (same contract as before).
# ---------------------------------------------------------------------------

BACKOFF_BASE_SECONDS: float = 1.0
TIER_TIMEOUT_SECONDS: float = 30.0

# Tiers in execution order for the hackathon profile.
HACKATHON_TIERS: tuple[tuple[ModelFamily, str], ...] = (
    ("text_llm", "default"),    # Gemini 3.5
    ("text_llm", "fallback"),   # Gemma 4 26B-A4B
)

# Dev profile adds a third tier (minimax-m3) for the harness.
DEV_TIERS: tuple[tuple[ModelFamily, str], ...] = (
    ("text_llm", "default"),
    ("text_llm", "fallback"),
    ("text_llm", "dev_primary"),
)

# Per-tier retry budgets. The router walks the tiers only after the current
# tier has exhausted its retries. After all tiers fail, LLMCallError is raised.
TIER_RETRY_BUDGETS: dict[str, int] = {
    "default": 2,
    "fallback": 1,
    "dev_primary": 1,
}


# ---------------------------------------------------------------------------
# Exception + data types.
# ---------------------------------------------------------------------------


class ModelExcludedError(ValueError):
    """Raised when a caller requests a model that is excluded by policy."""


class LLMCallError(RuntimeError):
    """Raised when every tier has failed for a ``call_llm()`` invocation."""

    def __init__(self, message: str, *, attempts: Sequence[TierAttempt]) -> None:
        super().__init__(message)
        self.attempts: list[TierAttempt] = list(attempts)
        self.last_error: str = attempts[-1].error if attempts else ""


class TierTimeoutError(RuntimeError):
    """Raised internally when a single tier exceeds its wall-clock budget."""


@dataclass(frozen=True)
class TierAttempt:
    """One attempt against a single tier."""

    tier: int
    family: ModelFamily
    role: str
    model: str
    backend: str
    latency_ms: int
    error: str = ""
    succeeded: bool = False


@dataclass(frozen=True)
class LLMResponse:
    """The result of a successful :func:`call_llm` invocation."""

    content: str
    model: str
    backend: str
    tier: int
    family: ModelFamily
    role: str
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    attempts: list[TierAttempt] = field(default_factory=list)


Message = dict[str, str]
"""OpenAI-compatible message shape: ``{"role": ..., "content": ...}``."""


# ---------------------------------------------------------------------------
# LiteLLM router construction.
# ---------------------------------------------------------------------------

_ROUTER: Router | None = None


def _build_router() -> Router:
    """Build (and cache) the LiteLLM router with the active profile's tiers."""
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

    profile = _active_profile()
    tiers = DEV_TIERS if profile == "dev" else HACKATHON_TIERS

    model_list: list[dict[str, Any]] = []
    fallback_list: list[dict[str, str]] = []
    for i, (family, role) in enumerate(tiers, start=1):
        entry = model_for(family, role, profile=profile)
        if entry is None or entry.litellm_alias is None:
            logger.warning(
                "tier_skipped_no_registry_entry",
                tier=i,
                family=family,
                role=role,
                profile=profile,
            )
            continue
        _assert_model_allowed(entry.litellm_alias)
        model_list.append({
            "model_name": f"tier-{i}",
            "litellm_params": _build_litellm_params(entry),
        })
        fallback_list.append({"model": f"tier-{i}"})

    _ROUTER = Router(
        model_list=model_list,
        fallbacks=fallback_list,
        num_retries=1,
        timeout=TIER_TIMEOUT_SECONDS,
        set_verbose=False,
    )
    return _ROUTER


def _build_litellm_params(entry: ModelRegistryEntry) -> dict[str, Any]:
    """Translate a registry entry into a LiteLLM ``litellm_params`` block."""
    alias = entry.litellm_alias or ""
    params: dict[str, Any] = {
        "model": alias,
        "timeout": TIER_TIMEOUT_SECONDS,
    }

    if entry.backend == "vertex":
        params["vertex_project"] = os.getenv("GOOGLE_CLOUD_PROJECT")
        params["vertex_location"] = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        # Vertex uses ADC by default; no API key needed.
    elif entry.backend == "aistudio":
        params["api_key"] = os.getenv("GEMINI_API_KEY", "")
    elif entry.backend == "unsloth_studio":
        params["api_base"] = os.getenv("UNSLOTH_BASE_URL", "http://127.0.0.1:8888/v1")
        params["api_key"] = os.getenv("UNSLOTH_API_KEY", "sk-unsloth-placeholder")
    elif entry.backend == "llama_swap":
        params["api_base"] = os.getenv("LLAMA_SWAP_BASE_URL", "http://127.0.0.1:8080/v1")
        params["api_key"] = os.getenv("LLAMASWAP_API_KEY", "not-required")
    elif entry.backend == "minimax":
        params["api_key"] = os.getenv("MINIMAX_API_KEY", "sk-placeholder")
        params["api_base"] = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
    elif entry.backend == "invokeai":
        params["api_base"] = os.getenv("INVOKEAI_BASE_URL", "http://127.0.0.1:9090/v1")
        params["api_key"] = os.getenv("INVOKEAI_API_KEY", "not-required")
    elif entry.backend == "comfyui":
        params["api_base"] = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
        params["api_key"] = os.getenv("COMFYUI_API_KEY", "not-required")
    # local + google + voice + translation entries fall through; the caller
    # is responsible for using the right adapter.

    return params


def reset_router() -> None:
    """Reset the cached router. Useful for tests + profile swaps."""
    global _ROUTER  # noqa: PLW0603
    _ROUTER = None


# ---------------------------------------------------------------------------
# The main entrypoint.
# ---------------------------------------------------------------------------


def call_llm(
    messages: Sequence[Message],
    *,
    profile: ModelProfile | None = None,
    family: ModelFamily | None = None,
    role: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    metadata: dict[str, Any] | None = None,
) -> LLMResponse:
    """Call the LLM through the dual-profile router.

    Behaviour:
        * ``profile`` defaults to ``$MODEL_PROFILE`` (or ``hackathon``).
        * When ``family`` and ``role`` are passed, the router resolves
          those — useful for harness comparisons (e.g. compare text_llm
          dev_strong vs text_llm default in a single process).
        * Otherwise the router walks the active profile's tiers.

    Args:
        messages: OpenAI-compatible message list (non-empty).
        profile: Optional override for ``MODEL_PROFILE``.
        family:  Optional single-family pin (skips tier walk).
        role:    Optional single-role pin (must be passed with ``family``).
        temperature: Sampling temperature in [0.0, 2.0]. Default 0.2.
        max_tokens: Max completion tokens. Default 1024.
        metadata: Optional dict merged into every log event.

    Returns:
        An :class:`LLMResponse`.

    Raises:
        ModelExcludedError: If any tier model matches the exclusion patterns.
        ValueError: If ``messages`` is empty.
        LLMCallError: If every tier has failed.

    Example:
        >>> response = call_llm([{"role": "user", "content": "What is 2+2?"}])
        >>> response.model
        'vertex_ai/gemini-3.5-flash'
        >>> response.tier
        1
    """
    if not messages:
        raise ValueError("call_llm() requires a non-empty `messages` list")

    active_profile = profile or _active_profile()
    log_metadata: dict[str, Any] = dict(metadata or {})
    log_metadata["model_profile"] = active_profile

    # Pin mode: one call against one specific (family, role) entry.
    if family is not None and role is not None:
        entry = model_for(family, role, profile=active_profile)
        if entry is None or entry.litellm_alias is None:
            raise ValueError(
                f"No registry entry for ({family}, {role}) under profile={active_profile!r}"
            )
        _assert_model_allowed(entry.litellm_alias)
        return _attempt(
            entry=entry,
            tier_idx=1,
            role=role,
            retry_budget=TIER_RETRY_BUDGETS.get(role, 1),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            log_metadata=log_metadata,
        )

    # Tier-walk mode: resolves the active profile's tiers in order.
    tiers = DEV_TIERS if active_profile == "dev" else HACKATHON_TIERS
    attempts: list[TierAttempt] = []
    overall_start = time.monotonic()

    for tier_idx, (tier_family, tier_role) in enumerate(tiers, start=1):
        entry = model_for(tier_family, tier_role, profile=active_profile)
        if entry is None or entry.litellm_alias is None:
            continue
        _assert_model_allowed(entry.litellm_alias)
        try:
            return _attempt(
                entry=entry,
                tier_idx=tier_idx,
                role=tier_role,
                retry_budget=TIER_RETRY_BUDGETS.get(tier_role, 1),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                log_metadata=log_metadata,
                attempts_accumulator=attempts,
            )
        except LLMCallError as e:
            attempts.extend(e.attempts)
            continue

    total_ms = int((time.monotonic() - overall_start) * 1000)
    logger.error(
        "llm.all_tiers_failed",
        llm_latency_ms=total_ms,
        llm_tiers_attempted=[(f, r) for f, r in tiers],
        **log_metadata,
    )
    raise LLMCallError(
        f"All tiers failed for call_llm(); see attempts[] for details.",
        attempts=attempts,
    )


def _attempt(
    *,
    entry: ModelRegistryEntry,
    tier_idx: int,
    role: str,
    retry_budget: int,
    messages: Sequence[Message],
    temperature: float,
    max_tokens: int,
    log_metadata: dict[str, Any],
    attempts_accumulator: list[TierAttempt] | None = None,
) -> LLMResponse:
    """Run one entry with retries + per-attempt logging."""
    router = _build_router()
    attempts: list[TierAttempt] = attempts_accumulator if attempts_accumulator is not None else []
    overall_start = time.monotonic()
    router_name = f"tier-{tier_idx}"

    for attempt_no in range(retry_budget):
        attempt_start = time.monotonic()
        error_msg = ""
        try:
            response = router.completion(
                model=router_name,
                messages=list(messages),
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
            tokens_out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
            attempt_ms = int((time.monotonic() - attempt_start) * 1000)
            attempts.append(TierAttempt(
                tier=tier_idx,
                family=entry.family,
                role=role,
                model=entry.litellm_alias or entry.key,
                backend=entry.backend,
                latency_ms=attempt_ms,
                succeeded=True,
            ))
            total_ms = int((time.monotonic() - overall_start) * 1000)
            _emit_invocation_log(
                tier=tier_idx,
                role=role,
                entry=entry,
                latency_ms=total_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                log_metadata=log_metadata,
            )
            return LLMResponse(
                content=content,
                model=entry.litellm_alias or entry.key,
                backend=entry.backend,
                tier=tier_idx,
                family=entry.family,
                role=role,
                latency_ms=total_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                attempts=attempts,
            )
        except Exception as e:  # noqa: BLE001 — broad catch on purpose
            attempt_ms = int((time.monotonic() - attempt_start) * 1000)
            error_msg = f"{type(e).__name__}: {e}"
            attempts.append(TierAttempt(
                tier=tier_idx,
                family=entry.family,
                role=role,
                model=entry.litellm_alias or entry.key,
                backend=entry.backend,
                latency_ms=attempt_ms,
                error=error_msg,
                succeeded=False,
            ))
            logger.warning(
                "llm.invocation_failed",
                llm_tier=str(tier_idx),
                llm_model=entry.litellm_alias,
                llm_backend=entry.backend,
                llm_latency_ms=attempt_ms,
                llm_attempt=attempt_no + 1,
                llm_retry_budget=retry_budget,
                llm_error=error_msg,
                **log_metadata,
            )
            if attempt_no + 1 < retry_budget:
                backoff = BACKOFF_BASE_SECONDS * (2 ** attempt_no)
                time.sleep(backoff)
                continue
            break

    # All retries on this tier exhausted.
    total_ms = int((time.monotonic() - overall_start) * 1000)
    raise LLMCallError(
        f"Tier {tier_idx} ({entry.key}) exhausted its retry budget.",
        attempts=attempts,
    )


# ---------------------------------------------------------------------------
# Logging helper.
# ---------------------------------------------------------------------------


def _emit_invocation_log(
    *,
    tier: int,
    role: str,
    entry: ModelRegistryEntry,
    latency_ms: int,
    tokens_in: int,
    tokens_out: int,
    log_metadata: dict[str, Any],
) -> None:
    """Emit the canonical ``llm.invocation`` structlog event."""
    payload: dict[str, Any] = {
        "llm.tier": str(tier),
        "llm.role": role,
        "llm.model_key": entry.key,
        "llm.model_alias": entry.litellm_alias,
        "llm.backend": entry.backend,
        "llm.latency_ms": latency_ms,
        "llm.tokens_in": tokens_in,
        "llm.tokens_out": tokens_out,
    }
    if tier > 1:
        payload["llm.fallback_reason"] = f"tier-{tier - 1}_failed_or_timeout"
    payload.update(log_metadata)
    logger.info("llm.invocation", **payload)


def _active_profile() -> ModelProfile:
    raw = os.environ.get("MODEL_PROFILE", "hackathon").strip().lower()
    if raw not in {"hackathon", "dev"}:
        logger.warning("unknown_model_profile_falling_back", extra={"got": raw})
        return "hackathon"
    return raw  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Utility helpers.
# ---------------------------------------------------------------------------


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    """Best-effort USD cost estimate (placeholder pricing)."""
    pricing = {
        "gemini-3.5-flash": (0.000075, 0.0003),
        "gemini-3.5-flash-aistudio": (0.000075, 0.0003),
        "gemma-4-26b-a4b": (0.0, 0.0),  # local
        "minimax-m3": (0.0002, 0.0006),
    }
    in_rate, out_rate = pricing.get(model, (0.0, 0.0))
    return round((tokens_in / 1000.0) * in_rate + (tokens_out / 1000.0) * out_rate, 6)


def normalise_messages(messages: Sequence[Message]) -> list[Message]:
    out: list[Message] = []
    for msg in messages:
        if "role" not in msg or "content" not in msg:
            raise ValueError(f"Message must have `role` and `content` keys; got {msg!r}")
        if msg["role"] not in {"system", "user", "assistant"}:
            raise ValueError(f"Invalid message role: {msg['role']!r}")
        out.append({"role": msg["role"], "content": str(msg["content"])})
    return out


def parse_model_string(model: str) -> tuple[str | None, str]:
    """Split a LiteLLM model string into ``(provider, name)``."""
    if "/" in model:
        provider, _, name = model.partition("/")
        return provider, name
    return None, model


__all__ = [
    "BACKOFF_BASE_SECONDS",
    "DEV_TIERS",
    "HACKATHON_TIERS",
    "LLMCallError",
    "LLMResponse",
    "Message",
    "ModelExcludedError",
    "TIER_RETRY_BUDGETS",
    "TIER_TIMEOUT_SECONDS",
    "TierAttempt",
    "TierTimeoutError",
    "call_llm",
    "estimate_cost_usd",
    "normalise_messages",
    "parse_model_string",
    "reset_router",
]
