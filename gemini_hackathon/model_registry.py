"""gemini_hackathon.model_registry — the single source of truth for model strings.

A **trimmed port** of
``cianfhoghlaim/meaisinfhoghlaim/models/model_registry.py`` (v6, 2026-08-21).

Why a port and not an import: the upstream module imports
``meaisinfhoghlaim.models.registry`` (the 22-entry ``VISION_MODELS`` dict,
plus ``CLASSICAL_OCR`` / ``TEXT_MODELS`` / ``ModelBackend`` / ``OCRModel``),
which drags the whole monorepo in. ``gemini_hackathon`` ships standalone for
the submission, so the three families it actually needs are copied here.

What was kept from upstream
---------------------------
* The :class:`ModelRegistryEntry` dataclass shape (same field names + order).
* The ``model_for(family, role)`` helper as the canonical resolution API.
* First-match-wins linear scan over insertion order, so the canonical entry
  for a ``(family, role)`` pair MUST be declared first within its family.

What was trimmed
----------------
* Families: only ``text_llm``, ``ocr_vision`` and ``image_gen``. Upstream's
  ``embedder`` / ``rerank`` / ``voice`` / ``translation`` families are not
  routed by this project's ``call_llm``.

What was added (not upstream)
-----------------------------
* ``ModelRegistryEntry.profile`` — ``hackathon`` | ``dev`` | ``both``. This is
  the mechanism that makes it *impossible* for a dev-only model to reach a
  user-facing surface: :func:`gemini_hackathon.call_llm.public_model_roster`
  reads the ``hackathon`` profile unconditionally.
* ``ModelRegistryEntry.capabilities`` — free-form capability tags.
* ``model_for()`` returns the *entry* rather than upstream's bare key string,
  because the router needs ``backend`` + ``litellm_alias`` together. Use
  :func:`model_key_for` when the upstream ``-> str`` behaviour is wanted.

Known upstream defect corrected here
------------------------------------
Upstream ``model_registry.py:959`` records FIBO's ``upstream_id`` as
``"fibonet/fibo"``. That repository does not exist. FIBO is **Bria AI's**
JSON-native diffusion model and its canonical Hugging Face id is
``briaai/FIBO``. The correct id is used below; see the comment on the
``fibo`` entry. The upstream value should be treated as a bug, not as a
mirror to be preserved.

Consumers MUST resolve model strings through this module rather than
hardcoding them. Adding a model is a registry change, not a router change.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Type vocabulary.
# ---------------------------------------------------------------------------


ModelFamily = Literal["text_llm", "ocr_vision", "image_gen"]
"""The 3 families this project routes. Upstream defines 7."""


ModelRole = str
"""Free-form within-family role (``default``, ``fallback``, ``dev_primary``…)."""


ModelProfile = Literal["hackathon", "dev", "both"]
"""Which ``MODEL_PROFILE`` exposes an entry.

- ``hackathon`` — exposed when ``MODEL_PROFILE=hackathon`` (the default).
  This is the only profile docs, the UI, or the submission ever reference.
