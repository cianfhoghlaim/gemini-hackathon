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


ModelFamily = Literal[
    "text_llm",
    "ocr_vision",
    "image_gen",
    "learning_graph",
    "embedder",
    "rerank",
    "voice",
    "translation",
]
"""The families this project routes.

The ``learning_graph`` family was added in the
2026-08-31-uk-ncce-learning-graph-showcase-v1 change (the canonical NCCE
showcase). The ``embedder`` / ``rerank`` / ``voice`` / ``translation``
families were lifted from the previously-duplicate
``gemini_hackathon/models/__init__.py`` registry (deleted in the
2026-08-31-fix-critical-import-bugs-v1 Phase 0 change) so this module
is the **single** canonical model registry for the project.

Upstream defines 7 of these; the docstring at lines 19-23 is now stale
and the ``text_llm`` / ``ocr_vision`` / ``image_gen`` only claim is
no longer accurate — every family listed here is real and routable
either via ``call_llm`` (text_llm / ocr_vision) or via the
domain-specific consumer (image_gen / learning_graph / embedder /
rerank / voice / translation)."""


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
        # ── Tier 1 PRIMARY (hackathon + dev): Gemini 3.5 Flash on Vertex AI ──
        # Per the 2026-08-30 Gemma+Gemini refocus (this commit): promoted
        # from `role="agent_garden"` (the Tier-3 final fallback) to
        # `role="default"` (the Tier-1 primary). Vertex is the default
        # because the submission is judged partly on Google Cloud usage.
        # `call_llm.resolve_gemini_backend()` swaps to the `aistudio` entry
        # below when GEMINI_BACKEND=aistudio, or when Vertex credentials
        # are absent but GEMINI_API_KEY is present.
        "gemini-3.5-flash": ModelRegistryEntry(
            key="gemini-3.5-flash",
            family="text_llm",
            role="default",
            display_name="Gemini 3.5 Flash (Vertex, Tier 1 primary)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="gemini-3.5-flash",
            backend="vertex",
            available=True,
            litellm_alias="vertex_ai/gemini-3.5-flash",
            profile="both",
            env_var="GOOGLE_CLOUD_PROJECT",
            notes=(
                "Tier 1 PRIMARY (hackathon + dev). Served from Vertex AI "
                "using GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION and "
                "Application Default Credentials (no API key). When "
                "Vertex creds are missing but GEMINI_API_KEY is present, "
                "the call_llm router auto-swaps to gemini-3.5-flash-aistudio."
            ),
            capabilities=("chat", "function_calling", "json_mode", "long_context"),
        ),
        # ── Tier 1 PRI: same model via AI Studio (auto-fallback) ──────────
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
        # ── Tier 1 LITE: Gemini 3.5 Flash Lite (NEW per 2026-08-30 refocus) ─
        # Low-cost high-volume extraction tier. Same family, same backend.
        "gemini-3.5-flash-lite": ModelRegistryEntry(
            key="gemini-3.5-flash-lite",
            family="text_llm",
            role="lite",
            display_name="Gemini 3.5 Flash Lite (AI Studio)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="gemini-3.5-flash-lite",
            backend="aistudio",
            available=True,
            litellm_alias="gemini/gemini-3.5-flash-lite",
            profile="hackathon",
            env_var="GEMINI_API_KEY",
            notes=(
                "Tier 1 lite. Lower cost / higher throughput than flash; "
                "preferred for the high-volume NCCE BAML extraction sweeps."
            ),
            capabilities=("chat", "json_mode"),
        ),
        # ── Tier 1 EVAL (dev only): Gemini 3.5 Pro ─────────────────────────
        # Phase 5b — for the model comparison harness. Higher quality than
        # Flash; same Vertex AI backend, higher pricing ($1.25 / $5.00 per M).
        "gemini-3.5-pro": ModelRegistryEntry(
            key="gemini-3.5-pro",
            family="text_llm",
            role="pro",
            display_name="Gemini 3.5 Pro (Vertex, eval-tier)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="gemini-3.5-pro",
            backend="vertex",
            available=True,
            litellm_alias="vertex_ai/gemini-3.5-pro",
            profile="dev",
            env_var="GOOGLE_CLOUD_PROJECT",
            notes=(
                "Dev-profile only. Phase 5 model comparison harness. "
                "Same Vertex AI backend as gemini-3.5-flash; higher cost."
            ),
            capabilities=("chat", "function_calling", "json_mode", "long_context"),
        ),
        # ── Tier 1 ALT: Gemini 2.5 Flash (ADK-examples compat per docs/ideas) ─
        "gemini-2.5-flash": ModelRegistryEntry(
            key="gemini-2.5-flash",
            family="text_llm",
            role="alt",
            display_name="Gemini 2.5 Flash (Vertex, ADK-examples compat)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="gemini-2.5-flash",
            backend="vertex",
            available=True,
            litellm_alias="vertex_ai/gemini-2.5-flash",
            profile="both",
            env_var="GOOGLE_CLOUD_PROJECT",
            notes=(
                "Compatibility tier for the docs/ideas/Agent Development Kit "
                "examples that use MODEL_GEMINI_FLASH=gemini-2.5-flash."
            ),
            capabilities=("chat", "function_calling", "json_mode"),
        ),
        # ── Tier 1 EMBEDDING (NEW per 2026-08-30 refocus) ────────────────────
        "gemini-embedding-2-preview": ModelRegistryEntry(
            key="gemini-embedding-2-preview",
            family="text_llm",
            role="embedder",
            display_name="Gemini Embedding 2 Preview (AI Studio)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="gemini-embedding-2-preview",
            backend="aistudio",
            available=True,
            litellm_alias="gemini/gemini-embedding-2-preview",
            profile="hackathon",
            env_var="GEMINI_API_KEY",
            notes=(
                "Tier 1 embeddings. Replaces the prior BGE-M3 default for "
                "the BAML ExtractCrossLinguisticConcept text path. "
                "Family=LiteLLM embedder role (separate from chat models)."
            ),
            capabilities=("embed",),
        ),
        # ── Tier 2 PRIMARY (hackathon): Gemma 4 26B-A4B via Unsloth Studio ──
        "gemma-4-26b-a4b": ModelRegistryEntry(
            key="gemma-4-26b-a4b",
            family="text_llm",
            role="fallback",
            display_name="Gemma 4 26B-A4B (Unsloth Studio, Tier 2 primary)",
            unsloth_id="unsloth/gemma-4-26B-A4B-it-GGUF",
            mlx_id=None,
            upstream_id="google/gemma-4-26B-A4B-it",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/gemma-4-26b-a4b",
            profile="hackathon",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Tier 2 of the hackathon profile (the +0.2 'Google AI "
                "model integration' bonus). Unsloth Studio is a HOST "
                "process on :8888 exposing an OpenAI-compatible /v1 surface; "
                "it is not a container and it is not ollama."
            ),
            capabilities=("chat", "function_calling"),
        ),
        # ── Tier 2 LIGHT (hackathon): Gemma 4 E4B ───────────────────────────
        "gemma-4-e4b": ModelRegistryEntry(
            key="gemma-4-e4b",
            family="text_llm",
            role="fallback_light",
            display_name="Gemma 4 E4B (Unsloth Studio, Tier 2 light)",
            unsloth_id="unsloth/gemma-4-E4B-it-GGUF",
            mlx_id=None,
            upstream_id="google/gemma-4-E4B-it",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/gemma-4-e4b",
            profile="hackathon",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Tier 2 light. ~3GB on disk; much faster cold-start than "
                "the 26B-A4B. Used for low-latency Tier-2 reads."
            ),
            capabilities=("chat",),
        ),
        # ── Tier 2 BENCHMARK (dev): Gemma 3 27B (prior-gen vs Gemma 4) ─────
        "gemma-3-27b-it": ModelRegistryEntry(
            key="gemma-3-27b-it",
            family="text_llm",
            role="local_fallback",
            display_name="Gemma 3 27B IT (Unsloth Studio, dev benchmark)",
            unsloth_id="unsloth/gemma-3-27b-it-GGUF",
            mlx_id=None,
            upstream_id="google/gemma-3-27b-it",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/gemma-3-27b-it",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Dev-profile Gemma 3 prior-generation benchmark. Used in "
                "the comparison harness to grade Gemma 4 improvements."
            ),
            capabilities=("chat",),
        ),
        # ── Tier 2 BENCHMARK (dev): Gemma 2 9B (older baseline) ────────────
        "gemma-2-9b": ModelRegistryEntry(
            key="gemma-2-9b",
            family="text_llm",
            role="local_fallback_old",
            display_name="Gemma 2 9B (Unsloth Studio, dev baseline)",
            unsloth_id="unsloth/gemma-2-9b",
            mlx_id=None,
            upstream_id="google/gemma-2-9b",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/gemma-2-9b",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Dev-profile Gemma 2 baseline for the comparison harness. "
                "Smaller + cheaper than the Gemma 4 family; useful for fast "
                "iteration on the dev harness."
            ),
            capabilities=("chat",),
        ),
        # ── Tier 2 ENCODER-DECODER (dev): T5Gemma-2 4B ─────────────────────
        "t5gemma-2-4b": ModelRegistryEntry(
            key="t5gemma-2-4b",
            family="text_llm",
            role="dev_encoder_decoder",
            display_name="T5Gemma-2 4B (Unsloth Studio, encoder-decoder)",
            unsloth_id="unsloth/t5gemma-2-4b-GGUF",
            mlx_id=None,
            upstream_id="google/t5gemma-2-4b",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/t5gemma-2-4b",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes=(
                "Dev-profile encoder-decoder variant per "
                "docs/ideas/bilingual-datasets.md (Phase 0/5 of the "
                "Gemini 3 + T5Gemma-2 architecture proposal)."
            ),
            capabilities=("chat", "long_context"),
        ),
    }


