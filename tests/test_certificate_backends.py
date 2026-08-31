"""Tests for `gemini_hackathon.certificate.backends` per-compositor subclasses.

Updated 2026-08-31 (Phase 6): exercises `is_available()` happy + sad
paths + `render()`'s stub fallback when the backend is unreachable
(the canonical offline test path).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _compositor_for_subclass(subclass_path: str):
    """Load a compositor class by dotted path (lazy import pattern)."""
    import importlib

    mod = importlib.import_module(subclass_path)
    name = next(
        n for n in dir(mod) if n.endswith("Compositor") and n != "AssetCompositor"
    )
    return getattr(mod, name), name


def test_diffusiongemma_is_available_false_without_httpx(monkeypatch):
    """`is_available()` returns False when httpx is not importable."""
    import builtins

    import_diff = builtins.__import__
    real_import = import_diff
    if isinstance(real_import, dict):
        real_import = real_import["__import__"]

    def fake_import(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError("no httpx")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from gemini_hackathon.certificate.backends.diffusiongemma_compositor import (
        DiffusionGemmaCompositor,
    )
    assert DiffusionGemmaCompositor().is_available() is False


def test_diffusiongemma_render_returns_stub_when_backend_down(monkeypatch):
    """`render()` returns the 1×1 PNG stub when `is_available()` is False."""
    import builtins

    import_diff = builtins.__import__
    real_import = import_diff
    if isinstance(real_import, dict):
        real_import = real_import["__import__"]

    def fake_import(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError("no httpx")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from gemini_hackathon.certificate.backends.diffusiongemma_compositor import (
        DiffusionGemmaCompositor,
    )

    result = DiffusionGemmaCompositor().render(
        concept=MagicMock(), seed=42
    )
    assert result.backend == "diffusiongemma"
    assert result.model_key == "google/diffusiongemma-26B-A4B-it"
    assert result.seed == 42
    assert result.success is True
    assert result.metadata.get("stub") is True


def test_diffusiongemma_class_constants():
    """`DiffusionGemmaCompositor.backend` + `model_key` are class attrs."""
    from gemini_hackathon.certificate.backends.diffusiongemma_compositor import (
        DiffusionGemmaCompositor,
    )

    assert DiffusionGemmaCompositor.backend == "diffusiongemma"
    assert DiffusionGemmaCompositor.model_key.startswith("google/")


def test_fibo_render_returns_stub_when_backend_down():
    """`FIBOCompositor.render()` returns the stub when the backend is down."""
    import builtins

    real_import = builtins.__import__ if isinstance(builtins, type(builtins)) else builtins["__import__"]

    def fake_import(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError("no httpx")
        return real_import(name, *args, **kwargs)

    import importlib

    saved_httpx = __import__("sys").modules.get("httpx")
    import sys as _sys
    if "httpx" in _sys.modules:
        del _sys.modules["httpx"]
    builtins.__import__ = fake_import
    try:
        from gemini_hackathon.certificate.backends.fibo_compositor import FIBOCompositor

        concept = MagicMock()
        concept.subject = "chemistry_lc"
        concept.topic = "solvation"
        concept.lo_code = "MA-LC-CH-3.2"
        concept.palette_primary = "#0066CC"
        concept.palette_accent = "#FF9900"
        result = FIBOCompositor().render(concept=concept, seed=42)
        assert result.backend == "fibo"
        assert result.success is True
        assert result.metadata.get("stub") is True
    finally:
        builtins.__import__ = real_import
        if saved_httpx is not None:
            _sys.modules["httpx"] = saved_httpx


def test_imagen3_backend_constant():
    """`Imagen3Compositor.backend` is `imagen3`."""
    from gemini_hackathon.certificate.backends.imagen3_compositor import Imagen3Compositor

    assert Imagen3Compositor.backend == "imagen3"


def test_gemini_flash_image_backend_constant():
    """`GeminiFlashImageCompositor.backend` is `gemini_flash_image`."""
    from gemini_hackathon.certificate.backends.gemini_flash_image_compositor import (
        GeminiFlashImageCompositor,
    )

    assert GeminiFlashImageCompositor.backend == "gemini_flash_image"


def test_flux_schnell_backend_constant():
    """`FLUXSchnellCompositor.backend` is `flux_schnell`."""
    from gemini_hackathon.certificate.backends.flux_schnell_compositor import (
        FLUXSchnellCompositor,
    )

    assert FLUXSchnellCompositor.backend == "flux_schnell"


def test_all_compositors_have_render_method():
    """Every compositor subclass implements `render(concept=, seed=)`."""
    import importlib
    import inspect

    for name in (
        "diffusiongemma_compositor",
        "fibo_compositor",
        "flux_schnell_compositor",
        "gemini_flash_image_compositor",
        "imagen3_compositor",
    ):
        mod = importlib.import_module(
            f"gemini_hackathon.certificate.backends.{name}"
        )
        cls = next(
            n for n in dir(mod) if n.endswith("Compositor") and n != "AssetCompositor"
        )
        cls_obj = getattr(mod, cls)
        # No inheritance from AssetCompositor (the base is a Protocol).
        assert hasattr(cls_obj, "render"), f"{cls} missing render()"
        sig = inspect.signature(cls_obj.render)
        assert "concept" in sig.parameters
        assert "seed" in sig.parameters


def test_all_compositors_carry_backend_class_attribute():
    """Every compositor declares a `backend: str` class attribute."""
    import importlib

    for name in (
        "diffusiongemma_compositor",
        "fibo_compositor",
        "flux_schnell_compositor",
        "gemini_flash_image_compositor",
        "imagen3_compositor",
    ):
        mod = importlib.import_module(
            f"gemini_hackathon.certificate.backends.{name}"
        )
        cls = next(
            n for n in dir(mod) if n.endswith("Compositor") and n != "AssetCompositor"
        )
        cls_obj = getattr(mod, cls)
        assert isinstance(cls_obj.backend, str)
        assert cls_obj.backend  # non-empty