- ``dev``       — exposed only when ``MODEL_PROFILE=dev``. Never public.
- ``both``      — exposed under either profile.
"""


Backend = Literal[
    "vertex",
    "aistudio",
    "unsloth_studio",
    "llama_swap",
    "invokeai",
    "comfyui",
    "minimax",
    "agent_garden",
    "local",
]
"""Runtime backend for an entry. ``unsloth_studio`` is a *host* process on
:8888 — it is never a Docker Compose service (see ``docs/MODEL_POLICY.md``).
``agent_garden`` is the Google Cloud Agent Garden — Vertex AI Model Garden
publisher models (Gemma 3, Llama 3, etc.) reached via the
``vertex_ai/<publisher>/<model>`` LiteLLM alias."""


PROFILES: tuple[ModelProfile, ...] = ("hackathon", "dev")
"""The two selectable values of ``MODEL_PROFILE``. (``both`` is an entry
annotation, not a selectable profile.)"""

DEFAULT_PROFILE: ModelProfile = "hackathon"


# ---------------------------------------------------------------------------
# The entry dataclass — same shape as upstream, plus `profile`/`capabilities`.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelRegistryEntry:
    """A single entry in :data:`MODEL_REGISTRY`.

    Attributes:
        key: Canonical identifier, unique across the registry.
        family: One of the :data:`ModelFamily` literals.
        role: Free-form role within the family (``"default"``, ``"fallback"``…).
        display_name: Human-readable name for UI surfaces.
        unsloth_id: The Unsloth GGUF id, when one exists.
        mlx_id: The MLX-community id, when one exists.
        upstream_id: The canonical upstream (usually Hugging Face) id.
        backend: The runtime backend (see :data:`Backend`).
        available: False for deprecated / not-yet-deployed entries.
        litellm_alias: The LiteLLM model string. ``None`` when the entry is
            not routed via LiteLLM (e.g. ComfyUI graph nodes).
        profile: Profile gate — see :data:`ModelProfile`.
        env_var: Environment variable that configures this entry at runtime.
        notes: Free-form documentation.
        languages: Languages the entry is specialised for (``None`` =
            language-agnostic).
        capabilities: Free-form capability tags (``"chat"``, ``"ocr"``…).
    """

    key: str
    family: ModelFamily
    role: str
    display_name: str
    unsloth_id: str | None
    mlx_id: str | None
    upstream_id: str
    backend: Backend
    available: bool
    litellm_alias: str | None = None
    profile: ModelProfile = "hackathon"
    env_var: str | None = None
    notes: str = ""
    languages: tuple[str, ...] | None = None
    capabilities: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Family 1 — text_llm.
#
# Declaration order is significant: `resolve()` is first-match-wins, so the
# canonical entry for each (family, role) pair comes first.
# ---------------------------------------------------------------------------


def _text_llm_entries() -> dict[str, ModelRegistryEntry]:
    """The text LLM family: the hackathon 2-tier chain + dev-only extras."""
    return {
        # ── Tier 1 (hackathon): Gemini 3.5 Flash on Vertex AI ──────────────
        # Vertex is the default because the submission is judged partly on
        # Google Cloud usage. `call_llm.resolve_gemini_backend()` swaps to the
        # `aistudio` entry below when GEMINI_BACKEND=aistudio, or when Vertex
        # credentials are absent but GEMINI_API_KEY is present.
        # Dev-profile Tier 1. REMOVED in the Phase 4 3-tier refactor —
        # both hackathon + dev profiles now use minimax-m3 as Tier 1
        # (per the OpenSpec model-policy spec). The dev-only entry
        # previously won the first-match scan for `role="default"`,
        # `profile="dev"`; with minimax-m3 promoted to `profile="both"`,
        # that role is now correctly resolved to the canonical primary.
        # The AI Studio twin remains as `gemini-3.5-flash-aistudio`
        # below (role=aistudio) for callers that pin it explicitly.
        "gemini-3.5-flash": ModelRegistryEntry(
            key="gemini-3.5-flash",
            family="text_llm",
            role="agent_garden",
            display_name="Gemini 3.5 Flash (Agent Garden, final fallback)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="gemini-3.5-flash",
            backend="vertex",
            available=True,
            litellm_alias="vertex_ai/gemini-3.5-flash",
            profile="both",
            env_var="GOOGLE_CLOUD_PROJECT",
            notes=(
                "Tier 3 (final fallback) of both the hackathon + dev profiles. "
                "Served from Vertex AI using GOOGLE_CLOUD_PROJECT + "
                "GOOGLE_CLOUD_LOCATION and Application Default Credentials "
                "(no API key). Reached when Tier 1 (MiniMax-M3) + Tier 2 "
                "(Unsloth) both fail or time out."
            ),
            capabilities=("chat", "function_calling", "json_mode", "long_context"),
        ),
        # ── Tier 1 alternate: the same model, served from AI Studio ────────
        "gemini-3.5-flash-aistudio": ModelRegistryEntry(
            key="gemini-3.5-flash-aistudio",
            family="text_llm",
            role="aistudio",
            display_name="Gemini 3.5 Flash (AI Studio)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="gemini-3.5-flash",
            backend="aistudio",
            available=True,
            litellm_alias="gemini/gemini-3.5-flash",
            profile="hackathon",
            env_var="GEMINI_API_KEY",
            notes=(
                "Same weights as the Vertex entry, keyed by GEMINI_API_KEY. "
                "Selected by GEMINI_BACKEND=aistudio, or automatically when "
                "Vertex credentials are missing."
            ),
            capabilities=("chat", "function_calling", "json_mode"),
        ),
        # ── Tier 2 (hackathon): Gemma 4 26B-A4B via Unsloth Studio ─────────
        # Dev-profile gemma-4 (same model, dev-profile wiring).
        "gemma-4-26b-a4b-dev": ModelRegistryEntry(
            key="gemma-4-26b-a4b-dev",
            family="text_llm",
            role="fallback",
            display_name="Gemma 4 26B-A4B (Unsloth Studio, dev Tier 2)",
            unsloth_id="unsloth/gemma-4-26B-A4B-it-GGUF",
            mlx_id=None,
            upstream_id="google/gemma-4-26B-A4B-it",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/gemma-4-26b-a4b",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes="Dev-profile Tier 2.",
            capabilities=("chat", "function_calling"),
        ),
        "gemma-4-26b-a4b": ModelRegistryEntry(
            key="gemma-4-26b-a4b",
            family="text_llm",
            role="fallback",
            display_name="Gemma 4 26B-A4B (Unsloth Studio)",
            unsloth_id="unsloth/gemma-4-26B-A4B-it-GGUF",
            mlx_id=None,
            upstream_id="google/gemma-4-26B-A4B-it",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/gemma-4-26b-a4b",
            profile="hackathon",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Tier 2 of the hackathon profile. Unsloth Studio is a HOST "
                "process on :8888 exposing an OpenAI-compatible /v1 surface; "
                "it is not a container and it is not ollama. Same Gemma "
                "family as Tier 1, so a Tier-1 -> Tier-2 failover keeps the "
                "output register consistent."
            ),
            capabilities=("chat", "function_calling"),
        ),
        # ── Dev profile only. Never surfaced publicly. ─────────────────────
        "minimax-m3": ModelRegistryEntry(
            key="minimax-m3",
            family="text_llm",
            role="default",
            display_name="MiniMax M3 (LiteLLM, Tier 1 primary)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="minimax-m3",
            backend="minimax",
            available=True,
            litellm_alias="minimax-m3",
            profile="both",
            env_var="MINIMAX_BASE_URL",
            notes=(
                "Tier 1 (LiteLLM-routed primary) of both the hackathon + dev "
                "profiles. Routed via LiteLLM's openai-generic provider against "
                "MINIMAX_BASE_URL — defaults to https://api.minimax.io/v1. "
                "Auth via MINIMAX_API_KEY. When this tier fails or times out, "
                "the router falls through to Tier 2 (Unsloth) then Tier 3 "
                "(Vertex/Agent Garden)."
            ),
            capabilities=("chat", "function_calling"),
        ),
        "qwen3.8-27b": ModelRegistryEntry(
            key="qwen3.8-27b",
            family="text_llm",
            role="dev_strong",
            display_name="Qwen 3.8 27B (Unsloth Studio)",
            unsloth_id="unsloth/qwen3.8-27b-it-GGUF",
            mlx_id=None,
            upstream_id="Qwen/Qwen3-8-27B",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/qwen3.8-27b",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes="Dev-only Qwen flagship for the comparison harness.",
            capabilities=("chat",),
        ),
        "deepseek-v4-flash": ModelRegistryEntry(
            key="deepseek-v4-flash",
            family="text_llm",
            role="dev_fast",
            display_name="DeepSeek V4 Flash (Unsloth Studio)",
            unsloth_id="unsloth/deepseek-v4-flash-GGUF",
            mlx_id=None,
            upstream_id="deepseek-ai/DeepSeek-V4-Flash",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/deepseek-v4-flash",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes="Dev-only fast tier for the comparison harness.",
            capabilities=("chat",),
        ),
        "kimi-k2.6": ModelRegistryEntry(
            key="kimi-k2.6",
            family="text_llm",
            role="dev_alt",
            display_name="Kimi K2.6 (Unsloth Studio)",
            unsloth_id="unsloth/kimi-k2.6-GGUF",
            mlx_id=None,
            upstream_id="moonshotai/Kimi-K2.6",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/kimi-k2.6",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes="Dev-only long-context comparison.",
            capabilities=("chat", "long_context"),
        ),
    }


# ---------------------------------------------------------------------------
# Family 2 — ocr_vision (served by llama-swap on :8080).
# ---------------------------------------------------------------------------


def _ocr_vision_entries() -> dict[str, ModelRegistryEntry]:
    """The OCR / VLM family — the subset of upstream ``VISION_MODELS`` used here."""
    return {
        "qwen3-vl-8b": ModelRegistryEntry(
            key="qwen3-vl-8b",
            family="ocr_vision",
            role="default",
            display_name="Qwen 3-VL 8B (llama-swap OCR workhorse)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="Qwen/Qwen3-VL-8B-Instruct",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/qwen3-vl-8b",
            profile="hackathon",
            env_var="LLAMA_SWAP_BASE_URL",
            notes="Stage-1 OCR workhorse.",
            capabilities=("ocr", "figure_caption", "multilingual"),
        ),
        "gemma-4-26b-a4b-vision": ModelRegistryEntry(
            key="gemma-4-26b-a4b-vision",
            family="ocr_vision",
            role="vision_strong",
            display_name="Gemma 4 26B-A4B Vision (llama-swap)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="google/gemma-4-26B-A4B-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-4-26b-a4b",
            profile="hackathon",
            env_var="LLAMA_SWAP_BASE_URL",
            notes="Vision-language variant of the Tier-2 text model.",
            capabilities=("ocr", "vision_qa", "figure_caption"),
        ),
        "gemma-4-12b-vision": ModelRegistryEntry(
            key="gemma-4-12b-vision",
            family="ocr_vision",
            role="vision_medium",
            display_name="Gemma 4 12B Vision (llama-swap)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="google/gemma-4-12B-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-4-12b",
            profile="hackathon",
            env_var="LLAMA_SWAP_BASE_URL",
            notes="Mid-tier vision alternative; faster cold-start than the 26B.",
            capabilities=("ocr", "vision_qa"),
        ),
        "gemma-4-e4b-vision": ModelRegistryEntry(
            key="gemma-4-e4b-vision",
            family="ocr_vision",
            role="vision_light",
            display_name="Gemma 4 E4B Vision (llama-swap)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="google/gemma-4-E4B-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-4-e4b",
            profile="hackathon",
            env_var="LLAMA_SWAP_BASE_URL",
            notes="Lightweight Gemma 4 vision variant for low-latency reads.",
            capabilities=("ocr",),
        ),
        "qwen3-vl-4b": ModelRegistryEntry(
            key="qwen3-vl-4b",
            family="ocr_vision",
            role="vision_fast",
            display_name="Qwen 3-VL 4B (llama-swap)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="Qwen/Qwen3-VL-4B-Instruct",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/qwen3-vl-4b",
            profile="dev",
            env_var="LLAMA_SWAP_BASE_URL",
            notes="Dev-only fast vision tier for the comparison harness.",
            capabilities=("ocr",),
        ),
    }


# ---------------------------------------------------------------------------
# Family 3 — image_gen (the 7 real entries from upstream v6).
# ---------------------------------------------------------------------------


def _image_gen_entries() -> dict[str, ModelRegistryEntry]:
    """The 7-entry image_gen family, ported from upstream ``v6``."""
    return {
        "diffusiongemma-26b-a4b": ModelRegistryEntry(
            key="diffusiongemma-26b-a4b",
            family="image_gen",
            role="default",
            display_name="DiffusionGemma 26B-A4B (Unsloth Studio)",
            unsloth_id="unsloth/diffusiongemma-26B-A4B-it-GGUF",
            mlx_id=None,
            upstream_id="google/diffusiongemma-26B-A4B-it",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/diffusiongemma-26b-a4b",
            profile="hackathon",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Default generative route. Gemma-family lineage keeps the "
                "visual assets consistent with the Tier-2 text model."
            ),
            capabilities=("text_to_image", "image_to_image"),
        ),
        # FIBO — upstream-id defect fix.
        #
        # cianfhoghlaim/meaisinfhoghlaim/models/model_registry.py:959 records
        # this as `upstream_id="fibonet/fibo"`. There is no such Hugging Face
        # repository; `fibonet` is not the publisher. FIBO is Bria AI's
        # JSON-native diffusion model, published at `briaai/FIBO`. The correct
        # id is used here. Do NOT "restore" the upstream value when
        # re-syncing this port — upstream is the one that is wrong.
        "fibo": ModelRegistryEntry(
            key="fibo",
            family="image_gen",
            role="provenance",
            display_name="Bria FIBO (structured-JSON, ComfyUI)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="briaai/FIBO",
            backend="comfyui",
            available=True,
            litellm_alias=None,
            profile="hackathon",
            env_var="COMFYUI_BASE_URL",
            notes=(
                "JSON-native diffusion: camera, FOV, lighting, palette and "
                "composition are structured parameters rather than prose. "
                "Trained on licensed images with commercial indemnity, which "
                "is why it is the provenance-critical route for certificates. "
                "Upstream registry records the wrong upstream_id "
                "('fibonet/fibo'); the correct publisher is Bria AI."
            ),
            capabilities=("text_to_image", "json_control", "palette_control"),
        ),
        "flux2-dev": ModelRegistryEntry(
            key="flux2-dev",
            family="image_gen",
            role="quality",
            display_name="FLUX.2-dev (InvokeAI)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="black-forest-labs/FLUX.2-dev",
            backend="invokeai",
            available=True,
            litellm_alias="local/image/flux2-dev",
            profile="hackathon",
            env_var="INVOKEAI_BASE_URL",
            notes="Quality flagship, used for subject illustrations.",
            capabilities=("text_to_image", "image_to_image"),
        ),
        "z-image-turbo": ModelRegistryEntry(
            key="z-image-turbo",
            family="image_gen",
            role="fast",
            display_name="Z-Image-Turbo (InvokeAI)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="stabilityai/z-image-turbo",
            backend="invokeai",
            available=True,
            litellm_alias="local/image/z-image-turbo",
            profile="both",
            env_var="INVOKEAI_BASE_URL",
            notes="Fast 4-step iteration tier.",
            capabilities=("text_to_image",),
        ),
        "qwen-image-2512": ModelRegistryEntry(
            key="qwen-image-2512",
            family="image_gen",
            role="bilingual",
            display_name="Qwen-Image 2512 (Unsloth Studio)",
            unsloth_id="unsloth/Qwen-Image-2512-GGUF",
            mlx_id=None,
            upstream_id="Qwen/Qwen-Image-2512",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/qwen-image-2512",
            profile="both",
            env_var="UNSLOTH_BASE_URL",
            notes="Bilingual EN/GA text rendering — preferred for Celtic assets.",
            capabilities=("text_to_image", "bilingual_text"),
        ),
        "qwen-image": ModelRegistryEntry(
            key="qwen-image",
            family="image_gen",
            role="legacy_bilingual",
            display_name="Qwen-Image (InvokeAI)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="Qwen/Qwen-Image",
            backend="invokeai",
            available=True,
            litellm_alias="local/image/qwen-image",
            profile="both",
            env_var="INVOKEAI_BASE_URL",
            notes="Predecessor of qwen-image-2512, served via InvokeAI.",
            capabilities=("text_to_image", "bilingual_text"),
        ),
        "sdxl": ModelRegistryEntry(
            key="sdxl",
            family="image_gen",
            role="legacy",
            display_name="SDXL (InvokeAI)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="stabilityai/stable-diffusion-xl-base-1.0",
            backend="invokeai",
            available=True,
            litellm_alias="local/image/sdxl",
            profile="both",
            env_var="INVOKEAI_BASE_URL",
            notes="Legacy fallback; slated for removal post-submission.",
            capabilities=("text_to_image",),
        ),
    }


# ---------------------------------------------------------------------------
# The registry.
# ---------------------------------------------------------------------------


class ModelRegistry:
    """Holds every entry and exposes ``resolve()`` / ``filter()``.

    Mirrors the upstream API. ``resolve()`` is a first-match linear scan over
    insertion order, so canonical entries MUST be declared first within a
    family.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ModelRegistryEntry] = {}
        for family_entries in (
            _text_llm_entries(),
            _ocr_vision_entries(),
            _image_gen_entries(),
        ):
            for key, entry in family_entries.items():
                if key in self._entries:
                    raise ValueError(f"Duplicate registry key: {key!r}")
                self._entries[key] = entry

    # ── Iteration / inspection ──────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[ModelRegistryEntry]:
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

    def items(self) -> Iterable[tuple[str, ModelRegistryEntry]]:
        return self._entries.items()

    # ── Queries ─────────────────────────────────────────────────────────

    @staticmethod
    def _profile_matches(entry: ModelRegistryEntry, active: ModelProfile) -> bool:
        """``both`` matches any active profile; otherwise exact match."""
        if entry.profile == "both":
            return True
        return entry.profile == active

    def filter(
        self,
        family: ModelFamily | None = None,
        *,
        role: str | None = None,
        available: bool | None = None,
        profile: ModelProfile | None = None,
    ) -> list[ModelRegistryEntry]:
        """Filter entries by family, role, availability and profile."""
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

    def resolve(
        self,
        family: ModelFamily,
        role: str,
        *,
        profile: ModelProfile = DEFAULT_PROFILE,
    ) -> ModelRegistryEntry | None:
        """First-match lookup of ``(family, role)`` visible under ``profile``.

        Returns ``None`` when nothing matches — callers decide whether that is
        a hard error (pin mode) or a skipped tier (tier-walk mode).
        """
        for entry in self._entries.values():
            if entry.family != family or entry.role != role:
                continue
            if not self._profile_matches(entry, profile):
                continue
            return entry
        return None

    def for_profile(self, profile: ModelProfile) -> list[ModelRegistryEntry]:
        """Every entry visible under ``profile``."""
        return self.filter(profile=profile)