# ---------------------------------------------------------------------------
# Family 2 — ocr_vision (served by llama-swap on :8080).
# ---------------------------------------------------------------------------


def _ocr_vision_entries() -> dict[str, ModelRegistryEntry]:
    """The OCR / VLM family — Gemma-only per the 2026-08-30 refocus."""
    return {
        "gemma-4-26b-a4b-vision": ModelRegistryEntry(
            key="gemma-4-26b-a4b-vision",
            family="ocr_vision",
            role="default",
            display_name="Gemma 4 26B-A4B Vision (llama-swap, OCR primary)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="google/gemma-4-26B-A4B-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-4-26b-a4b-vision",
            profile="hackathon",
            env_var="LLAMA_SWAP_BASE_URL",
            notes=(
                "OCR/VLM primary. Vision-language variant of the Tier-2 "
                "text model. Replaces the previous qwen3-vl-8b workhorse "
                "(per the 2026-08-30 Gemma+Gemini refocus)."
            ),
            capabilities=("ocr", "vision_qa", "figure_caption", "multilingual"),
        ),
        "gemma-4-12b-vision": ModelRegistryEntry(
            key="gemma-4-12b-vision",
            family="ocr_vision",
            role="vision_medium",
            display_name="Gemma 4 12B Vision (llama-swap)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="google/gemma-4-12b-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-4-12b-vision",
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
            litellm_alias="openai/gemma-4-e4b-vision",
            profile="hackathon",
            env_var="LLAMA_SWAP_BASE_URL",
            notes="Lightweight Gemma 4 vision variant for low-latency reads.",
            capabilities=("ocr",),
        ),
        "gemma-3-12b-vision": ModelRegistryEntry(
            key="gemma-3-12b-vision",
            family="ocr_vision",
            role="vision_prior_gen",
            display_name="Gemma 3 12B Vision (llama-swap, dev benchmark)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="google/gemma-3-12b-it",
            backend="llama_swap",
            available=True,
            litellm_alias="openai/gemma-3-12b-vision",
            profile="dev",
            env_var="LLAMA_SWAP_BASE_URL",
            notes=(
                "Dev-profile prior-generation benchmark. Used to grade "
                "Gemma 4 vision improvements in the comparison harness."
            ),
            capabilities=("ocr", "vision_qa"),
        ),
        "gemma-3n-E4B-vision": ModelRegistryEntry(
            key="gemma-3n-E4B-vision",
            family="ocr_vision",
            role="vision_mobile",
            display_name="Gemma 3n E4B Vision (llama-swap, mobile-optimised)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="google/gemma-3n-E4B-it",
            backend="llama_swap",
            available=False,  # gated: verify HF id before activating
            litellm_alias="openai/gemma-3n-E4B-vision",
            profile="hackathon",
            env_var="LLAMA_SWAP_BASE_URL",
            notes=(
                "Mobile-optimised Gemma 3n (per docs/ideas/Irish Handwriting "
                "App Development.md §4.2). NOTE: gated behind available=False "
                "until the upstream google/gemma-3n-E4B-it repo + a community "
                "q4_k_m GGUF quant is verified on HuggingFace. To activate, "
                "set available=True + add the GGUF download to the llama-swap "
                "download script."
            ),
            capabilities=("ocr", "vision_qa", "mobile_optimised"),
        ),
    }


