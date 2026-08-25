"""gemini_hackathon — the public-demo Python package.

Public API:
    theming: palette loading + per-source palette extraction (BAML stub)
    models:  registry of every model the project routes through
    call_llm: dual-profile LiteLLM router with model-exclusion guard
    ocr:     capability-dispatched OCR/VLM pipeline (Phase 2)
    assets:  generative asset pipeline (Phase 8)
    compare: Gemini-vs-Gemma comparison harness (Phase 4)
    observability: structlog + Langfuse + MLflow port (Phase 10)
    backend: stdlib HTTP server exposing /api/chat/completions + /api/themes
"""

from .theming import (
    Palette,
    load_palette,
    list_all_palettes,
    extract_source_palette_from_pdf,
    JURISDICTIONS,
    BOARDS,
    SAFEGUARDING_BODIES,
    SAFEGUARDING_SOURCES,
    CANONICAL_TO_FILE,
)
from .models import (
    MODEL_REGISTRY,
    ModelRegistry,
    ModelRegistryEntry,
    ModelFamily,
    ModelRole,
    ModelProfile,
    model_for,
)

__all__ = [
    # theming
    "Palette",
    "load_palette",
    "list_all_palettes",
    "extract_source_palette_from_pdf",
    "JURISDICTIONS",
    "BOARDS",
    "SAFEGUARDING_BODIES",
    "SAFEGUARDING_SOURCES",
    "CANONICAL_TO_FILE",
    # models
    "MODEL_REGISTRY",
    "ModelRegistry",
    "ModelRegistryEntry",
    "ModelFamily",
    "ModelRole",
    "ModelProfile",
    "model_for",
]