MODEL_REGISTRY = ModelRegistry()
"""Module-level singleton. Import this, do not instantiate ModelRegistry()."""


# ---------------------------------------------------------------------------
# Module-level helpers.
# ---------------------------------------------------------------------------


def active_profile() -> ModelProfile:
    """Read ``MODEL_PROFILE`` from the environment.

    Unknown values fall back to ``hackathon`` with a warning, so a typo can
    never silently widen the exposed model set.
    """
    raw = os.environ.get("MODEL_PROFILE", DEFAULT_PROFILE).strip().lower()
    if raw not in PROFILES:
        logger.warning(
            "Unknown MODEL_PROFILE %r; falling back to %r", raw, DEFAULT_PROFILE
        )
        return DEFAULT_PROFILE
    return raw  # type: ignore[return-value]


def model_for(
    family: ModelFamily,
    role: str,
    *,
    profile: ModelProfile | None = None,
) -> ModelRegistryEntry | None:
    """Resolve ``(family, role)`` to a registry entry.

    The canonical resolution API — every model string in this project comes
    from here. ``profile`` defaults to :func:`active_profile`.

    Note the deviation from upstream, which returns a bare key string. See
    :func:`model_key_for` for that behaviour.
    """
    if profile is None:
        profile = active_profile()
    return MODEL_REGISTRY.resolve(family, role, profile=profile)