# ---------------------------------------------------------------------------
# Family 4 — learning_graph (the NCCE showcase artefacts).
#
# Added in the 2026-08-31-uk-ncce-learning-graph-showcase-v1 change. Each
# entry corresponds to one of the 5 NCCE PDFs lifted from the upstream
# leabharlann/ollscoil_na_gaillimhe source + the canonical per-subject
# extracted-graph assets. These are NOT models in the LLM/VLM sense —
# they are the canonical artefact identifiers used by the BIEP learning-
# graph substrate (DLT resource → Firestore collection → Gradio studio).
# ---------------------------------------------------------------------------


def _learning_graph_entries() -> dict[str, ModelRegistryEntry]:
    """The NCCE learning-graph family — 5 PDF artefacts + 1 showcase composite."""
    return {
        # The 5 NCCE PDF artefacts (lifted verbatim from the upstream
        # cianfhoghlaim leabharlann/ source). Each entry is the canonical
        # slug used by the BIEP substrate.
        "ncce_y8_python": ModelRegistryEntry(
            key="ncce_y8_python",
            family="learning_graph",
            role="learning_graph",
            display_name="NCCE Y8 Intro to Python Programming (the showcase)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="local://data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_intro_to_python_programming_y8.pdf",
            backend="local",
            available=True,
            litellm_alias=None,
            profile="both",
            env_var="BI_EP_NCCE_RAW_ROOT",
            notes=(
                "The canonical NCCE learning-graph showcase artefact — a "
                "4-row × 7-column grid mapping Y8 Python programming outcomes "
                "to lesson columns + a prerequisite arrow graph. Lifted "
                "verbatim from the upstream cianfhoghlaim leabharlann "
                "source on 2026-08-31."
            ),
            capabilities=("learning_graph", "uk_ncce", "computer_science"),
        ),
        "ncce_y7_scratch": ModelRegistryEntry(
            key="ncce_y7_scratch",
            family="learning_graph",
            role="learning_graph",
            display_name="NCCE Y7 Programming Essentials in Scratch (Parts I & II)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="local://data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf",
            backend="local",
            available=True,
            litellm_alias=None,
            profile="both",
            env_var="BI_EP_NCCE_RAW_ROOT",
            notes=(
                "Y7 Scratch unit learning graph — 6-column grid with 3 "
                "cross-cutting skill ribbons (decomposition, abstraction, "
                "evaluation)."
            ),
            capabilities=("learning_graph", "uk_ncce", "computer_science"),
        ),
        "ncce_y6_variables": ModelRegistryEntry(
            key="ncce_y6_variables",
            family="learning_graph",
            role="learning_graph",
            display_name="NCCE Y6 Variables in Games",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="local://data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_variables_in_games_y6.pdf",
            backend="local",
            available=True,
            litellm_alias=None,
            profile="both",
            env_var="BI_EP_NCCE_RAW_ROOT",
            notes=(
                "Y6 unit grid — the earliest year covered by an NCCE "
                "learning graph. Variables-in-games is the canonical "
                "introduction to programming concepts."
            ),
            capabilities=("learning_graph", "uk_ncce", "computer_science"),
        ),
        "ncce_pedagogy_principles": ModelRegistryEntry(
            key="ncce_pedagogy_principles",
            family="learning_graph",
            role="pedagogy_principles",
            display_name="NCCE 12 Pedagogy Principles",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="local://data/bi_ep/syllabi_raw/uk_ncce/curriculum/pedagogy_principles.pdf",
            backend="local",
            available=True,
            litellm_alias=None,
            profile="both",
            env_var="BI_EP_NCCE_RAW_ROOT",
            notes=(
                "The 12 named NCCE pedagogy principles (Lead with concepts, "
                "Work together, Get hands-on, …). Consumed by "
                "ExtractPedagogyPrinciples and overlaid onto learning-graph "
                "cells by Change C (`2026-08-31-pedagogy-overlay-renderer-v1`)."
            ),
            capabilities=("learning_graph", "uk_ncce", "pedagogy"),
        ),
        "ncce_curriculum_journey": ModelRegistryEntry(
            key="ncce_curriculum_journey",
            family="learning_graph",
            role="curriculum_journey",
            display_name="NCCE Full Curriculum Journey Y7-Y11 (2024-2025)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="https://ncce-curriculum-production.s3.eu-west-1.amazonaws.com/qvz4tnrz4y7rrxayqz2qfji94nko",
            backend="local",
            available=True,
            litellm_alias=None,
            profile="both",
            env_var="BI_EP_NCCE_RAW_ROOT",
            notes=(
                "Full NCCE Computing journey from Y7 to Y11. The 5th NCCE "
                "PDF; download is deferred (the placeholder JSON at "
                "data/bi_ep/syllabi_raw/uk_ncce/curriculum/curriculum_journey_full_2024_2025.placeholder.json "
                "records the S3 URL + status)."
            ),
            capabilities=("learning_graph", "uk_ncce", "curriculum_journey"),
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
        # kept invokeai variant per Phase 0 critical-fix #1; llama_swap variant removed
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
            display_name="Qwen-Image 2512 (Unsloth Studio) — REMOVED 2026-08-30",
            unsloth_id=None,  # was "unsloth/Qwen-Image-2512-GGUF"
            mlx_id=None,
            upstream_id="Qwen/Qwen-Image-2512",
            backend="unsloth_studio",
            available=False,  # REMOVED in the 2026-08-30 Gemma+Gemini refocus
            litellm_alias=None,
            profile="both",
            env_var=None,
            notes=(
                "REMOVED 2026-08-30 (the Gemma+Gemini focus drops all Qwen). "
                "Kept as a tombstone entry (available=False, litellm_alias=None) "
                "so old callers get None instead of an unknown-key error."
            ),
            capabilities=(),
        ),
        "qwen-image": ModelRegistryEntry(
            key="qwen-image",
            family="image_gen",
            role="legacy_bilingual",
            display_name="Qwen-Image (InvokeAI) — REMOVED 2026-08-30",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="Qwen/Qwen-Image",
            backend="invokeai",
            available=False,  # REMOVED
            litellm_alias=None,
            profile="both",
            env_var=None,
            notes="Removed 2026-08-30; tombstone entry.",
            capabilities=(),
        ),
        "sdxl": ModelRegistryEntry(
            key="sdxl",
            family="image_gen",
            role="legacy",
            display_name="SDXL (InvokeAI) — REMOVED 2026-08-30",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="stabilityai/stable-diffusion-xl-base-1.0",
            backend="invokeai",
            available=False,  # REMOVED
            litellm_alias=None,
            profile="both",
            env_var=None,
            notes="Removed 2026-08-30; the speed tier is z-image-turbo now.",
            capabilities=(),
        ),
    }


