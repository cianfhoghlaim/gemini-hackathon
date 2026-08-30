"""test_model_comparison_harness.py — Phase 5a verification of the harness.

Tests:
  1. ``cost_usd`` for Gemini 3.5 Flash (API), Pro (API), and 2 local models.
  2. ``field_level_f1`` with exact match + tolerance + missing fields.
  3. ``schema_validity`` for dict / list / string / empty.
  4. ``run_one`` with a stub invoker (cost, F1, schema_validity, latency).
  5. ``run_all`` iterates over (model × sample) pairs.
  6. ``is_local_model`` + ``amortised_local_cost_per_million_tokens``.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_base = pathlib.Path(__file__).resolve().parent.parent / "experiments" / "model_comparison"
pricing = _load("_test_pricing", _base / "pricing.py")
metrics = _load("_test_metrics", _base / "metrics.py")
runner = _load("_test_runner", _base / "runner.py")


def test_is_local_model() -> None:
    assert pricing.is_local_model("unsloth/gemma-4-26b-a4b") is True
    assert pricing.is_local_model("unsloth/gemma-2-9b") is True
    assert pricing.is_local_model("gemini-3.5-flash") is False
    assert pricing.is_local_model("gemini-3.5-pro") is False
    assert pricing.is_local_model("minimax-m3") is False  # unpriced, treated as remote


def test_amortised_local_cost_positive() -> None:
    per_m = pricing.amortised_local_cost_per_million_tokens("unsloth/gemma-4-26b-a4b")
    # 0.50 USD/hr / (50 tok/s * 3600) * 1e6 = 2.777... USD per million tokens
    assert 2.0 < per_m < 4.0


def test_cost_usd_gemini_flash() -> None:
    # 1000 input + 500 output tokens
    # 1000/1e6 * 0.075 + 500/1e6 * 0.30 = 0.000075 + 0.000150 = 0.000225
    cost = metrics.cost_usd("gemini-3.5-flash", 1000, 500)
    assert abs(cost - 0.000225) < 1e-9


def test_cost_usd_gemini_pro() -> None:
    # 1000 input + 500 output tokens
    # 1000/1e6 * 1.25 + 500/1e6 * 5.00 = 0.00125 + 0.0025 = 0.00375
    cost = metrics.cost_usd("gemini-3.5-pro", 1000, 500)
    assert abs(cost - 0.00375) < 1e-9


def test_cost_usd_local_model() -> None:
    # Local models: amortised GPU cost.
    cost = metrics.cost_usd("unsloth/gemma-4-26b-a4b", 1_000_000, 1_000_000)
    per_m = pricing.amortised_local_cost_per_million_tokens("unsloth/gemma-4-26b-a4b")
    # cost = 2M tokens * per_m / 1M = 2 * per_m
    assert abs(cost - 2 * per_m) < 1e-9


def test_cost_usd_unpriced_returns_zero() -> None:
    assert metrics.cost_usd("minimax-m3", 1000, 500) == 0.0  # dev-only, no entry


def test_field_level_f1_exact_match() -> None:
    pred = {"subject": "mathematics", "language": "en"}
    truth = {"subject": "mathematics", "language": "en"}
    assert metrics.field_level_f1(pred, truth) == 1.0


def test_field_level_f1_no_match() -> None:
    pred = {"subject": "chemistry"}
    truth = {"subject": "mathematics"}
    assert metrics.field_level_f1(pred, truth) == 0.0


def test_field_level_f1_with_typo_tolerance() -> None:
    pred = {"subject": "mathematics", "language": "en"}
    truth = {"subject": "mathematcs", "language": "en"}  # 1-letter typo
    # Default tolerance is 0.85 — "mathematics" vs "mathematcs" should pass
    f1 = metrics.field_level_f1(pred, truth, tolerance=0.85)
    assert f1 > 0.5


def test_field_level_f1_missing_fields() -> None:
    pred = {"subject": "mathematics"}  # missing language
    truth = {"subject": "mathematics", "language": "en"}
    f1 = metrics.field_level_f1(pred, truth)
    assert 0.0 < f1 < 1.0


def test_field_level_f1_empty_inputs() -> None:
    assert metrics.field_level_f1({}, {}) == 0.0
    assert metrics.field_level_f1(None, {"x": 1}) == 0.0
    assert metrics.field_level_f1({"x": 1}, None) == 0.0


def test_schema_validity() -> None:
    assert metrics.schema_validity({"a": 1}) is True
    assert metrics.schema_validity({}) is False
    assert metrics.schema_validity([]) is False
    assert metrics.schema_validity("text") is False
    assert metrics.schema_validity(None) is False


def test_run_one_with_stub_invoker() -> None:
    sample = runner.EvalSample(
        sample_id="math-ie-1",
        pdf_path="x.pdf",
        subject="mathematics",
        language="en",
        md_text="# Mathematics\n## Page 1\n\nAlgebra stub",
        ground_truth={
            "subject_slug": "mathematics",
            "language": "en",
        },
    )

    def stub_inv(model_key: str, prompt: str) -> tuple[str, int, int]:
        # Output valid JSON that matches ground_truth
        return (
            '{"subject_slug": "mathematics", "language": "en", "stub": true}',
            100,
            50,
        )

    result = runner.run_one("gemini-3.5-flash", sample, invoker=stub_inv)
    assert result.model == "gemini-3.5-flash"
    assert result.sample_id == "math-ie-1"
    assert result.tokens_in == 100
    assert result.tokens_out == 50
    assert result.schema_valid is True
    assert result.accuracy > 0.5  # 2 of 3 fields match
    assert result.cost_usd > 0  # gemini-3.5-flash has a price
    assert result.error == ""


def test_run_one_handles_invoker_failure() -> None:
    sample = runner.EvalSample(
        sample_id="x",
        pdf_path="x.pdf",
        subject="mathematics",
        language="en",
        md_text="",
        ground_truth={},
    )

    def bad_inv(model_key: str, prompt: str) -> tuple[str, int, int]:
        raise RuntimeError("simulated network failure")

    result = runner.run_one("gemini-3.5-flash", sample, invoker=bad_inv)
    assert result.error == "simulated network failure"
    assert result.schema_valid is False
    assert result.accuracy == 0.0
    assert result.tokens_in == 0


def test_run_all_iterates_pairs() -> None:
    samples = [
        runner.EvalSample(
            sample_id=f"s{i}",
            pdf_path=f"x{i}.pdf",
            subject="mathematics",
            language="en",
            md_text="",
            ground_truth={"x": 1},
        )
        for i in range(3)
    ]
    models = ["gemini-3.5-flash", "unsloth/gemma-4-26b-a4b"]

    def stub_inv(model_key, prompt):
        return "{}", 10, 10

    results = runner.run_all(samples, models, invoker=stub_inv)
    assert len(results) == 6  # 3 samples × 2 models
    models_seen = {r.model for r in results}
    assert models_seen == set(models)
    samples_seen = {r.sample_id for r in results}
    assert samples_seen == {f"s{i}" for i in range(3)}


def test_run_alias_matches_run_all() -> None:
    assert runner.run is runner.run_all


def test_default_invoker_falls_back_to_stub_when_no_call_llm() -> None:
    """In test env without gemini_hackathon.call_llm, default_invoker
    returns a stub. (Can't easily test the no-call_llm path since the
    project DOES have call_llm — the test below verifies the stub path
    in the runner directly via _stub_invoker.)
    """
    content, tin, tout = runner._stub_invoker("gemini-3.5-flash", "long prompt " * 10)
    parsed = runner._try_parse(content)
    assert parsed is not None
    assert parsed["stub"] is True
    assert parsed["model"] == "gemini-3.5-flash"
    assert tin > 0 and tout > 0


def test_try_parse_handles_json_fences() -> None:
    """LLM responses sometimes wrap JSON in ```json fences."""
    content = '```json\n{"a": 1, "b": "two"}\n```'
    parsed = runner._try_parse(content)
    assert parsed == {"a": 1, "b": "two"}


def test_try_parse_returns_none_for_invalid_json() -> None:
    assert runner._try_parse("not json at all") is None
    assert runner._try_parse("") is None


def test_eval_sample_dataclass_serializes() -> None:
    sample = runner.EvalSample(
        sample_id="x",
        pdf_path="x.pdf",
        subject="mathematics",
        language="en",
        md_text="text",
        ground_truth={"k": 1},
    )
    assert sample.sample_id == "x"
    assert sample.ground_truth == {"k": 1}