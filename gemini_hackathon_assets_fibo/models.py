"""gemini_hackathon_assets_fibo.models — asset generation data models for FIBO.

Lifted from `cianfhoghlaim/docs/sruth/tuath/asset_generation/models.py` and
adapted for the British Isles education system:

  - CelticStyle (La Tène / Ogham / Knotwork / Zoomorphic / Spiral /
    Illuminated) → SubjectStyle (14 NCCA subjects + 5 stage styles).
  - AssetType (character_portrait / item_icon / clan_heraldry /
    territory_tile / spell_effect / creature) →
    EducationAssetType (syllabus_diagram / experiment_apparatus /
    formative_exit_card / certificate / topic_summary / molecule_svg /
    equation_render).
  - ClanId (Tuatha Dé Danann / Fir Bolg / Fomorians / Milesians) →
    removed (out of scope for education).
  - GenerationModel kept (FLUX / SDXL / Qwen-VL).
  - AssetRequest / AssetResponse / BatchAssetRequest / BatchAssetResponse
    kept verbatim with the per-subject style extension.

Drives the W10 FIBO image generation + the W14 certificate pipeline
background rendering.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class EducationAssetType(StrEnum):
    """Types of education assets the FIBO pipeline generates.

    Generalises the Celtic AssetType (character_portrait, item_icon,
    clan_heraldry, territory_tile, spell_effect, creature) to the
    British Isles education system.
    """

    SYLLABUS_DIAGRAM = "syllabus_diagram"  # NCCA syllabus page with diagram
    EXPERIMENT_APPARATUS = "experiment_apparatus"  # chemistry apparatus diagram
    FORMATIVE_EXIT_CARD = "formative_exit_card"  # formative assessment cover
    CERTIFICATE = "certificate"  # LC/JC certificate background (W14)
    TOPIC_SUMMARY = "topic_summary"  # NCCA topic summary poster
    MOLECULE_SVG = "molecule_svg"  # chemistry molecule diagram
    EQUATION_RENDER = "equation_render"  # math equation rendered image
    MAP_DIAGRAM = "map_digram"  # British Isles map diagram


class SubjectStyle(StrEnum):
    """Subject / stage styles for generation.

    Replaces CelticStyle (La Tène / Ogham / Knotwork / Zoomorphic /
    Spiral / Illuminated). The 14 NCCA subjects × 5 stages produce a
    70-entry matrix; this enum exposes the canonical 14 subjects + the
    5 stage defaults.
    """

    # 8 NCCA subjects
    SUBJECT_MATHEMATICS = "subject_mathematics"
    SUBJECT_APPLIED_MATHEMATICS = "subject_applied_mathematics"
    SUBJECT_CHEMISTRY = "subject_chemistry"
    SUBJECT_GEOGRAPHY = "subject_geography"
    SUBJECT_HISTORY = "subject_history"
    SUBJECT_ENGLISH = "subject_english"
    SUBJECT_GAEILGE = "subject_gaeilge"
    SUBJECT_COMPUTER_SCIENCE = "subject_computer_science"
    # 6 NCCA-adjacent subjects
    SUBJECT_ACCOUNTING = "subject_accounting"
    SUBJECT_BIOLOGY = "subject_biology"
    SUBJECT_BUSINESS = "subject_business"
    SUBJECT_FRENCH = "subject_french"
    SUBJECT_IRISH_T2 = "subject_irish_t2"
    SUBJECT_PHYSICS = "subject_physics"
    # 5 stage defaults
    STAGE_AISTEAR = "stage_aistear"
    STAGE_BUNSCOIL = "stage_bunscoil"
    STAGE_MEANSCOIL = "stage_meanscoil"
    STAGE_SCOIL_SINSEARACH = "stage_scoil_sinsearach"
    STAGE_OLLSCOIL = "stage_ollscoil"


class GenerationModel(StrEnum):
    """Available generation models."""

    FLUX_DEV = "black-forest-labs/FLUX.1-dev"
    FLUX_SCHNELL = "black-forest-labs/FLUX.1-schnell"
    SDXL_TURBO = "stabilityai/sdxl-turbo"
    QWEN_VL = "Qwen/Qwen2-VL-7B-Instruct"
    UNSLOTH_STUDIO_FLUX = (
        "unsloth_studio/flux"  # the gemini_hackathon Tier 2 (Gemma 4 26B-A4B → Flux)
    )


class Rarity(StrEnum):
    """Visual asset rarity levels.

    Kept from the Celtic AssetType (where it meant "item rarity") —
    here it maps to "diagram detail level" (Common = outline, Rare =
    fully rendered).
    """

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class AssetRequest(BaseModel):
    """Request for asset generation."""

    asset_type: EducationAssetType
    style: SubjectStyle = SubjectStyle.STAGE_SCOIL_SINSEARACH
    model: GenerationModel = GenerationModel.FLUX_SCHNELL

    # Dimensions
    width: int = Field(default=512, ge=256, le=2048)
    height: int = Field(default=512, ge=256, le=2048)

    # Generation parameters
    prompt_override: str | None = None
    negative_prompt: str | None = None
    seed: int | None = None
    steps: int = Field(default=20, ge=1, le=100)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)

    # Asset-specific parameters
    subject: str | None = None  # for subject-specific diagrams
    topic_code: str | None = None  # learning outcome code (e.g. MA-LC-CH-1.2)
    detail_level: Rarity = Rarity.COMMON

    # Caching (the existing AssetCache from service.py)
    cache_key: str | None = None
    use_cache: bool = True

    class Config:
        use_enum_values = True


class AssetResponse(BaseModel):
    """Response from asset generation."""

    success: bool
    asset_id: str

    # Image data
    image_url: str | None = None
    image_base64: str | None = None

    # Metadata
    prompt_used: str
    model_used: str
    generation_time_ms: int

    # Asset details
    asset_type: EducationAssetType
    style: SubjectStyle
    width: int
    height: int

    # Storage (HF Hub — see gemini_hackathon_gradio._common.hf_hub_push)
    hf_dataset_repo: str | None = None  # cianfhoghlaim/gemini-hackathon-assets-<user>
    hf_dataset_path: str | None = None  # path within the repo

    # Error handling
    error: str | None = None

    class Config:
        use_enum_values = True


class BatchAssetRequest(BaseModel):
    """Batch request for multiple assets."""

    requests: list[AssetRequest]
    priority: int = Field(default=0, ge=0, le=10)
    callback_url: str | None = None

    class Config:
        use_enum_values = True


class BatchAssetResponse(BaseModel):
    """Response from batch asset generation."""

    batch_id: str
    total_requested: int
    completed: int
    failed: int
    results: list[AssetResponse]

    class Config:
        use_enum_values = True


class LiteLLMConfig(BaseModel):
    """LiteLLM gateway configuration (per the W3 _common/baml_client.py).

    Lifted from sruth/tuath/asset_generation/service.py:LiteLLMConfig.
    """

    api_base: str = "http://localhost:4000"
    api_key: str | None = None
    timeout: int = 120
    max_retries: int = 3


__all__ = [
    "AssetRequest",
    "AssetResponse",
    "BatchAssetRequest",
    "BatchAssetResponse",
    "EducationAssetType",
    "GenerationModel",
    "LiteLLMConfig",
    "Rarity",
    "SubjectStyle",
]
