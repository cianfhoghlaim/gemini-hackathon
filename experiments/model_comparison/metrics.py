"""experiments.model_comparison.metrics — cost / time / accuracy / schema metrics.

Phase 5a of the multi-stage plan (see AGENTS.md).

Public API:
  ``cost_usd(model_key, tokens_in, tokens_out)`` — total USD cost
    for one model invocation.
  ``field_level_f1(predicted, ground_truth, tolerance=2)`` — F1 across
    field-level values with Levenshtein tolerance for typo forgiveness.
  ``schema_validity(parsed)`` — True when the parsed value is a non-empty
    dict (the BAML stub always returns a valid dict; a real LLM call
    can return text or partial JSON).
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

try:
    from .pricing import (
        PRICING_PER_MILLION_TOKENS,
        amortised_local_cost_per_million_tokens,
        is_local_model,
    )
except ImportError:  # pragma: no cover — standalone-load fallback
    import importlib.util as _iu, sys as _sys, pathlib as _pl
    _spec = _iu.spec_from_file_location(
        "_pricing_mod",
        _pl.Path(__file__).resolve().parent / "pricing.py",
    )
    _p = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_p)
    PRICING_PER_MILLION_TOKENS = _p.PRICING_PER_MILLION_TOKENS
    amortised_local_cost_per_million_tokens = _p.amortised_local_cost_per_million_tokens
    is_local_model = _p.is_local_model


def cost_usd(
    model_key: str,
    tokens_in: int,
    tokens_out: int,
) -> float:
    """Total USD cost for one model invocation.

    Local models: cost = amortised GPU cost only.
    API models: cost = (input_pricing * tokens_in/1M) + (output_pricing * tokens_out/1M).
    """
    if is_local_model(model_key):
        total = tokens_in + tokens_out
        per_m = amortised_local_cost_per_million_tokens(model_key)
        return total / 1_000_000.0 * per_m
    pricing = PRICING_PER_MILLION_TOKENS.get(model_key)
    if not pricing or pricing["input"] is None or pricing["output"] is None:
        return 0.0  # unpriced (e.g. dev-only model not in the table)
    in_cost = pricing["input"] / 1_000_000.0 * tokens_in
    out_cost = pricing["output"] / 1_000_000.0 * tokens_out
    return in_cost + out_cost


def _normalise(value: Any) -> str:
    """Lowercase + collapse whitespace for string comparison."""
    if value is None:
        return ""
    return " ".join(str(value).lower().split())


def _similar(a: str, b: str) -> float:
    """SequenceMatcher ratio in [0.0, 1.0]."""
    return SequenceMatcher(None, a, b).ratio()


def field_level_f1(
    predicted: dict[str, Any] | None,
    ground_truth: dict[str, Any] | None,
    *,
    tolerance: float = 0.85,
) -> float:
    """F1 over field-level values with a similarity tolerance.

    Each field is compared via SequenceMatcher; a field "matches" when
    similarity >= ``tolerance`` (default 0.85 = 15% Levenshtein tolerance).
    F1 is computed across the union of predicted + ground-truth field names
    (a field missing from either side is a miss).
    """
    if not predicted or not ground_truth:
        return 0.0
    pred_norm = {_normalise(k): _normalise(v) for k, v in predicted.items()}
    truth_norm = {_normalise(k): _normalise(v) for k, v in ground_truth.items()}
    keys = set(pred_norm.keys()) | set(truth_norm.keys())
    if not keys:
        return 0.0
    tp = 0
    fp = 0
    fn = 0
    for k in keys:
        p = pred_norm.get(k, "")
        t = truth_norm.get(k, "")
        if not p and not t:
            continue
        if _similar(p, t) >= tolerance:
            tp += 1
        elif p:
            fp += 1
        else:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def schema_validity(parsed: Any) -> bool:
    """True when ``parsed`` looks like a valid extraction result.

    The BAML stub returns a non-empty dict with at least one key. Real
    LLM calls can return text, partial JSON, or a structured object —
    this heuristic accepts dicts and rejects everything else.
    """
    if not isinstance(parsed, dict):
        return False
    return len(parsed) > 0


__all__ = [
    "cost_usd",
    "field_level_f1",
    "schema_validity",
]