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
    # Phase 3 sources (jurisdiction/board/subject registry)
    "JurisdictionMeta",
    "BoardMeta",
    "Subject",
    "JurisdictionCode",
    "BoardCode",
    "sources_JURISDICTIONS",
    "sources_BOARDS",
    "sources_SUBJECTS",
    "sources_list_jurisdictions",
    "sources_list_boards",
    "sources_get_jurisdiction_meta",
    "sources_get_board_meta",
    "sources_subjects_for",
    "sources_public_roster",
]


# ---------------------------------------------------------------------------
# Phase 3 — jurisdiction/board/subject canonical registry (sources.py).
# Aliased with `sources_` prefix so they don't clash with the parent
# TIER 1 lift (which exports `JURISDICTIONS` / `BOARDS` for the theming
# module). When the parent cianfhoghlaim package is installed, those
# win; when it's not, the wholesale theming.py copy wins. The Phase 3
# sources are always available via the `sources_*` aliases regardless.
# ---------------------------------------------------------------------------

from .sources import (
    JurisdictionMeta as _Sources_JurisdictionMeta,
    BoardMeta as _Sources_BoardMeta,
    Subject as _Sources_Subject,
    JurisdictionCode as _Sources_JurisdictionCode,
    BoardCode as _Sources_BoardCode,
    JURISDICTIONS as sources_JURISDICTIONS,
    BOARDS as sources_BOARDS,
    SUBJECTS as sources_SUBJECTS,
    list_jurisdictions as sources_list_jurisdictions,
    list_boards as sources_list_boards,
    get_jurisdiction_meta as sources_get_jurisdiction_meta,
    get_board_meta as sources_get_board_meta,
    subjects_for as sources_subjects_for,
    public_roster as sources_public_roster,
)

# Type aliases (re-export the Phase 3 types under their canonical names).
JurisdictionMeta = _Sources_JurisdictionMeta
BoardMeta = _Sources_BoardMeta
Subject = _Sources_Subject
JurisdictionCode = _Sources_JurisdictionCode
BoardCode = _Sources_BoardCode


__all__ += [
    # Phase 3 sources (jurisdiction/board/subject registry)
    "JurisdictionMeta",
    "BoardMeta",
    "Subject",
    "JurisdictionCode",
    "BoardCode",
    "sources_JURISDICTIONS",
    "sources_BOARDS",
    "sources_SUBJECTS",
    "sources_list_jurisdictions",
    "sources_list_boards",
    "sources_get_jurisdiction_meta",
    "sources_get_board_meta",
    "sources_subjects_for",
    "sources_public_roster",
]


# ---------------------------------------------------------------------------
# Phase 0 — Google Cloud Secret Manager injection (2026-08-30)
# Replaces the legacy Infisical + Locket contract for the gemini_hackathon
# dev demo. Behaviour is opt-in via ADK_LOAD_SECRETS=1 — the default is to
# leave the environment untouched so that existing tools (uvicorn, marimo,
# BAML CLI) continue to work in dev. CI / Cloud Run / GCE should always set
# ADK_LOAD_SECRETS=1 so that ADC + GSM populate the env at process start.
# ---------------------------------------------------------------------------
try:
    import os as _os
    if _os.environ.get("ADK_LOAD_SECRETS", "").strip().lower() in {"1", "true", "yes"}:
        from .secrets_loader import inject_into_environ as _inject_secrets  # noqa: E402

        _injected = _inject_secrets()
        _SECRETS_LOADED = True
        _SECRETS_COUNT = len(_injected)
        _SECRETS_BACKEND = "gsm" if _os.environ.get("ADK_LOCAL_SECRETS", "").strip().lower() not in {"1", "true", "yes"} else "dotenv"
    else:
        _SECRETS_LOADED = False
        _SECRETS_COUNT = 0
        _SECRETS_BACKEND = None
except Exception as _exc:
    _SECRETS_LOADED = False
    _SECRETS_COUNT = 0
    _SECRETS_BACKEND = None
    _SECRETS_LOAD_ERROR = str(_exc)
else:
    _SECRETS_LOAD_ERROR = None


__all__ += [
    "_SECRETS_LOADED",
    "_SECRETS_COUNT",
    "_SECRETS_BACKEND",
    "_SECRETS_LOAD_ERROR",
]
