"""gemini_hackathon.assets — the generative asset pipeline.

Sits downstream of the OCR pipeline (Phase 2). Inputs:
    - a BAML ``SourcePalette`` (from extract_palette.baml)
    - a BAML ``SyllabusDocument`` (from extract_curriculum.baml, per jurisdiction)
    - a per-source BAML ``AssetPrompt`` (from extract_assets.baml, Phase 8 stub)

Outputs:
    - an ``AssetControlRecord`` — JSON-native control (FIBO-compatible)
    - an ``asset_provenance`` row — the chain back to the source document

The 4 image_gen backends (ComfyUI / InvokeAI / Unsloth Studio) are
routed via :class:`ImageGenRouter`. In the hackathon profile the default
is ``diffusiongemma-26b-a4b`` (Unsloth Studio); for provenance-critical
artefacts (certificates), ``fibo`` (ComfyUI) is preferred.
"""
