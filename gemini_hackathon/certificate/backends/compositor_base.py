"""gemini_hackathon.certificate.backends.compositor_base — the base compositor protocol."""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from . import CompositorResult, build_prompt_from_concept

logger = logging.getLogger(__name__)


class AssetCompositor(Protocol):
    """The protocol every compositor implements."""

    backend: str
    model_key: str

    def is_available(self) -> bool: ...

    def render(
        self,
        *,
        concept: Any, # CurriculumConcept
        seed: int | None = None,
    ) -> CompositorResult: ...


def _make_stub_result(backend: str, model_key: str, *, seed: int, duration_ms: int) -> CompositorResult:
    """Build a stub result when a compositor is unavailable.

    Returns a 1×1 PNG (the same minimal PNG used elsewhere in the repo)
    so the rest of the pipeline can run end-to-end.
    """
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c6300010000000500015c6df8b50000000049454e44ae426082"
    )
    import base64
    return CompositorResult(
        backend=backend,
        model_key=model_key,
        image_b64=base64.b64encode(png).decode("ascii"),
        seed=seed,
        duration_ms=duration_ms,
        cost_usd=0.0,
        success=True,
        metadata={"stub": True, "reason": "backend_unreachable"},
    )


__all__ = [
    "AssetCompositor",
    "_make_stub_result",
]