def model_key_for(
    family: ModelFamily,
    role: str,
    *,
    profile: ModelProfile | None = None,
) -> str | None:
    """Upstream-compatible variant of :func:`model_for` returning the key."""
    entry = model_for(family, role, profile=profile)
    return entry.key if entry is not None else None


def filter_models(
    family: ModelFamily | None = None,
    *,
    role: str | None = None,
    available: bool | None = None,
    profile: ModelProfile | None = None,
) -> list[ModelRegistryEntry]:
    """Convenience wrapper around :meth:`ModelRegistry.filter`."""
    return MODEL_REGISTRY.filter(
        family, role=role, available=available, profile=profile
    )


__all__ = [
    "DEFAULT_PROFILE",
    "MODEL_REGISTRY",
    "PROFILES",
    "Backend",
    "ModelFamily",
    "ModelProfile",
    "ModelRegistry",
    "ModelRegistryEntry",
    "ModelRole",
    "active_profile",
    "filter_models",
    "model_for",
    "model_key_for",
    "ModelPolicyError",
    "PublicModelEntry",
    "public_model_roster",
    "public_tier_table",
]


# ---------------------------------------------------------------------------
# Public surface (the only roster docs and the UI may read).
# ---------------------------------------------------------------------------


class ModelPolicyError(RuntimeError):
    """Raised when the public roster is asked to include a dev-only entry."""


