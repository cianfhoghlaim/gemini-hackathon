"""DiffusionGemma compositor (the Google first-party image-gen Gemma)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from . import CompositorResult, build_prompt_from_concept
from .compositor_base import _make_stub_result

logger = logging.getLogger(__name__)


class DiffusionGemmaCompositor:
    """The DiffusionGemma 26B-A4B-it compositor (via Unsloth Studio)."""

    backend: str = "diffusiongemma"
    model_key: str = "google/diffusiongemma-26B-A4B-it"

    def is_available(self) -> bool:
        try:
            import httpx

            base_url = os.environ.get("UNSLOTH_BASE_URL", "http://127.0.0.1:8888/v1").rstrip("/v1")
            r = httpx.get(f"{base_url}/models", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def render(self, *, concept: Any, seed: int | None = None) -> CompositorResult:
        started = time.monotonic()
        if not self.is_available():
            return _make_stub_result(self.backend, self.model_key, seed=seed or 0, duration_ms=0)
        try:
            import httpx

            base_url = os.environ.get("UNSLOTH_BASE_URL", "http://127.0.0.1:8888/v1")
            api_key = os.environ.get("UNSLOTH_API_KEY", "sk-unsloth-placeholder")
            actual_seed = seed or int(time.time() * 1000) % (1 << 31)
            prompt = build_prompt_from_concept(concept)
            resp = httpx.post(
                f"{base_url.rstrip('/v1')}/images/generations",
                json={
                    "model": self.model_key,
                    "prompt": prompt,
                    "seed": actual_seed,
                    "size": "1024x1024",
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=180.0,
            )
            resp.raise_for_status()
            out = resp.json()
            image_b64 = out.get("data", [{}])[0].get("b64_json", "")
            duration_ms = int((time.monotonic() - started) * 1000)
            return CompositorResult(
                backend=self.backend,
                model_key=self.model_key,
                image_b64=image_b64,
                seed=actual_seed,
                duration_ms=duration_ms,
                cost_usd=0.0,  # Unsloth is local
                success=True,
                metadata={"unsloth_url": base_url},
            )
        except Exception as exc:
            logger.warning("DiffusionGemma render failed: %s", exc)
            return _make_stub_result(self.backend, self.model_key, seed=seed or 0, duration_ms=0)


__all__ = ["DiffusionGemmaCompositor"]
