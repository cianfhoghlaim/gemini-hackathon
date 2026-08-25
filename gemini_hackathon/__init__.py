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

# ─────────────────────────────────────────────────────────────────────
# TIER 1 re-export shim (per the 2026-08-25-lift-model-registry-to-t1-v1
# openspec change). When the parent cianfhoghlaim-model-registry
# TIER 1 package is installed (e.g. via
# `uv pip install -e $DEV/cianfhoghlaim/packages/model-registry`),
# this shim takes precedence over the wholesale copy above.
# When the parent package is NOT installed, the wholesale copy
# remains in effect (the try/except is a soft shim).
# This pattern is mirrored in the other 4 sibling repos
# (tuatha + ciancheiltis + cianchosaint + ciandlithe) in their
# own TIER 1 lift changes (openspec weeks 23-30).
# ─────────────────────────────────────────────────────────────────────
try:
    from cianfhoghlaim.model_registry import (  # noqa: F401
        MODEL_REGISTRY as _CIANFHLOGHLAIM_MODEL_REGISTRY,
        ModelRegistry as _ModelRegistry,
        ModelRegistryEntry as _ModelRegistryEntry,
        ModelFamily as _ModelFamily,
        ModelRole as _ModelRole,
        ModelProfile as _ModelProfile,
        model_for as _model_for,
    )
    # When the parent package is installed, replace the wholesale
    # copy with the canonical TIER 1 implementation.
    MODEL_REGISTRY = _CIANFHLOGHLAIM_MODEL_REGISTRY
    ModelRegistry = _ModelRegistry
    ModelRegistryEntry = _ModelRegistryEntry
    ModelFamily = _ModelFamily
    ModelRole = _ModelRole
    ModelProfile = _ModelProfile
    model_for = _model_for
    _MODEL_REGISTRY_TIER_1_LIFT_ACTIVE = True
except ImportError:
    # Parent package not installed; the wholesale copy above
    # remains in effect.
    _MODEL_REGISTRY_TIER_1_LIFT_ACTIVE = False

# ─────────────────────────────────────────────────────────────────────
# TIER 1 re-export shim (per the 2026-08-25-lift-theming-to-t1-v1
# openspec change). Mirrors the model-registry shim pattern.
# ─────────────────────────────────────────────────────────────────────
try:
    from cianfhoghlaim.theming import (  # noqa: F401
        Palette as _TIER1_Palette,
        load_palette as _tier1_load_palette,
        list_all_palettes as _tier1_list_all_palettes,
        extract_source_palette_from_pdf as _tier1_extract_source_palette_from_pdf,
        JURISDICTIONS as _TIER1_JURISDICTIONS,
        BOARDS as _TIER1_BOARDS,
        SAFEGUARDING_BODIES as _TIER1_SAFEGUARDING_BODIES,
        SAFEGUARDING_SOURCES as _TIER1_SAFEGUARDING_SOURCES,
        CANONICAL_TO_FILE as _TIER1_CANONICAL_TO_FILE,
    )
    Palette = _TIER1_Palette
    load_palette = _tier1_load_palette
    list_all_palettes = _tier1_list_all_palettes
    extract_source_palette_from_pdf = _tier1_extract_source_palette_from_pdf
    JURISDICTIONS = _TIER1_JURISDICTIONS
    BOARDS = _TIER1_BOARDS
    SAFEGUARDING_BODIES = _TIER1_SAFEGUARDING_BODIES
    SAFEGUARDING_SOURCES = _TIER1_SAFEGUARDING_SOURCES
    CANONICAL_TO_FILE = _TIER1_CANONICAL_TO_FILE
    _THEMING_TIER_1_LIFT_ACTIVE = True
except ImportError:
    _THEMING_TIER_1_LIFT_ACTIVE = False

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
    # TIER 1 lift markers (exposed for downstream consumers + tests)
    "_MODEL_REGISTRY_TIER_1_LIFT_ACTIVE",
    "_THEMING_TIER_1_LIFT_ACTIVE",
]