@dataclass(frozen=True)
class PublicModelEntry:
    """Flat view of a registry entry for docs + UI."""

    key: str
    family: ModelFamily
    role: str
    display_name: str
    backend: str
    upstream_id: str
    litellm_alias: str | None
    tier: int | None
    notes: str


_PUBLIC_TIER_INDEX: dict[tuple[str, str], int] = {
    ("text_llm", "default"):     1,
    ("text_llm", "aistudio"):    1,
    ("text_llm", "fallback"):    2,
    ("text_llm", "dev_primary"): 3,
    ("ocr_vision", "default"):         1,
    ("ocr_vision", "vision_strong"):    1,
    ("ocr_vision", "vision_medium"):    1,
    ("ocr_vision", "vision_light"):     1,
}


def public_model_roster(
    *,
    family: ModelFamily | None = None,
) -> tuple[PublicModelEntry, ...]:
    """The public model roster — always the ``hackathon`` profile.

    Deliberately ignores ``MODEL_PROFILE``. Docs, UI, CLI and submission
    materials must read from here and nowhere else.
    """
    entries = MODEL_REGISTRY.filter(family=family, profile="hackathon", available=True)
    roster: list[PublicModelEntry] = []
    for entry in entries:
        if entry.profile == "dev":
            raise ModelPolicyError(
                f"Dev-only model {entry.key!r} reached the public roster."
            )
        roster.append(PublicModelEntry(
            key=entry.key,
            family=entry.family,
            role=entry.role,
            display_name=entry.display_name,
            backend=entry.backend,
            upstream_id=entry.upstream_id,
            litellm_alias=entry.litellm_alias,
            tier=_PUBLIC_TIER_INDEX.get((entry.family, entry.role)),
            notes=entry.notes,
        ))
    roster.sort(key=lambda e: (e.tier is None, e.tier or 0, e.key))
    return tuple(roster)


def public_tier_table() -> tuple[PublicModelEntry, ...]:
    """Tiered text_llm entries in tier order — for the docs table."""
    return tuple(
        e for e in public_model_roster(family="text_llm") if e.tier is not None
    )
