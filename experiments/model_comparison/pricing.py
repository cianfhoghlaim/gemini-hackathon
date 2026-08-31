"""experiments.model_comparison.pricing — per-model pricing table (USD/M tokens).

Phase 5a of the multi-stage plan (see AGENTS.md). Single source of truth
for the cost calculation in ``metrics.cost_usd()``.

Public API:
    ``PRICING_PER_MILLION_TOKENS[model_key] -> {"input": float, "output": float}``
    ``LOCAL_GPU_HOURLY_USD`` — amortised T4 cost (used for local-model
        cost calculation: $0.50/hr / throughput_tokens_per_sec * 3600)
    ``LOCAL_GPU_THROUGHPUT_TOKENS_PER_SEC`` — pessimistic 50 tok/s for a
        A100 / T4 quantised inference (the canonical Unsloth Studio target)
"""

from __future__ import annotations

#: Pricing per million tokens. ``None`` means the model is local (cost = 0
#: for the API call itself, but we add amortised GPU cost below).
PRICING_PER_MILLION_TOKENS: dict[str, dict[str, float | None]] = {
    "gemini-3.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-3.5-pro": {"input": 1.25, "output": 5.00},
    "minimax-m3": {"input": None, "output": None},  # dev-only — see model_registry
    "unsloth/gemma-4-26b-a4b": {"input": None, "output": None},
    "unsloth/gemma-2-9b": {"input": None, "output": None},
}

#: Amortised GPU cost for local models. $0.50/hr on a T4 (Vertex AI spot
#: pricing floor). Conservative — actual Unsloth Studio throughput is closer
#: to $0.20/hr on a 4090.
LOCAL_GPU_HOURLY_USD: float = 0.50

#: Conservative throughput for a 4-bit quantised Gemma 4 26B on T4/A100.
#: 50 tokens/sec = 180,000 tokens/hr; cost = $0.50 / 180k = $0.0028/M tokens.
LOCAL_GPU_THROUGHPUT_TOKENS_PER_SEC: float = 50.0

#: Per-docling page overhead (only when Docling is used; Phase 2b defaults
#: to pypdfium2 which is free).
DOCLING_PER_PAGE_USD: float = 0.001


def is_local_model(model_key: str) -> bool:
    """Return True when the model is local (Unsloth Studio) — cost = amortised GPU."""
    return model_key in {
        "unsloth/gemma-4-26b-a4b",
        "unsloth/gemma-2-9b",
    }


def amortised_local_cost_per_million_tokens(model_key: str) -> float:
    """Compute the amortised local-model cost per M tokens.

    Local models have no per-token API cost, but the GPU they run on
    consumes power. We amortise the hourly GPU cost over the assumed
    throughput to get a per-token cost that's honest about the
    hardware footprint.
    """
    if not is_local_model(model_key):
        return 0.0
    tokens_per_hour = LOCAL_GPU_THROUGHPUT_TOKENS_PER_SEC * 3600.0
    return LOCAL_GPU_HOURLY_USD / tokens_per_hour * 1_000_000


__all__ = [
    "DOCLING_PER_PAGE_USD",
    "LOCAL_GPU_HOURLY_USD",
    "LOCAL_GPU_THROUGHPUT_TOKENS_PER_SEC",
    "PRICING_PER_MILLION_TOKENS",
    "amortised_local_cost_per_million_tokens",
    "is_local_model",
]