# ---------------------------------------------------------------------------
# Family 5 — embedder (the canonical text-embedding backends).
#
# Added in the 2026-08-31-fix-critical-import-bugs-v1 change (Phase 0):
# lifted from the deleted ``gemini_hackathon/models/__init__.py``. Only
# ``bge-m3`` is routable today; ``gemini-embedding-2-preview`` lives in
# the ``text_llm`` family because LiteLLM surfaces it through the chat
# router with an ``embed`` role.
# ---------------------------------------------------------------------------


def _embedder_entries() -> dict[str, ModelRegistryEntry]:
    """The embedder family — the canonical text-embedding backends."""
    return {
        "bge-m3": ModelRegistryEntry(
            key="bge-m3",
            family="embedder",
            role="default",
            display_name="BAAI/bge-m3 (multilingual, 1024-dim)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="BAAI/bge-m3",
            backend="local",
            available=True,
            litellm_alias="openai/bge-m3",
            profile="both",
            env_var=None,
            notes=(
                "Canonical multilingual embedder for the BIEP substrate. "
                "1024-dim vectors; supports EN / GA / CY / GD. Used by every "
                "CocoIndex flow in ``cocoindex_flows/`` + the LanceDB hybrid "
                "search in ``knowledge_graph/hybrid_search.py``."
            ),
            languages=("en", "ga", "cy", "gd"),
            capabilities=("embed", "multilingual", "long_context"),
        ),
    }


