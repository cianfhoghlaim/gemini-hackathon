"""LiteLLM-backed image-generation adapter.

Routes to the model-key in the LiteLLM registry. The full list at
https://docs.litellm.ai/docs/providers covers Gemini (gemini-image-1.0, etc.),
Vertex image generation, DALL-E, Stable Diffusion, and more.

For the gemini_hackathon submission we use this for Google models:
  - gemini-2.5-flash-image       (Gemini native image gen, multimodal output)
  - imagen-3.0-generate-002      (Vertex Imagen 3)
  - imagen-4.0-generate-preview-06-06  (Vertex Imagen 4 preview — NEW Phase 2)
  - gemini-3.5-flash            (the VLM extractor + primary)
  - gemini-2.5-flash            (VLM fallback)

For local image generation via Hugging Face (the Gemma / DiffusionGemma bonus):
  - google/diffusiongemma-26B-A4B-it    via HF Inference Endpoints / llama-swap
  - google/gemma-4-26B-A4B-it-qat-q4_0-gguf  via llama-swap local
  - google/gemma-4-E4B-it-qat-q4_0-gguf     via llama-swap local (multimodal)

All are Google models and satisfy the hackathon's Google infrastructure
requirement. LiteLLM transparently picks Vertex AI when VERTEXAI_PROJECT
is set, or AI Studio when GEMINI_API_KEY is set.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LiteLLMImageRequest:
    """Arguments for a LiteLLM image generation call."""

    prompt: str
    model: str = "gemini-2.5-flash-image"
    size: str = "1024x1024"
    n: int = 1
    seed: int | None = None


@dataclass(frozen=True)
class LiteLLMImageResult:
    """A normalised image-generation result."""

    b64_images: list[str] = field(default_factory=list)
    model: str = ""
    cost_usd: float = 0.0
    duration_ms: int = 0
    usage: dict = field(default_factory=dict)
    provider: str = "litellm"


def _litellm_available() -> bool:
    try:
        import litellm

        return True
    except ImportError:
        return False


def generate_with_litellm(req: LiteLLMImageRequest) -> LiteLLMImageResult:
    """Call LiteLLM's image_generation with our request and normalise the result."""
    if not _litellm_available():
        raise RuntimeError("litellm not installed; install with `uv pip install litellm`.")

    start = time.monotonic()
    try:
        from litellm import image_generation

        response = image_generation(
            prompt=req.prompt,
            model=req.model,
            size=req.size,
            n=req.n,
            seed=req.seed,
        )
    except Exception as e:
        logger.warning(f"litellm.image_generation failed: {type(e).__name__}: {e}")
        raise

    duration_ms = int((time.monotonic() - start) * 1000)

    b64_list: list[str] = []
    for img in getattr(response, "data", []):
        b64 = getattr(img, "b64_json", None)
        if not b64:
            url = getattr(img, "url", None)
            if url:
                b64_list.append(url)
            continue
        b64_list.append(b64)
    cost = 0.0
    hidden = getattr(response, "_hidden_params", None)
    if isinstance(hidden, dict):
        cost = float(hidden.get("response_cost", 0.0) or 0.0)
    usage = getattr(response, "usage", {}) or {}
    return LiteLLMImageResult(
        b64_images=b64_list,
        model=req.model,
        cost_usd=cost,
        duration_ms=duration_ms,
        usage=dict(usage) if usage else {},
        provider="litellm",
    )


__all__ = [
    "LiteLLMImageRequest",
    "LiteLLMImageResult",
    "generate_with_litellm",
]


# ---------------------------------------------------------------------------
# HF / local-fallback image generation registry (Phase 2)
# ---------------------------------------------------------------------------
# The Google HF catalog of image-gen models for the bonus +0.4 (Gemma + DiffusionGemma).
# These route through llama-swap or HF Inference Endpoints — not through LiteLLM.

HF_IMAGEGEN_REGISTRY: dict[str, dict[str, str]] = {
    # Google's first image-gen Gemma (Jun 2026, Apache-2.0, 25.8B MoE)
    "google/diffusiongemma-26B-A4B-it": {
        "license": "apache-2.0",
        "params": "25.8B (MoE 4B active)",
        "endpoint": "huggingface",
        "use_for": "Image gen — primary Google HF model",
        "downloads": "4.9M",
    },
    # Google's flagship multimodal Gemma 4 (52.8M DL #1 Gemma 4)
    "google/gemma-4-26B-A4B-it-qat-q4_0-gguf": {
        "license": "apache-2.0",
        "params": "25.8B Q4 (~16 GB GGUF)",
        "endpoint": "llama-swap",
        "use_for": "Multimodal image gen + chat (local fallback)",
        "downloads": "16M",
    },
    # Gemma 4 E4B — sweet-spot VLM (28.2M DL #1 Gemma 4 multimodal)
    "google/gemma-4-E4B-it-qat-q4_0-gguf": {
        "license": "apache-2.0",
        "params": "8B active Q4 (~5 GB GGUF)",
        "endpoint": "llama-swap",
        "use_for": "Multimodal VLM (OCR + extraction + image gen)",
        "downloads": "28.2M",
    },
}


def list_hf_imagegen_models() -> list[str]:
    """List the HF-hosted Google image-gen models available for the hackathon."""
    return list(HF_IMAGEGEN_REGISTRY.keys())
