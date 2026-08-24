"""gemini_hackathon — the public-demo Python package.

Public API:
    theming: palette loading + per-source palette extraction (BAML stub)
    models:  registry of every model the project routes through
    call_llm: dual-profile LiteLLM router with model-exclusion guard
"""

from .theming import (
    Palette,
    load_palette,
    list_all_palettes,
    extract_source_palette_from_pdf,
    JURISDICTION_SOURCES,
    SAFEGUARDING_SOURCES,
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
    "JURISDICTION_SOURCES",
    "SAFEGUARDING_SOURCES",
    # models
    "MODEL_REGISTRY",
    "ModelRegistry",
    "ModelRegistryEntry",
    "ModelFamily",
    "ModelRole",
    "ModelProfile",
    "model_for",
]
