"""gemini_hackathon.certificate.backends — the 7 compositor backends for the asset comparison.

Per the user's "compare FIBO + DiffusionGemma + FLUX + Imagen + Gemini
Flash Image" ask, we ship 7 backends:

  1. FIBO                  (JSON-native, ComfyUI, provenance-critical)
  2. DiffusionGemma 26B-A4B (Unsloth Studio, HF model)
  3. FLUX.1-schnell        (InvokeAI)
  4. FLUX.2-dev            (InvokeAI)
  5. Gemini 2.5 Flash Image (LiteLLM, Vertex)
  6. Imagen 3              (LiteLLM, Vertex)
  7. Imagen 4              (LiteLLM, Vertex — NEW Phase 2)

Each compositor returns (image_b64, duration_ms, model_key, cost_usd,
seed, success) given a CurriculumConcept (per-topic asset schema).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CompositorResult:
    """The result of one compositor call."""

    backend: str
    model_key: str
    image_b64: str | bytes
    seed: int
    duration_ms: int
    cost_usd: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def build_prompt_from_concept(concept: Any) -> str:
    """Build a prompt from a CurriculumConcept.

    Uses the concept's subject speciality (visual_cue + diagram_type)
    + the LO text + the topic name.
    """
    subject = getattr(concept, "subject", "subject")
    topic = getattr(concept, "topic", "topic")
    lo_text = getattr(concept, "lo_text", "")
    visual_cue = getattr(concept, "visual_cue", "")
    diagram_type = getattr(concept, "diagram_type", "diagram")
    palette_primary = getattr(concept, "palette_primary", "#1a1a1a")
    palette_accent = getattr(concept, "palette_accent", "#CC4500")

    return (
        f"Educational asset for {subject} on '{topic}'.\n"
        f"Learning outcome: {lo_text}\n"
        f"Visual style: {visual_cue}\n"
        f"Diagram type: {diagram_type}\n"
        f"Primary colour: {palette_primary}, Accent: {palette_accent}\n"
        f"Style: clean, professional, accessible, WCAG 2.2 AA contrast."
    )


__all__ = [
    "CompositorResult",
    "build_prompt_from_concept",
]