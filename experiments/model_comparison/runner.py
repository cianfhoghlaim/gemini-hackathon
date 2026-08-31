"""experiments.model_comparison.runner — Phase 5 model comparison harness.

Phase 5a of the multi-stage plan (see AGENTS.md). Orchestrates the
5-model evaluation across N=13 syllabus samples, producing
``EvalResult`` rows with cost / time / accuracy / schema metrics.

The harness delegates the actual model call to a ``ModelInvoker``
(callable: ``invoke(model_key, prompt) -> (content, tokens_in, tokens_out)``).
The default implementation uses ``gemini_hackathon.call_llm.call_llm``;
tests inject a stub ``ModelInvoker`` for determinism.

Public API:
  ``run_one(model_key, sample, invoker=default_invoker) -> EvalResult``
  ``run_all(samples, models, invoker=default_invoker) -> list[EvalResult]``
  ``run(samples, models, invoker=default_invoker) -> list[EvalResult]`` (alias)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

try:
    from .metrics import cost_usd, field_level_f1, schema_validity
except ImportError:  # pragma: no cover — standalone-load fallback
    import importlib.util as _iu
    import pathlib as _pl

    _spec = _iu.spec_from_file_location(
        "_metrics_mod",
        _pl.Path(__file__).resolve().parent / "metrics.py",
    )
    _m = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    cost_usd = _m.cost_usd
    field_level_f1 = _m.field_level_f1
    schema_validity = _m.schema_validity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EvalSample:
    """One syllabus sample to evaluate models against."""

    sample_id: str
    pdf_path: str
    subject: str
    language: str
    md_text: str
    ground_truth: dict[str, Any]


@dataclass
class EvalResult:
    """One (model × sample) result."""

    model: str
    sample_id: str
    cost_usd: float
    latency_ms: int
    tokens_in: int
    tokens_out: int
    accuracy: float  # field-level F1 against ground_truth
    schema_valid: bool
    raw_output: str = ""
    error: str = ""
    fetched_at: str = field(default_factory=lambda: "")


# ---------------------------------------------------------------------------
# Default invoker — delegates to call_llm()
# ---------------------------------------------------------------------------

ModelInvoker = Callable[[str, str], tuple[str, int, int]]


def default_invoker(model_key: str, prompt: str) -> tuple[str, int, int]:
    """Invoke ``gemini_hackathon.call_llm.call_llm`` and return (content, tokens_in, tokens_out).

    Falls back to a stub on ImportError (the canonical dev path).
    """
    try:
        from gemini_hackathon.call_llm import call_llm  # type: ignore[import-not-found]

        response = call_llm(
            [{"role": "user", "content": prompt}],
            family="text_llm",
            role=_role_for_model(model_key),
        )
        tokens_in = int(response.tokens_in or 0)
        tokens_out = int(response.tokens_out or 0)
        return str(response.content), tokens_in, tokens_out
    except ImportError:
        return _stub_invoker(model_key, prompt)
    except Exception as exc:
        logger.warning("runner.default_invoker_failed model=%s reason=%s", model_key, exc)
        return "", 0, 0


def _role_for_model(model_key: str) -> str:
    """Pick the LiteLLM router role for a model_key.

    Local models -> "fallback" (LiteLLM doesn't know about them, so
    we let the role-to-tier mapping in the registry resolve them).
    Gemini tiers -> "default" (Tier 1).
    MiniMax-M3 -> "default".
    """
    if model_key.startswith("unsloth/"):
        return "fallback"
    return "default"


def _stub_invoker(model_key: str, prompt: str) -> tuple[str, int, int]:
    """Deterministic stub used when the real call_llm is unavailable.

    Returns a minimal valid extraction that exercises the metrics path.
    """
    stub = {
        "stub": True,
        "model": model_key,
        "subject_slug": "unknown",
        "language": "en",
    }
    return json_dumps(stub), len(prompt) // 4, 100


def json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj)


# ---------------------------------------------------------------------------
# The harness
# ---------------------------------------------------------------------------


def run_one(
    model_key: str,
    sample: EvalSample,
    *,
    invoker: ModelInvoker = default_invoker,
) -> EvalResult:
    """Run ``model_key`` against ``sample``. Returns one ``EvalResult``."""
    prompt = _build_prompt(sample)
    started = time.monotonic()
    try:
        content, tokens_in, tokens_out = invoker(model_key, prompt)
    except Exception as exc:
        return EvalResult(
            model=model_key,
            sample_id=sample.sample_id,
            cost_usd=0.0,
            latency_ms=int((time.monotonic() - started) * 1000),
            tokens_in=0,
            tokens_out=0,
            accuracy=0.0,
            schema_valid=False,
            raw_output="",
            error=str(exc),
        )
    elapsed_ms = int((time.monotonic() - started) * 1000)

    parsed = _try_parse(content)
    accuracy = field_level_f1(parsed or {}, sample.ground_truth)
    valid = schema_validity(parsed)
    cost = cost_usd(model_key, tokens_in, tokens_out)
    return EvalResult(
        model=model_key,
        sample_id=sample.sample_id,
        cost_usd=cost,
        latency_ms=elapsed_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        accuracy=accuracy,
        schema_valid=valid,
        raw_output=content[:500],  # truncate to avoid huge log lines
    )


def _build_prompt(sample: EvalSample) -> str:
    """Build the canonical syllabus-extraction prompt for one sample."""
    return (
        f"You are an expert British Isles curriculum extractor.\n"
        f"Subject: {sample.subject}  Language: {sample.language}\n"
        f"\n"
        f"Syllabus text (Markdown, may be truncated):\n"
        f"--- BEGIN ---\n"
        f"{sample.md_text[:8000]}\n"
        f"--- END ---\n"
        f"\n"
        f"Extract the structured syllabus (modules, learning outcomes, "
        f"assessment objectives) as JSON."
    )


def _try_parse(content: str) -> dict[str, Any] | None:
    """Best-effort JSON parse. Returns the dict or None."""
    import json

    if not content:
        return None
    try:
        parsed = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        # Strip ```json fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").lstrip("json").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            parsed = json.loads(cleaned)
        except (TypeError, json.JSONDecodeError):
            return None
    if isinstance(parsed, dict):
        return parsed
    return None


def run_all(
    samples: Iterable[EvalSample],
    models: Iterable[str],
    *,
    invoker: ModelInvoker = default_invoker,
) -> list[EvalResult]:
    """Run every (model, sample) pair. Returns one ``EvalResult`` per pair."""
    samples_list = list(samples)
    models_list = list(models)
    results: list[EvalResult] = []
    total = len(models_list) * len(samples_list)
    started_all = time.monotonic()
    for i, model_key in enumerate(models_list, start=1):
        for j, sample in enumerate(samples_list, start=1):
            logger.info(
                "runner.eval progress=%d/%d model=%s sample=%s",
                (i - 1) * len(samples_list) + j,
                total,
                model_key,
                sample.sample_id,
            )
            results.append(run_one(model_key, sample, invoker=invoker))
    elapsed_ms = int((time.monotonic() - started_all) * 1000)
    logger.info("runner.complete results=%d elapsed_ms=%d", len(results), elapsed_ms)
    return results


# Alias for the canonical name in the plan.
run = run_all


__all__ = [
    "EvalResult",
    "EvalSample",
    "ModelInvoker",
    "default_invoker",
    "run",
    "run_all",
    "run_one",
]
