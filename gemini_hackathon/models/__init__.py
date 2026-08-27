"""gemini_hackathon model registry — ported from meaisinfhoghlaim.

This is the single source of truth for model identity in the hackathon
project. Hardcoding model strings in three places is a known footgun;
this registry centralises them and the ``call_llm()`` router resolves
every model via ``model_for(family, role)``.

Model families exposed:
- ``text_llm``        — Gemini 3.5 (vertex + aistudio), Gemma 4 via Unsloth Studio,
                        minimax-m3, plus the wider Unsloth Studio text set.
- ``ocr_vision``      — qwen3-vl-8b + gemma-4-{E2B,E4B,12B,26B-A4B} via llama-swap.
- ``embedder``        — BAAI/bge-m3 (1024-dim multilingual).
- ``rerank``          — placeholder; consumer-side BGE-reranker.
- ``image_gen``       — DiffusionGemma 26B-A4B (Unsloth) + Qwen-Image 2512 (Unsloth)
                        + FLUX.2-dev / Z-Image-Turbo / Qwen-Image (InvokeAI)
                        + FIBO (ComfyUI) — full registry mirrors meaisinfhoghlaim.
- ``voice``           — Orpheus + Sesame-CSM (TTS), via Unsloth Studio.
- ``translation``     — minicpm-o-4_5 (multimodal) — registry entry only.

Each entry has:
- ``key``             — canonical identifier (e.g. ``"gemini-3.5-flash"``).
- ``family``          — ``ModelFamily`` literal.
- ``role``            — within-family role string (``default`` | ``primary`` | …).
- ``display_name``    — human-readable name for UI surfaces.
- ``unsloth_id``      — Unsloth GGUF id, if applicable.
- ``upstream_id``     — canonical HuggingFace id (or hosted-API name).
- ``backend``         — runtime backend (vertex | aistudio | unsloth_studio |
                        llama_swap | invokeai | comfyui | local | google).
- ``available``       — True when the model is currently routable.
- ``litellm_alias``   — LiteLLM route alias (e.g. ``"vertex_ai/gemini-3.5-flash"``).
- ``profile``         — hackathon | dev | both — which MODEL_PROFILE includes it.
- ``notes``           — free-form documentation.

Reference: cianfhoghlaim/meaisinfhoghlaim/models/model_registry.py (v6).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


ModelFamily = Literal[
    "text_llm",
    "ocr_vision",
    "embedder",
    "rerank",
    "image_gen",
    "voice",
    "translation",
]
"""The 7 supported model families (matches meaisinfhoghlaim)."""


ModelRole = str
"""Free-form within-family role (default, primary, diagram, tts, …)."""


ModelProfile = Literal["hackathon", "dev", "both"]
"""Which MODEL_PROFILE exposes this entry.