# ---------------------------------------------------------------------------
# Family 6 — rerank (cross-encoder rerankers).
# ---------------------------------------------------------------------------


def _rerank_entries() -> dict[str, ModelRegistryEntry]:
    """The rerank family — the cross-encoder rerankers."""
    return {
        "bge-reranker-v2-m3": ModelRegistryEntry(
            key="bge-reranker-v2-m3",
            family="rerank",
            role="default",
            display_name="BAAI/bge-reranker-v2-m3",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="BAAI/bge-reranker-v2-m3",
            backend="local",
            available=True,
            litellm_alias=None,
            profile="both",
            env_var=None,
            notes=(
                "Cross-encoder reranker for CocoIndex hybrid search. Pair-scores "
                "(query, candidate) pairs for the second-stage retrieval pipeline."
            ),
            capabilities=("rerank", "cross_encoder"),
        ),
    }


# ---------------------------------------------------------------------------
# Family 7 — voice (TTS models via Unsloth Studio).
# ---------------------------------------------------------------------------


def _voice_entries() -> dict[str, ModelRegistryEntry]:
    """The voice family — TTS models served from Unsloth Studio."""
    return {
        "orpheus-3b": ModelRegistryEntry(
            key="orpheus-3b",
            family="voice",
            role="tts",
            display_name="Orpheus 3B (Unsloth Studio TTS)",
            unsloth_id="unsloth/orpheus-3b-0.1-ft-GGUF",
            mlx_id=None,
            upstream_id="canopyai/Orpheus-3b-0.1-ft",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/orpheus-3b",
            profile="both",
            env_var="UNSLOTH_BASE_URL",
            notes="TTS for the Irish / English / Celtic asset narration.",
            capabilities=("tts", "multilingual"),
            languages=("en", "ga", "cy", "gd"),
        ),
        "sesame-csm-1b": ModelRegistryEntry(
            key="sesame-csm-1b",
            family="voice",
            role="tts_conversational",
            display_name="Sesame CSM 1B (Unsloth Studio)",
            unsloth_id="unsloth/sesame-csm-1b-GGUF",
            mlx_id=None,
            upstream_id="sesame/csm-1b",
            backend="unsloth_studio",
            available=True,
            litellm_alias="openai/unsloth/sesame-csm-1b",
            profile="both",
            env_var="UNSLOTH_BASE_URL",
            notes="Conversational TTS for the agent chat surface.",
            capabilities=("tts", "conversational"),
        ),
    }


