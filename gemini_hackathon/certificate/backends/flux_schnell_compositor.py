"""FLUX compositor (the Black Forest Labs flagship)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from . import CompositorResult, build_prompt_from_concept
from .compositor_base import AssetCompositor, _make_stub_result

logger = logging.getLogger(__name__)


class FLUXSchnellCompositor:
    """FLUX.1-schnell via InvokeAI (fast flagship)."""

    backend: str = "flux_schnell"
    model_key: str = "flux-schnell"

    def is_available(self) -> bool:
        try:
            import httpx
            base_url = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090/v1")
            r = httpx.get(f"{base_url}/models", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def render(self, *, concept: Any, seed: int | None = None) -> CompositorResult:
        return self._do_render(concept=concept, seed=seed)


class FLUX2DevCompositor:
    """FLUX.2-dev via InvokeAI (quality flagship)."""

    backend: str = "flux2_dev"
    model_key: str = "flux2-dev"

    def is_available(self) -> bool:
        try:
            import httpx
            base_url = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090/v1")
            r = httpx.get(f"{base_url}/models", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def render(self, *, concept: Any, seed: int | None = None) -> CompositorResult:
        return self._do_render(concept=concept, seed=seed)

    def _do_render(self, *, concept: Any, seed: int | None) -> CompositorResult:
        started = time.monotonic()
        if not self.is_available():
            return _make_stub_result(self.backend, self.model_key, seed=seed or 0, duration_ms=0)
        try:
            import httpx
            base_url = os.environ.get("INVOKEAI_BASE_URL", "http://127.0.0.1:9090/v1")
            api_key = os.environ.get("INVOKEAI_API_KEY", "not-required")
            actual_seed = seed or int(time.time() * 1000) % (1 << 31)
            prompt = build_prompt_from_concept(concept)
            resp = httpx.post(
                f"{base_url}/images/generations",
                json={"model": self.model_key, "prompt": prompt, "seed": actual_seed, "size": "1024x1024"},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=120.0,
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
                cost_usd=0.0,  # local
                success=True,
                metadata={"invokeai_url": base_url},
            )
        except Exception as exc:
            logger.warning("FLUX render failed: %s", exc)
            return _make_stub_result(self.backend, self.model_key, seed=seed or 0, duration_ms=0)


# Make FLUXSchnell share the _do_render method
FLUXSchnellCompositor._do_render = FLUX2DevCompositor._do_render


__all__ = ["FLUX2DevCompositor", "FLUXSchnellCompositor"]