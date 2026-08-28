"""Imagen 3 + Imagen 4 compositors (Vertex AI)."""

from __future__ import annotations

import logging
import time
from typing import Any

from . import CompositorResult, build_prompt_from_concept
from .compositor_base import AssetCompositor, _make_stub_result
from .gemini_flash_image_compositor import GeminiFlashImageCompositor

logger = logging.getLogger(__name__)


class Imagen3Compositor(GeminiFlashImageCompositor):
    """Imagen 3 (imagen-3.0-generate-002) via LiteLLM (Vertex AI)."""

    backend: str = "imagen3"
    model_key: str = "imagen-3.0-generate-002"


class Imagen4Compositor(GeminiFlashImageCompositor):
    """Imagen 4 preview (imagen-4.0-generate-preview-06-06) via LiteLLM (Vertex AI)."""

    backend: str = "imagen4"
    model_key: str = "imagen-4.0-generate-preview-06-06"


__all__ = ["Imagen3Compositor", "Imagen4Compositor"]