# ---------------------------------------------------------------------------
# Family 8 — translation (multimodal translation models).
# ---------------------------------------------------------------------------


def _translation_entries() -> dict[str, ModelRegistryEntry]:
    """The translation family — multimodal translation backends."""
    return {
        "minicpm-o-4_5": ModelRegistryEntry(
            key="minicpm-o-4_5",
            family="translation",
            role="multimodal",
            display_name="MiniCPM-o 4.5 (multimodal translation)",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="openbmb/MiniCPM-o-4_5",
            backend="llama_swap",
            available=True,
            litellm_alias=None,
            profile="both",
            env_var="LLAMA_SWAP_BASE_URL",
            notes=(
                "Multimodal translation. Registry entry only — Phase-11 "
                "tie-in for the bilingual LC/JC certificate pipeline."
            ),
            capabilities=("translation", "multimodal", "bilingual"),
            languages=("en", "ga"),
        ),
    }


# ---------------------------------------------------------------------------
# Stranded entries from the deleted ``gemini_hackathon/models/__init__.py``.
#
# These were registered with ``profile="dev"`` only — they are tombstones
# (available=False) under the canonical hackathon profile. They exist so
# old callers that hardcoded ``minimax-m3`` / ``qwen3.8-27b`` etc. get
# back the right ``ModelRegistryEntry`` (with ``available=False``) instead
# of an unknown-key error from ``model_for()``.
# ---------------------------------------------------------------------------


