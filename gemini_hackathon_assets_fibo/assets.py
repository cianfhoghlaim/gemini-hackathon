"""gemini_hackathon_assets_fibo.assets — Dagster asset templates for FIBO image generation.

Lifted from `cianfhoghlaim/docs/sruth/tuath/fibo_generation/assets.py`
(commit c853e360, "Phase 1 (atomic)"). Rewritten for the British Isles
education theme — the SAMPLE_CONCEPTS dict is replaced with a stub
that loads from the gemini_hackathon data lake (W5), not from a
hardcoded dictionary.

Assets:
  - fibo_configs: Generate FIBO JSON from curriculum concepts (BAML-driven)
  - generated_images: Generate images from FIBO JSON configs (Flux + Unsloth + LiteLLM)
  - fibo_configs_from_syllabus_diagrams: Generate FIBO JSON from REAL
    extracted SyllabusDiagram records (see its own docstring below)
  - generated_certificate: LC/JC certificate background (W14 — the showcase)

The real lifecycle (OCR → BAML extract → CocoIndex embed → FIBO generate
→ validate → push to HF Hub) is wired in W5 (data pipeline) + W10
(FIBO image gen) + W14 (certificate pipeline).

This module provides the type-safe Pydantic models + the asset function
signatures (Dagster asset templates). The actual asset definitions live
in `gemini_hackathon/orchestration/` (W5 lift).
"""

from __future__ import annotations

import json
import uuid

from .models import (
    AssetRequest,
    AssetResponse,
    EducationAssetType,
    GenerationModel,
    SubjectStyle,
)
from .schemas import (
    CurriculumConcept,
    FiboConfig,
    GeneratedAsset,
)


def generate_fibo_config_for_concept(
    concept: CurriculumConcept,
    *,
    style: SubjectStyle = SubjectStyle.STAGE_SCOIL_SINSEARACH,
    model: GenerationModel = GenerationModel.FLUX_SCHNELL,
) -> FiboConfig:
    """Generate the FIBO JSON config for a single curriculum concept.

    Constructs the FIBO prompt that the image-gen backend consumes
    (Flux / SDXL / Qwen-VL). The config carries the visual requirements
    + the per-subject style + the educational metadata.
    """
    # Pick the most-specific visual requirement (highest complexity)
    vis_req = concept.visual_requirements[0] if concept.visual_requirements else None
    diagram_type = vis_req.diagram_type if vis_req else "diagram"
    complexity = vis_req.complexity if vis_req else "moderate"

    # Build the educational detail
    subtitle = f"{concept.subject.title()} - {concept.topic_name}"
    if concept.strand:
        subtitle += f" - {concept.strand}"

    # Build the full descriptive prompt
    full_prompt = f"{concept.title}. {concept.description} "
    if concept.keywords:
        full_prompt += f"Key concepts: {', '.join(concept.keywords[:5])}. "
    if concept.learning_outcomes:
        first_lo = concept.learning_outcomes[0]
        full_prompt += f"Demonstrates learning outcome {first_lo.code}: {first_lo.description}. "

    return FiboConfig(
        title=concept.title or concept.topic_name,
        short_description=subtitle,
        detailed_description=full_prompt,
        style=style.value.replace("_", " "),
        medium="digital art" if complexity == "simple" else "digital illustration",
        color_palette=[concept.subject.lower(), "educational"],
        subject_area=concept.subject,
        diagram_type=diagram_type,
        complexity_level=complexity,
    )


def build_asset_request_for_fibo_config(
    config: FiboConfig,
    *,
    asset_type: EducationAssetType = EducationAssetType.SYLLABUS_DIAGRAM,
    subject: str = "",
    topic_code: str = "",
    width: int = 768,
    height: int = 768,
) -> AssetRequest:
    """Build an AssetRequest from a FIBO config."""
    return AssetRequest(
        asset_type=asset_type,
        style=SubjectStyle.STAGE_SCOIL_SINSEARACH,  # default to LC palette
        model=GenerationModel.FLUX_SCHNELL,
        width=width,
        height=height,
        prompt_override=config.to_prompt(),
        subject=subject,
        topic_code=topic_code,
    )


def record_generated_asset(
    concept: CurriculumConcept,
    config: FiboConfig,
    response: AssetResponse,
    image_path: str,
    *,
    ncca_policy_citations: list[str] | None = None,
) -> GeneratedAsset:
    """Record the provenance of a generated asset.

    Used by the Dagster asset to materialize the GeneratedAsset record
    with all the provenance fields populated.
    """
    return GeneratedAsset(
        id=str(uuid.uuid4()),
        concept_id=concept.id,
        fibo_prompt_json=json.dumps(
            {
                "title": config.title,
                "short_description": config.short_description,
                "detailed_description": config.detailed_description,
                "style": config.style,
                "medium": config.medium,
                "color_palette": config.color_palette,
                "subject_area": config.subject_area,
                "diagram_type": config.diagram_type,
                "complexity_level": config.complexity_level,
            }
        ),
        style_medium=config.medium,
        image_path=image_path,
        image_embedding=[],  # populated post-generation by the CLIP embed step (W10)
        status="draft",
        validation_issues=[],
        ncca_policy_citations=ncca_policy_citations or [],
    )


__all__ = [
    "build_asset_request_for_fibo_config",
    "generate_fibo_config_for_concept",
    "record_generated_asset",
]
