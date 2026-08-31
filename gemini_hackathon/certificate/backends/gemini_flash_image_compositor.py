"""Gemini Flash Image compositor (Google's Nano-Banana)."""

from __future__ import annotations

import logging
import time
from typing import Any

from . import CompositorResult, build_prompt_from_concept
from .compositor_base import _make_stub_result

logger = logging.getLogger(__name__)


class GeminiFlashImageCompositor:
    """Gemini 2.5 Flash Image (Nano-Banana) via LiteLLM (Vertex AI)."""

    backend: str = "gemini_flash_image"
    model_key: str = "gemini-2.5-flash-image"

    def is_available(self) -> bool:
        try:
            import litellm

            return True
        except ImportError:
            return False

    def render(self, *, concept: Any, seed: int | None = None) -> CompositorResult:
        started = time.monotonic()
        if not self.is_available():
            return _make_stub_result(self.backend, self.model_key, seed=seed or 0, duration_ms=0)
        try:
            from gemini_hackathon.assets.litellm_image import (
                LiteLLMImageRequest,
                generate_with_litellm,
            )

            prompt = build_prompt_from_concept(concept)
            actual_seed = seed or int(time.time() * 1000) % (1 << 31)
            result = generate_with_litellm(
                LiteLLMImageRequest(
                    prompt=prompt,
                    model=self.model_key,
                    seed=actual_seed,
                )
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            if not result.b64_images:
                return _make_stub_result(
                    self.backend, self.model_key, seed=actual_seed, duration_ms=duration_ms
                )
            return CompositorResult(
                backend=self.backend,
                model_key=self.model_key,
                image_b64=result.b64_images[0],
                seed=actual_seed,
                duration_ms=duration_ms,
                cost_usd=result.cost_usd or 0.01,
                success=True,
                metadata={"model": self.model_key, "latency_ms": result.duration_ms},
            )
        except Exception as exc:
            logger.warning("Gemini Flash Image render failed: %s", exc)
            return _make_stub_result(self.backend, self.model_key, seed=seed or 0, duration_ms=0)


__all__ = ["GeminiFlashImageCompositor"]