def _text_llm_dev_tombstones() -> dict[str, ModelRegistryEntry]:
    """Dev-profile text_llm tombstones — NOT exposed in the hackathon profile."""
    return {
        "minimax-m3": ModelRegistryEntry(
            key="minimax-m3",
            family="text_llm",
            role="dev_primary",
            display_name="minimax M3 (dev profile primary) — TOMBSTONE",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="minimax-m3",
            backend="minimax",
            available=False,
            litellm_alias="minimax-m3",
            profile="dev",
            env_var="MINIMAX_BASE_URL",
            notes=(
                "Dev-profile Tier 1 tombstone. Lifted from the deleted "
                "gemini_hackathon/models/__init__.py; lives here so old "
                "callers that hardcoded minimax-m3 get a registry hit "
                "(with available=False) instead of an unknown-key error. "
                "NOT exposed in the public hackathon profile roster."
            ),
            capabilities=("chat", "function_calling"),
        ),
        "qwen3.8-27b": ModelRegistryEntry(
            key="qwen3.8-27b",
            family="text_llm",
            role="dev_strong",
            display_name="Qwen 3.8 27B (Unsloth Studio) — TOMBSTONE",
            unsloth_id="unsloth/qwen3.8-27b-it-GGUF",
            mlx_id=None,
            upstream_id="Qwen/Qwen3-8-27B",
            backend="unsloth_studio",
            available=False,
            litellm_alias="openai/unsloth/qwen3.8-27b",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes="Dev-profile tombstone; dev-only Qwen flagship for harness comparisons.",
            capabilities=("chat",),
        ),
        "deepseek-v4-flash": ModelRegistryEntry(
            key="deepseek-v4-flash",
            family="text_llm",
            role="dev_fast",
            display_name="DeepSeek V4 Flash (Unsloth Studio) — TOMBSTONE",
            unsloth_id="unsloth/deepseek-v4-flash-GGUF",
            mlx_id=None,
            upstream_id="deepseek-ai/DeepSeek-V4-Flash",
            backend="unsloth_studio",
            available=False,
            litellm_alias="openai/unsloth/deepseek-v4-flash",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes="Dev-profile tombstone; dev-only fast tier for harness comparisons.",
            capabilities=("chat",),
        ),
        "kimi-k2.6": ModelRegistryEntry(
            key="kimi-k2.6",
            family="text_llm",
            role="dev_alt",
            display_name="Kimi K2.6 (Unsloth Studio) — TOMBSTONE",
            unsloth_id="unsloth/kimi-k2.6-GGUF",
            mlx_id=None,
            upstream_id="moonshotai/Kimi-K2.6",
            backend="unsloth_studio",
            available=False,
            litellm_alias="openai/unsloth/kimi-k2.6",
            profile="dev",
            env_var="UNSLOTH_BASE_URL",
            notes="Dev-profile tombstone; dev-only long-context comparison.",
            capabilities=("chat", "long_context"),
        ),
    }


