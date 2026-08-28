"""FIBO compositor (the provenance-critical backend)."""

from __future__ import annotations

import logging
import time
from typing import Any

from . import CompositorResult, build_prompt_from_concept
from .compositor_base import AssetCompositor, _make_stub_result

logger = logging.getLogger(__name__)


class FIBOCompositor:
    """The FIBO + ComfyUI compositor (provenance-critical for cert backgrounds)."""

    backend: str = "fibo"
    model_key: str = "fibo_comfyui"

    def is_available(self) -> bool:
        try:
            import httpx
            import os
            base_url = os.environ.get("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
            r = httpx.get(f"{base_url}/system_stats", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def render(self, *, concept: Any, seed: int | None = None) -> CompositorResult:
        started = time.monotonic()
        if not self.is_available():
            return _make_stub_result(self.backend, self.model_key, seed=seed or 0, duration_ms=0)
        try:
            import os
            import httpx
            base_url = os.environ.get("COMFYUI_BASE_URL", "http://127.0.0.1:8188").rstrip("/")
            api_key = os.environ.get("COMFYUI_API_KEY", "not-required")
            actual_seed = seed or int(time.time() * 1000) % (1 << 31)
            prompt = build_prompt_from_concept(concept)
            # FIBO is JSON-native: POST the control record as a workflow payload
            payload = {
                "prompt": prompt,
                "seed": actual_seed,
                "subject": getattr(concept, "subject", ""),
                "topic": getattr(concept, "topic", ""),
                "lo_code": getattr(concept, "lo_code", ""),
                "palette_primary": getattr(concept, "palette_primary", "#1a1a1a"),
                "palette_accent": getattr(concept, "palette_accent", "#CC4500"),
            }
            resp = httpx.post(
                f"{base_url}/prompt",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=120.0,
            )
            resp.raise_for_status()
            out = resp.json()
            image_b64 = out.get("images", [""])[0]
            duration_ms = int((time.monotonic() - started) * 1000)
            return CompositorResult(
                backend=self.backend,
                model_key=self.model_key,
                image_b64=image_b64,
                seed=actual_seed,
                duration_ms=duration_ms,
                cost_usd=0.0,  # FIBO is local
                success=True,
                metadata={"comfyui_url": base_url},
            )
        except Exception as exc:
            logger.warning("FIBO render failed: %s", exc)
            return _make_stub_result(self.backend, self.model_key, seed=seed or 0, duration_ms=0)


__all__ = ["FIBOCompositor"]