- ``hackathon`` — exposed when ``MODEL_PROFILE=hackathon`` (the default).
- ``dev``       — exposed when ``MODEL_PROFILE=dev``.
- ``both``      — exposed under either profile.
"""

Backend = Literal[
    "vertex",
    "aistudio",
    "unsloth_studio",
    "llama_swap",
    "invokeai",
    "comfyui",
    "local",
    "google",
    "minimax",
]


@dataclass(frozen=True)
class ModelRegistryEntry:
    """A single registry entry — see module docstring for the schema."""

    key: str
    family: ModelFamily
    role: str
    display_name: str
    unsloth_id: str | None
    upstream_id: str
    backend: Backend
    available: bool
    litellm_alias: str | None = None
    profile: ModelProfile = "hackathon"
    env_var: str | None = None
    notes: str = ""
    languages: tuple[str, ...] | None = None
    capabilities: tuple[str, ...] = field(default_factory=tuple)


# ─── Family contributors ──────────────────────────────────────────────────
# Each helper returns ``{key: entry}`` for that family. Insertion order is
# preserved (Python 3.7+); ``resolve()`` does a first-match linear scan so
# canonical / default entries MUST come first within a family.


def _text_llm_entries() -> dict[str, ModelRegistryEntry]:
    """The text LLM family — 3-tier router + dev-only extras."""

    entries: dict[str, ModelRegistryEntry] = {
        # ── Tier 1 (hackathon profile): Gemini 3.5 Flash ──
        # Both Vertex AI (preferred; GCS-credentialed) and AI Studio (API key)
        # are first-class; selection is driven by GEMINI_BACKEND env var.
        "gemini-3.5-flash": ModelRegistryEntry(
            key="gemini-3.5-flash",
            family="text_llm",
            role="default",
            display_name="Gemini 3.5 Flash (hackathon primary)",
            unsloth_id=None,
            upstream_id="gemini-3.5-flash",
            backend="vertex",
            available=True,
            litellm_alias="vertex_ai/gemini-3.5-flash",
            profile="hackathon",
            env_var="GEMINI_BACKEND",
            notes=(
                "Tier 1 in the hackathon model profile. Switches between "
                "Vertex AI (GEMINI_BACKEND=vertex, default) and AI Studio "
                "(GEMINI_BACKEND=aistudio) at call time. Promotes Google "
                "Cloud usage for the All Things Agentic submission."
            ),
            capabilities=("chat", "function_calling", "json_mode", "long_context"),
        ),
        "gemini-3.5-flash-aistudio": ModelRegistryEntry(
            key="gemini-3.5-flash-aistudio",
            family="text_llm",
            role="aistudio",
            display_name="Gemini 3.5 Flash (AI Studio)",
            unsloth_id=None,
            upstream_id="gemini-3.5-flash",
            backend="aistudio",
            available=True,
            litellm_alias="gemini/gemini-3.5-flash",
            profile="hackathon",
            env_var="GEMINI_API_KEY",
            notes="Same model served from AI Studio when GEMINI_BACKEND=aistudio.",
            capabilities=("chat", "function_calling", "json_mode"),
        ),
        # ── Tier 2 (hackathon profile): Gemma 4 26B-A4B via Unsloth Studio ──
        "gemma-4-26b-a4b": ModelRegistryEntry(
            key="gemma-4-26b-a4b",
            family="text_llm",
            role="fallback",
            display_name="Gemma 4 26B-A4B (Unsloth Studio, hackathon fallback)",
            unsloth_id="unsloth/gemma-4-26B-A4B-it-GGUF",
            upstream_id="google/gemma-4-26B-A4B-it",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/gemma-4-26b-a4b",
            profile="hackathon",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Tier 2 in the hackathon model profile. Served from the "
                "Unsloth Studio :8888 endpoint; identity matches the "
                "llama-swap gemma-4-26B-A4B entry so the two deployments "
                "are interchangeable."
            ),
            capabilities=("chat", "function_calling"),
        ),
        # ── Tier 3 (dev profile): minimax-m3 via MiniMax.io ──
        "minimax-m3": ModelRegistryEntry(
            key="minimax-m3",
            family="text_llm",
            role="dev_primary",
            display_name="minimax M3 (dev profile primary)",
            unsloth_id=None,
            upstream_id="minimax-m3",
            backend="minimax",
            available=True,
            litellm_alias="minimax-m3",
            profile="dev",
            env_var="MINIMAX_BASE_URL",
            notes=(
                "Dev-profile Tier 1. NOT exposed in hackathon profile docs "
                "or the submission UI. Lives here so the hackathon project "
                "can be compared against the upstream 12-agent fleet."
            ),
            capabilities=("chat", "function_calling"),
        ),
        # ── Dev profile extras: wider Unsloth text set ──
        "qwen3.8-27b": ModelRegistryEntry(
            key="qwen3.8-27b",
            family="text_llm",
            role="dev_strong",
            display_name="Qwen 3.8 27B (Unsloth Studio)",
            unsloth_id="unsloth/qwen3.8-27b-it-GGUF",
            upstream_id="Qwen/Qwen3-8-27B",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/qwen3.8-27b",
            profile="dev",
            notes="Dev-only Qwen flagship for harness comparisons.",
        ),
        "deepseek-v4-flash": ModelRegistryEntry(
            key="deepseek-v4-flash",
            family="text_llm",
            role="dev_fast",
            display_name="DeepSeek V4 Flash (Unsloth Studio)",
            unsloth_id="unsloth/deepseek-v4-flash-GGUF",
            upstream_id="deepseek-ai/DeepSeek-V4-Flash",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/deepseek-v4-flash",
            profile="dev",
            notes="Dev-only fast tier for harness comparisons.",
        ),
        "kimi-k2.6": ModelRegistryEntry(
            key="kimi-k2.6",
            family="text_llm",
            role="dev_alt",
            display_name="Kimi K2.6 (Unsloth Studio)",
            unsloth_id="unsloth/kimi-k2.6-GGUF",
            upstream_id="moonshotai/Kimi-K2.6",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/kimi-k2.6",
            profile="dev",
            notes="Dev-only long-context comparison.",
        ),
    }
    return entries


def _ocr_vision_entries() -> dict[str, ModelRegistryEntry]:
    """OCR/VLM family — ported from meaisinfhoghlaim/model_registry.py:v6."""
    return {
        "qwen3-vl-8b": ModelRegistryEntry(
            key="qwen3-vl-8b",
            family="ocr_vision",
            role="default",
            display_name="Qwen 3-VL 8B (llama-swap, OCR workhorse)",
            unsloth_id=None,
            upstream_id="Qwen/Qwen3-VL-8B-Instruct",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/qwen3-vl-8b",
            profile="hackathon",
            notes="Stage-1 OCR workhorse; 81s CPU warmup on llama-swap.",
            capabilities=("ocr", "figure_caption", "multilingual"),
        ),
        "gemma-4-26b-a4b-vision": ModelRegistryEntry(
            key="gemma-4-26b-a4b-vision",
            family="ocr_vision",
            role="vision_strong",
            display_name="Gemma 4 26B-A4B Vision (llama-swap)",
            unsloth_id=None,
            upstream_id="google/gemma-4-26B-A4B-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-4-26b-a4b",
            profile="hackathon",
            notes="Vision-language variant served from llama-swap.",
            capabilities=("ocr", "vision_qa", "figure_caption"),
        ),
        "gemma-4-12b-vision": ModelRegistryEntry(
            key="gemma-4-12b-vision",
            family="ocr_vision",
            role="vision_medium",
            display_name="Gemma 4 12B Vision (llama-swap)",
            unsloth_id=None,
            upstream_id="google/gemma-4-12B-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-4-12b",
            profile="hackathon",
            notes="Mid-tier vision alternative; faster cold-start than 26B.",
        ),
        "gemma-4-e4b-vision": ModelRegistryEntry(
            key="gemma-4-e4b-vision",
            family="ocr_vision",
            role="vision_light",
            display_name="Gemma 4 E4B Vision (llama-swap)",
            unsloth_id=None,
            upstream_id="google/gemma-4-E4B-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-4-e4b",
            profile="hackathon",
            notes="Lightweight Gemma 4 vision variant for low-latency reads.",
        ),
        "qwen3-vl-4b": ModelRegistryEntry(
            key="qwen3-vl-4b",
            family="ocr_vision",
            role="vision_fast",
            display_name="Qwen 3-VL 4B (llama-swap)",
            unsloth_id=None,
            upstream_id="Qwen/Qwen3-VL-4B-Instruct",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/qwen3-vl-4b",
            profile="dev",
            notes="Dev-only fast vision tier for the comparison harness.",
        ),
    }


def _embedder_entries() -> dict[str, ModelRegistryEntry]:
    return {
        "bge-m3": ModelRegistryEntry(
            key="bge-m3",
            family="embedder",
            role="default",
            display_name="BAAI/bge-m3 (multilingual, 1024-dim)",
            unsloth_id=None,
            upstream_id="BAAI/bge-m3",
            backend="local",
            available=True,
            litellm_alias="openai/bge-m3",
            profile="both",
            notes="Canonical Cianfhoghlaim embedder for all 14 CocoIndex flows.",
            languages=("en", "ga", "cy", "gd"),
        ),
    }


def _rerank_entries() -> dict[str, ModelRegistryEntry]:
    return {
        "bge-reranker-v2-m3": ModelRegistryEntry(
            key="bge-reranker-v2-m3",
            family="rerank",
            role="default",
            display_name="BAAI/bge-reranker-v2-m3",
            unsloth_id=None,
            upstream_id="BAAI/bge-reranker-v2-m3",
            backend="local",
            available=True,
            litellm_alias=None,
            profile="both",
            notes="Cross-encoder reranker for CocoIndex hybrid search.",
        ),
    }


def _image_gen_entries() -> dict[str, ModelRegistryEntry]:
    """The 7-entry image_gen family (matches meaisinfhoghlaim:v6)."""
    return {
        # Hackathon profile (default generative route for the submission)
        "diffusiongemma-26b-a4b": ModelRegistryEntry(
            key="diffusiongemma-26b-a4b",
            family="image_gen",
            role="default",
            display_name="DiffusionGemma 26B-A4B (Unsloth Studio)",
            unsloth_id="unsloth/diffusiongemma-26B-A4B-it-GGUF",
            upstream_id="google/diffusiongemma-26B-A4B-it",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/diffusiongemma-26b-a4b",
            profile="hackathon",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Hackathon-profile default generative model. Diffusion "
                "flagship of the Gemma family served from Unsloth Studio. "
                "Gemma-consistent with the Tier-2 text model so a "
                "certificate + visual asset pair share a family lineage."
            ),
            capabilities=("text_to_image", "image_to_image"),
        ),
        # Provenance-critical role (FIBO)
        "fibo": ModelRegistryEntry(
            key="fibo",
            family="image_gen",
            role="provenance",
            display_name="Bria FIBO (structured-JSON, ComfyUI)",
            unsloth_id=None,
            upstream_id="briaai/FIBO",
            backend="comfyui",
            available=True,
            litellm_alias=None,
            profile="hackathon",
            env_var="COMFYUI_BASE_URL",
            notes=(
                "JSON-native diffusion (camera, FOV, lighting, palette, "
                "composition as structured parameters). Trained on 1B+ "
                "fully-licensed images with commercial indemnity — the "
                "primary model for certificates. Stage-1 'palette' field "
                "directly maps the per-source palette into generation."
            ),
            capabilities=("text_to_image", "json_control", "palette_control"),
        ),
        # Quality flagship
        "flux2-dev": ModelRegistryEntry(
            key="flux2-dev",
            family="image_gen",
            role="quality",
            display_name="FLUX.2-dev (InvokeAI)",
            unsloth_id=None,
            upstream_id="black-forest-labs/FLUX.2-dev",
            backend="invokeai",
            available=True,
            litellm_alias="local/image/flux2-dev",
            profile="hackathon",
            notes="Quality flagship. Used for subject illustrations.",
            capabilities=("text_to_image", "image_to_image"),
        ),
        # Fast iteration
        "z-image-turbo": ModelRegistryEntry(
            key="z-image-turbo",
            family="image_gen",
            role="fast",
            display_name="Z-Image-Turbo (InvokeAI)",
            unsloth_id=None,
            upstream_id="stabilityai/z-image-turbo",
            backend="invokeai",
            available=True,
            litellm_alias="local/image/z-image-turbo",
            profile="both",
            notes="Fast iteration tier (4-step).",
            capabilities=("text_to_image"),
        ),
        # Bilingual (EN/GA) — Qwen-Image
        "qwen-image-2512": ModelRegistryEntry(
            key="qwen-image-2512",
            family="image_gen",
            role="bilingual",
            display_name="Qwen-Image 2512 (Unsloth Studio)",
            unsloth_id="unsloth/Qwen-Image-2512-GGUF",
            upstream_id="Qwen/Qwen-Image-2512",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/qwen-image-2512",
            profile="both",
            env_var="UNSLOTH_BASE_URL",
            notes="Bilingual EN/GA image model — preferred for Celtic assets.",
            capabilities=("text_to_image", "bilingual_text"),
        ),
        "qwen-image": ModelRegistryEntry(
            key="qwen-image",
            family="image_gen",
            role="legacy_bilingual",
            display_name="Qwen-Image (InvokeAI)",
            unsloth_id=None,
            upstream_id="Qwen/Qwen-Image",
            backend="invokeai",
            available=True,
            litellm_alias="local/image/qwen-image",
            profile="both",
            notes="Older Qwen-Image model, served via InvokeAI.",
        ),
        "sdxl": ModelRegistryEntry(
            key="sdxl",
            family="image_gen",
            role="legacy",
            display_name="SDXL (InvokeAI)",
            unsloth_id=None,
            upstream_id="stabilityai/sdxl",
            backend="invokeai",
            available=True,
            litellm_alias="local/image/sdxl",
            profile="both",
            notes="Legacy fallback. Will be deprecated post-submission.",
        ),
    }


def _voice_entries() -> dict[str, ModelRegistryEntry]:
    return {
        "orpheus-3b": ModelRegistryEntry(
            key="orpheus-3b",
            family="voice",
            role="tts",
            display_name="Orpheus 3B (Unsloth Studio TTS)",
            unsloth_id="unsloth/orpheus-3b-0.1-ft-GGUF",
            upstream_id="canopyai/Orpheus-3b-0.1-ft",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/orpheus-3b",
            profile="both",
            notes="TTS for the Irish/English/Celtic asset narration.",
        ),
        "sesame-csm-1b": ModelRegistryEntry(
            key="sesame-csm-1b",
            family="voice",
            role="tts_conversational",
            display_name="Sesame CSM 1B (Unsloth Studio)",
            unsloth_id="unsloth/sesame-csm-1b-GGUF",
            upstream_id="sesame/csm-1b",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/sesame-csm-1b",
            profile="both",
            notes="Conversational TTS for the agent chat surface.",
        ),
    }


def _translation_entries() -> dict[str, ModelRegistryEntry]:
    return {
        "minicpm-o-4_5": ModelRegistryEntry(
            key="minicpm-o-4_5",
            family="translation",
            role="multimodal",
            display_name="MiniCPM-o 4.5 (multimodal translation)",
            unsloth_id=None,
            upstream_id="openbmb/MiniCPM-o-4_5",
            backend="llama_swap",
            available=True,
            litellm_alias=None,
            profile="both",
            notes="Registry entry only — Phase-11 tie-in for certificates.",
        ),
    }


# ─── The registry singleton ───────────────────────────────────────────────


class ModelRegistry:
    """Holds every entry from every family and exposes ``resolve()``.

    Mirrors the upstream API: ``resolve(family, role)`` does a first-match
    linear scan over insertion order, so canonical / default entries MUST
    come first within a family.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ModelRegistryEntry] = {}
        for fam in (
            _text_llm_entries(),
            _ocr_vision_entries(),
            _embedder_entries(),
            _rerank_entries(),
            _image_gen_entries(),
            _voice_entries(),
            _translation_entries(),
        ):
            self._entries.update(fam)

    # ── Iteration / inspection ──
    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries.values())

    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def __getitem__(self, key: str) -> ModelRegistryEntry:
        return self._entries[key]

    def get(self, key: str, default: Any = None) -> ModelRegistryEntry | None:
        return self._entries.get(key, default)

    def entries(self) -> list[ModelRegistryEntry]:
        return list(self._entries.values())

    def keys(self) -> Iterable[str]:
        return self._entries.keys()

    def values(self) -> Iterable[ModelRegistryEntry]:
        return self._entries.values()

    def items(self):
        return self._entries.items()

    # ── Family / role / profile queries ──

    def filter(
        self,
        family: ModelFamily | None = None,
        *,
        role: str | None = None,
        available: bool | None = None,
        profile: ModelProfile | None = None,
    ) -> list[ModelRegistryEntry]:
        """Filter entries by family + role + availability + profile.

        ``profile="both"`` matches any active profile; ``profile="hackathon"``
        matches the hackathon active profile and ``profile="both"``.
        """
        results: list[ModelRegistryEntry] = []
        for entry in self._entries.values():
            if family is not None and entry.family != family:
                continue
            if role is not None and entry.role != role:
                continue
            if available is not None and entry.available != available:
                continue
            if profile is not None and not self._profile_matches(entry, profile):
                continue
            results.append(entry)
        return results

    @staticmethod
    def _profile_matches(entry: ModelRegistryEntry, active: ModelProfile) -> bool:
        if entry.profile == "both":
            return True
        return entry.profile == active

    def resolve(
        self,
        family: ModelFamily,
        role: str,
        *,
        profile: ModelProfile = "hackathon",
    ) -> ModelRegistryEntry | None:
        """First-match lookup of ``(family, role)`` within the active profile.

        Returns None when no match exists for the active profile.
        """
        for entry in self._entries.values():
            if entry.family != family or entry.role != role:
                continue
            if not self._profile_matches(entry, profile):
                continue
            return entry
        return None

    def for_profile(self, profile: ModelProfile) -> list[ModelRegistryEntry]:
        """Return every entry visible under ``profile``."""
        return self.filter(profile=profile)


# Module-level singleton.
MODEL_REGISTRY = ModelRegistry()


def model_for(
    family: ModelFamily,
    role: str,
    *,
    profile: ModelProfile | None = None,
) -> ModelRegistryEntry | None:
    """Convenience wrapper around ``MODEL_REGISTRY.resolve()``.

    ``profile`` defaults to the value of the ``MODEL_PROFILE`` environment
    variable (or ``hackathon`` if unset).
    """
    if profile is None:
        profile = _active_profile()
    return MODEL_REGISTRY.resolve(family, role, profile=profile)


def _active_profile() -> ModelProfile:
    """Read MODEL_PROFILE from the environment."""
    import os

    raw = os.environ.get("MODEL_PROFILE", "hackathon").strip().lower()
    if raw not in {"hackathon", "dev"}:
        logger.warning("unknown_model_profile_falling_back", extra={"got": raw})
        return "hackathon"
    return raw  # type: ignore[return-value]


__all__ = [
    "MODEL_REGISTRY",
    "ModelFamily",
    "ModelProfile",
    "ModelRegistry",
    "ModelRegistryEntry",
    "ModelRole",
    "model_for",
]
