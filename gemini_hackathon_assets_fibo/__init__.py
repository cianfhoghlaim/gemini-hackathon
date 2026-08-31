"""gemini_hackathon_assets_fibo — the FIBO image generation pipeline.

Lifted from `cianfhoghlaim/docs/sruth/tuath/{asset_generation,fibo_generation}/`
minus the Celtic-mythology content (asset_type, style enums, prompt
generators). The British Isles education context replaces them.

Modules:
  - models: Pydantic data models (EducationAssetType, SubjectStyle,
    GenerationModel, AssetRequest, AssetResponse, BatchAssetRequest, etc.)
  - schemas: dataclass schemas (SyllabusPage, CurriculumConcept,
    GeneratedAsset, FiboConfig)
  - cache: LRU AssetCache (from sruth/tuath AssetCache)
  - assets: Dagster asset templates (generate_fibo_config_for_concept,
    build_asset_request_for_fibo_config, record_generated_asset)

Drives the W10 FIBO image generation pipeline + the W14 certificate
pipeline background rendering.
"""

from gemini_hackathon_assets_fibo.assets import (
    build_asset_request_for_fibo_config,
    generate_fibo_config_for_concept,
    record_generated_asset,
)
from gemini_hackathon_assets_fibo.cache import AssetCache
from gemini_hackathon_assets_fibo.models import (
    AssetRequest,
    AssetResponse,
    BatchAssetRequest,
    BatchAssetResponse,
    EducationAssetType,
    GenerationModel,
    LiteLLMConfig,
    Rarity,
    SubjectStyle,
)
from gemini_hackathon_assets_fibo.schemas import (
    CurriculumConcept,
    FiboConfig,
    GeneratedAsset,
    LearningOutcome,
    SyllabusPage,
    VisualRequirement,
)

__all__ = [
    # cache
    "AssetCache",
    # models
    "AssetRequest",
    "AssetResponse",
    "BatchAssetRequest",
    "BatchAssetResponse",
    # schemas
    "CurriculumConcept",
    "EducationAssetType",
    "FiboConfig",
    "GeneratedAsset",
    "GenerationModel",
    "LearningOutcome",
    "LiteLLMConfig",
    "Rarity",
    "SubjectStyle",
    "SyllabusPage",
    "VisualRequirement",
    # assets
    "build_asset_request_for_fibo_config",
    "generate_fibo_config_for_concept",
    "record_generated_asset",
]