def _ocr_vision_dev_tombstones() -> dict[str, ModelRegistryEntry]:
    """Dev-profile ocr_vision tombstones — qwen3-vl-8b was the prior OCR primary."""
    return {
        # qwen3-vl-8b was the OCR workhorse pre-2026-08-30; replaced by
        # gemma-4-26b-a4b-vision in the Gemma+Gemini refocus. Marked as a
        # tombstone (available=False) under the hackathon profile so it
        # no longer leaks into the public roster, but the entry still
        # exists so old callers (tests, cocoindex flows) get a registry
        # hit with available=False instead of an unknown-key error.
        "qwen3-vl-8b": ModelRegistryEntry(
            key="qwen3-vl-8b",
            family="ocr_vision",
            role="default",
            display_name="Qwen 3-VL 8B (llama-swap, OCR workhorse) — TOMBSTONE",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="Qwen/Qwen3-VL-8B-Instruct",
            backend="llama_swap",
            available=False,
            litellm_alias="openai/qwen3-vl-8b",
            profile="hackathon",
            env_var="LLAMA_SWAP_BASE_URL",
            notes=(
                "Pre-2026-08-30 OCR primary. Replaced by "
                "gemma-4-26b-a4b-vision in the Gemma+Gemini refocus. "
                "Kept as a tombstone (available=False) so the entry still "
                "exists for old callers."
            ),
            capabilities=("ocr", "figure_caption", "multilingual"),
        ),
        "qwen3-vl-4b": ModelRegistryEntry(
            key="qwen3-vl-4b",
            family="ocr_vision",
            role="vision_fast",
            display_name="Qwen 3-VL 4B (llama-swap) — TOMBSTONE",
            unsloth_id=None,
            mlx_id=None,
            upstream_id="Qwen/Qwen3-VL-4B-Instruct",
            backend="llama_swap",
            available=False,
            litellm_alias="openai/qwen3-vl-4b",
            profile="dev",
            env_var="LLAMA_SWAP_BASE_URL",
            notes="Dev-profile tombstone; dev-only fast vision tier for the comparison harness.",
            capabilities=("ocr", "figure_caption"),
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
            _learning_graph_entries(),
            _embedder_entries(),
            _rerank_entries(),
            _voice_entries(),
            _translation_entries(),
            # Stranded entries from the deleted gemini_hackathon/models/__init__.py.
            # These are tombstones (available=False) for the hackathon profile;
            # they keep the registry hit-count stable for old callers.
            _text_llm_dev_tombstones(),
            _ocr_vision_dev_tombstones(),
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
        logger.warning("Unknown MODEL_PROFILE %r; falling back to %r", raw, DEFAULT_PROFILE)
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
    return MODEL_REGISTRY.filter(family, role=role, available=available, profile=profile)


__all__ = [
    "DEFAULT_PROFILE",
    "MODEL_REGISTRY",
    "PROFILES",
    "Backend",
    "ModelFamily",
    "ModelPolicyError",
    "ModelProfile",
    "ModelRegistry",
    "ModelRegistryEntry",
    "ModelRole",
    "PublicModelEntry",
    "active_profile",
    "filter_models",
    "model_for",
    "model_key_for",
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
    # Tier 1 (Gemini API — Vertex / AI Studio)
    ("text_llm", "default"): 1,
    ("text_llm", "aistudio"): 1,
    ("text_llm", "lite"): 1,
    ("text_llm", "pro"): 1,
    ("text_llm", "alt"): 1,
    ("text_llm", "embedder"): 1,
    # Tier 2 (Unsloth Studio — Gemma 4 + Gemma 3/2 benchmarks + T5Gemma-2)
    ("text_llm", "fallback"): 2,
    ("text_llm", "fallback_light"): 2,
    ("text_llm", "local_fallback"): 2,
    ("text_llm", "local_fallback_old"): 2,
    ("text_llm", "dev_encoder_decoder"): 2,
    # Tier 2/3 (llama-swap — Gemma-only vision + text)
    ("ocr_vision", "default"): 2,
    ("ocr_vision", "vision_medium"): 2,
    ("ocr_vision", "vision_light"): 2,
    ("ocr_vision", "vision_prior_gen"): 3,
    ("ocr_vision", "vision_mobile"): 2,
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
            raise ModelPolicyError(f"Dev-only model {entry.key!r} reached the public roster.")
        roster.append(
            PublicModelEntry(
                key=entry.key,
                family=entry.family,
                role=entry.role,
                display_name=entry.display_name,
                backend=entry.backend,
                upstream_id=entry.upstream_id,
                litellm_alias=entry.litellm_alias,
                tier=_PUBLIC_TIER_INDEX.get((entry.family, entry.role)),
                notes=entry.notes,
            )
        )
    roster.sort(key=lambda e: (e.tier is None, e.tier or 0, e.key))
    return tuple(roster)


def public_tier_table() -> tuple[PublicModelEntry, ...]:
    """Tiered text_llm entries in tier order — for the docs table."""
    return tuple(e for e in public_model_roster(family="text_llm") if e.tier is not None)
