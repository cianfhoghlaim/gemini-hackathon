"""Tests for `gemini_hackathon.certificate.backends` — the 7 compositor
backends (FIBO + DiffusionGemma + FLUX.1 + FLUX.2 + Gemini Flash Image +
Imagen 3 + Imagen 4) + the `CompositorResult` + `build_prompt_from_concept`
helpers.

Updated 2026-08-31 (Phase 6): exercises the prompt builder + the
`_make_stub_result` helper. Tests for the per-backend render() methods
require PIL + a live model invocation (out of scope for the offline
test suite).
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
from unittest.mock import MagicMock

import pytest

from gemini_hackathon.certificate.backends import (
    CompositorResult,
    build_prompt_from_concept,
)
from gemini_hackathon.certificate.backends.compositor_base import (
    _make_stub_result,
)


def test_compositor_result_carries_eight_fields():
    """`CompositorResult` has 9 dataclass fields."""
    fields = {f.name for f in dataclasses.fields(CompositorResult)}
    expected = {"backend", "model_key", "image_b64", "seed", "duration_ms",
                "cost_usd", "success", "error", "metadata"}
    assert fields == expected


def test_compositor_result_defaults_metadata_to_empty_dict():
    """`metadata` defaults to an empty dict (so callers can mutate it freely)."""
    out = CompositorResult(
        backend="stub",
        model_key="stub",
        image_b64="",
        seed=0,
        duration_ms=0,
        cost_usd=0.0,
        success=True,
    )
    assert out.metadata == {}
    assert out.error is None


def test_compositor_result_default_error_is_none():
    """`error` defaults to None; only populated when `success` is False."""
    err_out = CompositorResult(
        backend="x", model_key="y", image_b64="", seed=0,
        duration_ms=0, cost_usd=0.0, success=False, error="bad",
    )
    assert err_out.error == "bad"


def test_make_stub_result_returns_1x1_png():
    """`_make_stub_result` returns a base64-encoded 1×1 PNG (~70 chars)."""
    result = _make_stub_result(
        backend="stub", model_key="stub/1x1", seed=42, duration_ms=0
    )
    assert result.backend == "stub"
    assert result.model_key == "stub/1x1"
    assert result.seed == 42
    assert result.success is True
    assert result.cost_usd == 0.0
    assert result.metadata.get("stub") is True
    # The base64 should decode back to the canonical PNG header.
    decoded = base64.b64decode(result.image_b64)
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


def test_make_stub_result_duration_passes_through():
    """`_make_stub_result` carries the supplied `duration_ms` through verbatim."""
    result = _make_stub_result(
        backend="s", model_key="s/k", seed=1, duration_ms=1234
    )
    assert result.duration_ms == 1234


def test_build_prompt_from_concept_with_minimal_concept():
    """`build_prompt_from_concept` doesn't crash on a bare-None concept."""
    class _Bare:
        pass
    out = build_prompt_from_concept(_Bare())
    assert "Educational asset" in out
    assert "subject" in out  # the default value


def test_build_prompt_from_concept_includes_subject_and_topic():
    """The prompt surfaces the concept's subject + topic on dedicated lines."""
    concept = MagicMock()
    concept.subject = "chemistry"
    concept.topic = "electrolysis"
    concept.lo_text = "Apply Faraday's law to electrolytic cells"
    concept.visual_cue = "blue sparks"
    concept.diagram_type = "circuit"
    concept.palette_primary = "#0066CC"
    concept.palette_accent = "#FF9900"

    out = build_prompt_from_concept(concept)
    assert "chemistry" in out
    assert "electrolysis" in out
    assert "Apply Faraday's law" in out
    assert "blue sparks" in out
    assert "circuit" in out
    assert "#0066CC" in out
    assert "#FF9900" in out


def test_build_prompt_from_concept_uses_getattr_defaults_for_missing_fields():
    """`getattr` defaults keep the builder robust to missing concept fields."""
    concept = MagicMock(spec=[])  # no attributes at all
    out = build_prompt_from_concept(concept)
    # All falls back to the defaults.
    assert "subject" in out
    assert "topic" in out
    assert "diagram" in out  # default diagram_type


def test_compositor_result_is_not_a_frozen_dataclass():
    """`CompositorResult` is mutable (callers set `error` after construction)."""
    out = CompositorResult(
        backend="x", model_key="y", image_b64="", seed=0,
        duration_ms=0, cost_usd=0.0, success=True,
    )
    # Mutating a non-frozen dataclass is allowed.
    out.error = "late-bound"
    out.metadata["extra"] = "value"
    assert out.error == "late-bound"
    assert out.metadata["extra"] == "value"
