"""gemini_hackathon.call_llm — the dual-profile LiteLLM router.

Every LLM call in this codebase MUST go through :func:`call_llm`, which
enforces a tier policy selected by the ``MODEL_PROFILE`` environment variable.

``MODEL_PROFILE=hackathon`` (the default, and the only profile that docs, the
UI or the submission ever reference):

===== ==================================== ================================
Tier  Model                                Backend
===== ==================================== ================================
1     ``gemini-3.5-flash``                 Vertex AI (default) or AI Studio,
                                           selected by ``GEMINI_BACKEND``
2     ``unsloth/gemma-4-26B-A4B-it-GGUF``  Unsloth Studio (host process,
                                           ``UNSLOTH_BASE_URL``)
===== ==================================== ================================

``MODEL_PROFILE=dev`` keeps tiers 1 and 2 and adds ``minimax-m3`` plus the
wider Unsloth Studio text set for comparison work.

Profile containment
-------------------
It must be impossible for a dev-only model to reach a user-facing surface.
:func:`public_model_roster` is the **only** function docs and the UI may call,
and it reads the ``hackathon`` profile unconditionally — passing
``MODEL_PROFILE=dev`` does not change its output.

Excluded models (hard rejection, any profile)
---------------------------------------------
* Cloudflare Workers AI — anything containing ``@cf/``
* ``qwen3-coder-*`` — any model whose name starts with that prefix

Secrets
-------
Nothing in this module logs an environment *value* unless its key is on the
:data:`SAFE_ENV_KEYS` allow-list. Secret-bearing variables are reported as
presence booleans only. This is deliberately an allow-list: a deny-list regex
in this project previously matched ``KEY`` but not ``TOKEN`` and leaked a
credential. See :func:`safe_env_snapshot`.

Model strings are resolved through :mod:`gemini_hackathon.model_registry`;
adding a model is a registry change, not a router change.
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import structlog

from .model_registry import (
    MODEL_REGISTRY,
    ModelFamily,
    ModelProfile,
    ModelRegistryEntry,
    active_profile,
    model_for,
)
from .model_registry import (
    PublicModelEntry as _PublicModelEntry,
)

if TYPE_CHECKING:
    from litellm import Router

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Excluded-model patterns — these cannot be routed, ever.
# ---------------------------------------------------------------------------

_CF_PREFIX: str = "@cf/"
_QWEN_CODER_PREFIX: str = "qwen3-coder-"
_EXCLUDED_HELP: str = (
    "is explicitly excluded by the gemini_hackathon model policy. See docs/MODEL_POLICY.md"
)


class ModelExcludedError(ValueError):
    """Raised when a caller requests a model that is excluded by policy."""


class ModelPolicyError(RuntimeError):
    """Raised when a profile-containment invariant is violated.

    In practice this means a dev-only entry reached a public surface, which
    is a bug in the registry rather than a user error.
    """


def _assert_model_allowed(model: str) -> None:
    """Reject any model string that matches the exclusion patterns."""
    lowered = model.lower()
    if _CF_PREFIX in lowered:
        raise ModelExcludedError(f"Model {model} {_EXCLUDED_HELP}")
    if lowered.startswith(_QWEN_CODER_PREFIX) or f"/{_QWEN_CODER_PREFIX}" in lowered:
        raise ModelExcludedError(f"Model {model} {_EXCLUDED_HELP}")


# ---------------------------------------------------------------------------
# Secrets hygiene — ALLOW-LIST, never a deny-list.
# ---------------------------------------------------------------------------

SAFE_ENV_KEYS: frozenset[str] = frozenset(
    {
        "APP_ENV",
        "COMFYUI_BASE_URL",
        "GEMINI_BACKEND",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_CLOUD_PROJECT",
        "INVOKEAI_BASE_URL",
        "LLAMA_SWAP_BASE_URL",
        "LOG_LEVEL",
        "MINIMAX_BASE_URL",
        "MODEL_PROFILE",
        "UNSLOTH_BASE_URL",
    }
)
"""Environment variables whose **values** may be logged.

Every entry here is a non-secret: a profile name, a backend selector, a
project id, or a service URL. Anything not on this list is omitted from
diagnostics entirely. Adding a key here is a security decision — do not add
anything that could carry a credential.
"""

SECRET_ENV_KEYS: tuple[str, ...] = (
    "GEMINI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "LANGFUSE_SECRET_KEY",
    "MINIMAX_API_KEY",
    "UNSLOTH_API_KEY",
)
"""Secret-bearing variables. Reported as ``<KEY>_set: bool`` — never by value.

The Unsloth key has the form ``sk-unsloth-...`` and lives at Infisical
``dev-baile/unsloth/api_key``. It is never written to a file in this repo.
"""


def _scrub_url(value: str) -> str:
    """Strip any ``user:password@`` userinfo from a URL before logging.

    A base URL is on the allow-list because it is normally just a host and
    port. It is still possible to embed credentials in one
    (``https://user:pass@host/v1``), so the userinfo segment is removed.
    """
    if "://" not in value:
        return value
    scheme, _, rest = value.partition("://")
    if "@" not in rest:
        return value
    _userinfo, _, hostpart = rest.rpartition("@")
    return f"{scheme}://***@{hostpart}"


def safe_env_snapshot() -> dict[str, Any]:
    """Return a diagnostics-safe view of the model-policy environment.

    Only keys on the :data:`SAFE_ENV_KEYS` allow-list contribute a value;
    URLs have their userinfo scrubbed. Secret-bearing variables contribute a
    boolean ``<KEY>_set`` and nothing else. Variables that are unset are
    omitted rather than reported as empty.

    This is the only sanctioned way to put environment state into a log line
    or an error message in this module.
    """
    snapshot: dict[str, Any] = {}
    for key in sorted(SAFE_ENV_KEYS):
        raw = os.environ.get(key)
        if raw is None or not raw.strip():
            continue
        snapshot[key] = _scrub_url(raw.strip())
    for key in SECRET_ENV_KEYS:
        snapshot[f"{key}_set"] = bool(os.environ.get(key, "").strip())
    return snapshot


# ---------------------------------------------------------------------------
# Tier definitions.
# ---------------------------------------------------------------------------

BACKOFF_BASE_SECONDS: float = 1.0
TIER_TIMEOUT_SECONDS: float = 30.0

PUBLIC_PROFILE: ModelProfile = "hackathon"
"""The profile every user-facing surface reads, regardless of MODEL_PROFILE."""

HACKATHON_TIERS: tuple[tuple[ModelFamily, str], ...] = (
    # Per the 2026-08-30 Gemma+Gemini refocus:
    ("text_llm", "default"),  # Tier 1: gemini-3.5-flash via Vertex AI
    ("text_llm", "aistudio"),  # Tier 1: gemini-3.5-flash via AI Studio (auto-fallback)
    ("text_llm", "fallback"),  # Tier 2: gemma-4-26b-a4b via Unsloth Studio
    ("text_llm", "fallback_light"),  # Tier 2 light: gemma-4-e4b via Unsloth Studio
    ("text_llm", "local_fallback"),  # Tier 2 benchmark: gemma-3-27b-it via Unsloth Studio
    ("text_llm", "local_fallback_old"),  # Tier 2 baseline: gemma-2-9b via Unsloth Studio
)

DEV_TIERS: tuple[tuple[ModelFamily, str], ...] = (
    # dev profile = same chain + the lite tier for the comparison harness
    ("text_llm", "default"),
    ("text_llm", "aistudio"),
    ("text_llm", "lite"),
    ("text_llm", "fallback"),
    ("text_llm", "fallback_light"),
    ("text_llm", "local_fallback"),
    ("text_llm", "local_fallback_old"),
    ("text_llm", "dev_encoder_decoder"),  # t5gemma-2-4b
)

TIER_RETRY_BUDGETS: dict[str, int] = {
    "default": 2,
    "aistudio": 2,
    "lite": 2,
    "fallback": 1,
    "fallback_light": 1,
    "local_fallback": 1,
    "local_fallback_old": 1,
    "dev_encoder_decoder": 1,
}

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
}


def tiers_for_profile(profile: ModelProfile) -> tuple[tuple[ModelFamily, str], ...]:
    """The ordered tier chain for ``profile``."""
    return DEV_TIERS if profile == "dev" else HACKATHON_TIERS


# ---------------------------------------------------------------------------
# Gemini backend selection.
# ---------------------------------------------------------------------------

GeminiBackend = Literal["vertex", "aistudio"]

DEFAULT_GEMINI_BACKEND: GeminiBackend = "vertex"

_GEMINI_ROLE_BY_BACKEND: dict[GeminiBackend, str] = {
    "vertex": "default",
    "aistudio": "aistudio",
}


def _vertex_credentials_present() -> bool:
    """Whether Vertex AI is addressable.

    ``GOOGLE_CLOUD_PROJECT`` is the discriminator: a Vertex endpoint cannot be
    constructed without a project id, whereas Application Default Credentials
    may legitimately come from a metadata server, gcloud login, or a service
    account file, none of which are reliably visible as env vars.
    """
    return bool(os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip())


def _aistudio_credentials_present() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def resolve_gemini_backend() -> tuple[GeminiBackend, str]:
    """Decide which Gemini backend Tier 1 should use.

    Rules:
        1. ``GEMINI_BACKEND`` selects the backend; it defaults to ``vertex``.
        2. An unrecognised value falls back to ``vertex`` with a warning.
        3. If ``vertex`` is selected but no Vertex credentials are present
           while ``GEMINI_API_KEY`` is, switch to ``aistudio`` and log why.
        4. If neither is configured, stay on ``vertex`` so the resulting
           failure names the backend that was actually asked for rather than
           masquerading as an AI Studio auth error.

    Returns:
        A ``(backend, reason)`` pair. ``reason`` is a stable snake_case token
        suitable for logging and for assertions in tests.
    """
    raw = os.environ.get("GEMINI_BACKEND", DEFAULT_GEMINI_BACKEND).strip().lower()

    if raw not in _GEMINI_ROLE_BY_BACKEND:
        logger.warning(
            "llm.unknown_gemini_backend",
            llm_requested_backend=raw,
            llm_selected_backend=DEFAULT_GEMINI_BACKEND,
            **safe_env_snapshot(),
        )
        raw = DEFAULT_GEMINI_BACKEND

    if raw == "aistudio":
        return "aistudio", "explicit_aistudio"

    if _vertex_credentials_present():
        return "vertex", "vertex_credentials_present"

    if _aistudio_credentials_present():
        logger.info(
            "llm.gemini_backend_fallback",
            llm_requested_backend="vertex",
            llm_selected_backend="aistudio",
            llm_fallback_reason=(
                "GOOGLE_CLOUD_PROJECT is unset so Vertex AI cannot be "
                "addressed; GEMINI_API_KEY is set, so Tier 1 is served from "
                "AI Studio instead."
            ),
            **safe_env_snapshot(),
        )
        return "aistudio", "vertex_credentials_missing_fell_back_to_aistudio"

    logger.warning(
        "llm.gemini_backend_unconfigured",
        llm_selected_backend="vertex",
        llm_reason=(
            "Neither GOOGLE_CLOUD_PROJECT nor GEMINI_API_KEY is set; Tier 1 "
            "will fail and the router will fall through to Tier 2."
        ),
        **safe_env_snapshot(),
    )
    return "vertex", "no_gemini_credentials"


def gemini_tier1_role() -> str:
    """The registry role Tier 1 resolves to under the current environment."""
    backend, _reason = resolve_gemini_backend()
    return _GEMINI_ROLE_BY_BACKEND[backend]


def _resolve_tier_entry(
    family: ModelFamily,
    role: str,
    profile: ModelProfile,
) -> ModelRegistryEntry | None:
    """Resolve a tier spec, applying the Gemini backend switch to Tier 1.

    The (text_llm, default) -> (text_llm, aistudio) swap is a hackathon-only
    concern: the dev profile already registers its own Tier 1 entry
    (``gemini-3.5-flash-dev``) with ``role="default"`` and ``backend="aistudio"``,
    so no swap is needed there.
    """
    if (family, role) == ("text_llm", "default") and profile == "hackathon":
        role = gemini_tier1_role()
    return model_for(family, role, profile=profile)


# ---------------------------------------------------------------------------
# Public surface — the ONLY roster docs and the UI may read.
# ---------------------------------------------------------------------------
#
# NOTE: _PublicModelEntry is the canonical dataclass defined in
# gemini_hackathon.model_registry (imported above). The legacy duplicate
# definition that used to live here was removed in the
# 2026-08-31-fix-critical-import-bugs-v1 change so there is exactly one
# _PublicModelEntry in the codebase.


def public_model_roster(
    *,
    family: ModelFamily | None = None,
) -> tuple[_PublicModelEntry, ...]:
    """The public model roster — always the ``hackathon`` profile.

    This function deliberately ignores ``MODEL_PROFILE``. Running the process
    with ``MODEL_PROFILE=dev`` changes what :func:`call_llm` routes to, but it
    does not change one byte of this output. Docs generators, the UI, the CLI
    and the submission materials must read models from here and nowhere else.

    Args:
        family: Optional family filter.

    Returns:
        A tuple of :class:`_PublicModelEntry`, ordered by tier (untiered
        entries last, then by key).

    Raises:
        ModelPolicyError: If a dev-only entry somehow reached this list. That
            is a registry bug, not a caller error.
    """
    entries = MODEL_REGISTRY.filter(family, profile=PUBLIC_PROFILE, available=True)

    roster: list[_PublicModelEntry] = []
    for entry in entries:
        # `filter(profile="hackathon")` already excludes dev-only entries.
        # This second check is the belt to that braces: profile containment is
        # the one invariant in this module that must not fail quietly.
        if entry.profile == "dev":
            raise ModelPolicyError(
                f"Dev-only model {entry.key!r} reached the public roster. "
                "public_model_roster() must never expose MODEL_PROFILE=dev "
                "entries; fix the registry entry's `profile` field."
            )
        roster.append(
            _PublicModelEntry(
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


def public_tier_table() -> tuple[_PublicModelEntry, ...]:
    """Just the tiered text_llm entries, in tier order — for the docs table.

    Derived from :func:`public_model_roster`, so it inherits the same
    containment guarantee.
    """
    return tuple(e for e in public_model_roster(family="text_llm") if e.tier is not None)


# ---------------------------------------------------------------------------
# LiteLLM router construction.
# ---------------------------------------------------------------------------

_ROUTER: Router | None = None


def build_model_list(
    profile: ModelProfile | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Build the LiteLLM ``(model_list, fallbacks)`` pair for ``profile``.

    Split out from :func:`_build_router` so the routing configuration can be
    asserted in tests without importing litellm or opening a socket.
    """
    profile = profile or active_profile()
    model_list: list[dict[str, Any]] = []
    fallback_list: list[dict[str, str]] = []

    for i, (family, role) in enumerate(tiers_for_profile(profile), start=1):
        entry = _resolve_tier_entry(family, role, profile)
        if entry is None or entry.litellm_alias is None:
            logger.warning(
                "llm.tier_skipped_no_registry_entry",
                llm_tier=i,
                llm_family=family,
                llm_role=role,
                model_profile=profile,
            )
            continue
        _assert_model_allowed(entry.litellm_alias)
        model_list.append(
            {
                "model_name": f"tier-{i}",
                "litellm_params": _build_litellm_params(entry),
            }
        )
        fallback_list.append({"model": f"tier-{i}"})

    return model_list, fallback_list


def _build_router() -> Router:
    """Build (and cache) the LiteLLM router for the active profile."""
    global _ROUTER
    if _ROUTER is not None:
        return _ROUTER

    try:
        from litellm import Router  # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "litellm is required by gemini_hackathon.call_llm. Install with `uv add litellm`."
        ) from e

    model_list, fallback_list = build_model_list()
    _ROUTER = Router(
        model_list=model_list,
        fallbacks=fallback_list,
        num_retries=1,
        timeout=TIER_TIMEOUT_SECONDS,
        set_verbose=False,
    )
    return _ROUTER


def _require_key(env_var: str, *, backend: str) -> str:
    """Read a credential from the environment with no literal default.

    Returns an empty string when unset — the downstream provider then fails
    with its own auth error. A placeholder default is deliberately *not*
    supplied: a fake key produces a confusing 401 from a real endpoint, and
    committing one to source is how credentials end up in git history.
    """
    value = os.environ.get(env_var, "").strip()
    if not value:
        logger.warning(
            "llm.credential_missing",
            llm_backend=backend,
            llm_env_var=env_var,  # the NAME only; never the value
            **safe_env_snapshot(),
        )
    return value


def _build_litellm_params(entry: ModelRegistryEntry) -> dict[str, Any]:
    """Translate a registry entry into a LiteLLM ``litellm_params`` block."""
    alias = entry.litellm_alias or ""
    params: dict[str, Any] = {
        "model": alias,
        "timeout": TIER_TIMEOUT_SECONDS,
    }

    if entry.backend == "vertex":
        # Vertex authenticates via Application Default Credentials; there is
        # no API key to pass.
        params["vertex_project"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
        params["vertex_location"] = (
            os.environ.get("GOOGLE_CLOUD_LOCATION", "").strip() or "us-central1"
        )
    elif entry.backend == "aistudio":
        params["api_key"] = _require_key("GEMINI_API_KEY", backend="aistudio")
    elif entry.backend == "unsloth_studio":
        params["api_base"] = (
            os.environ.get("UNSLOTH_BASE_URL", "").strip() or "http://127.0.0.1:8888/v1"
        )
        params["api_key"] = _require_key("UNSLOTH_API_KEY", backend="unsloth_studio")
    elif entry.backend == "llama_swap":
        params["api_base"] = (
            os.environ.get("LLAMA_SWAP_BASE_URL", "").strip() or "http://127.0.0.1:8080/v1"
        )
        params["api_key"] = os.environ.get("LLAMASWAP_API_KEY", "").strip() or "not-required"
    elif entry.backend == "minimax":
        params["api_base"] = (
            os.environ.get("MINIMAX_BASE_URL", "").strip() or "https://api.minimax.io/v1"
        )
        params["api_key"] = _require_key("MINIMAX_API_KEY", backend="minimax")
    elif entry.backend == "agent_garden":
        # Google Cloud Agent Garden — Vertex AI Model Garden publisher
        # models (Gemma 3, Llama 3, etc.). Auth via Application Default
        # Credentials; no API key. The model alias is already
        # ``vertex_ai/<publisher>/<model>`` in the registry.
        params["vertex_project"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
        params["vertex_location"] = (
            os.environ.get("GOOGLE_CLOUD_LOCATION", "").strip() or "us-central1"
        )
    elif entry.backend == "invokeai":
        params["api_base"] = (
            os.environ.get("INVOKEAI_BASE_URL", "").strip() or "http://127.0.0.1:9090/v1"
        )
    elif entry.backend == "comfyui":
        params["api_base"] = (
            os.environ.get("COMFYUI_BASE_URL", "").strip() or "http://127.0.0.1:8188"
        )
    # `local` entries have no HTTP surface; the caller supplies the adapter.

    return params


def reset_router() -> None:
    """Reset the cached router. Required after a profile or backend swap."""
    global _ROUTER
    _ROUTER = None


# ---------------------------------------------------------------------------
# Exception + data types.
# ---------------------------------------------------------------------------


class LLMCallError(RuntimeError):
    """Raised when every tier has failed for a :func:`call_llm` invocation."""

    def __init__(self, message: str, *, attempts: Sequence[TierAttempt]) -> None:
        super().__init__(message)
        self.attempts: list[TierAttempt] = list(attempts)
        self.last_error: str = attempts[-1].error if attempts else ""


class TierTimeoutError(RuntimeError):
    """Raised internally when a single tier exceeds its wall-clock budget."""


@dataclass(frozen=True)
class TierAttempt:
    """One attempt against a single tier."""

    tier: int
    family: ModelFamily
    role: str
    model: str
    backend: str
    latency_ms: int
    error: str = ""
    succeeded: bool = False


@dataclass(frozen=True)
class LLMResponse:
    """The result of a successful :func:`call_llm` invocation."""

    content: str
    model: str
    backend: str
    tier: int
    family: ModelFamily
    role: str
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    attempts: list[TierAttempt] = field(default_factory=list)


Message = dict[str, str]
"""OpenAI-compatible message shape: ``{"role": ..., "content": ...}``."""


# ---------------------------------------------------------------------------
# The main entrypoint.
# ---------------------------------------------------------------------------


def call_llm(
    messages: Sequence[Message],
    *,
    profile: ModelProfile | None = None,
    family: ModelFamily | None = None,
    role: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    metadata: dict[str, Any] | None = None,
) -> LLMResponse:
    """Call the LLM through the dual-profile router.

    Behaviour:
        * ``profile`` defaults to ``$MODEL_PROFILE`` (or ``hackathon``).
        * When ``family`` and ``role`` are both given, that single entry is
          used and the tier walk is skipped — useful for the comparison
          harness.
        * Otherwise the router walks the active profile's tiers in order.

    Args:
        messages: OpenAI-compatible message list (non-empty).
        profile: Optional override for ``MODEL_PROFILE``.
        family: Optional single-family pin (must be passed with ``role``).
        role: Optional single-role pin (must be passed with ``family``).
        temperature: Sampling temperature. Default 0.2.
        max_tokens: Max completion tokens. Default 1024.
        metadata: Optional dict merged into every log event.

    Returns:
        An :class:`LLMResponse`.

    Raises:
        ValueError: If ``messages`` is empty, or a pinned ``(family, role)``
            does not resolve under the active profile.
        ModelExcludedError: If a resolved model matches the exclusion patterns.
        LLMCallError: If every tier failed.
    """
    if not messages:
        raise ValueError("call_llm() requires a non-empty `messages` list")

    resolved_profile = profile or active_profile()
    log_metadata: dict[str, Any] = dict(metadata or {})
    log_metadata["model_profile"] = resolved_profile

    # Pin mode: one call against one specific (family, role) entry.
    if family is not None and role is not None:
        entry = _resolve_tier_entry(family, role, resolved_profile)
        if entry is None or entry.litellm_alias is None:
            raise ValueError(
                f"No registry entry for ({family}, {role}) under profile={resolved_profile!r}"
            )
        _assert_model_allowed(entry.litellm_alias)
        return _attempt(
            entry=entry,
            tier_idx=1,
            role=entry.role,
            retry_budget=TIER_RETRY_BUDGETS.get(entry.role, 1),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            log_metadata=log_metadata,
        )

    tiers = tiers_for_profile(resolved_profile)
    attempts: list[TierAttempt] = []
    overall_start = time.monotonic()

    for tier_idx, (tier_family, tier_role) in enumerate(tiers, start=1):
        entry = _resolve_tier_entry(tier_family, tier_role, resolved_profile)
        if entry is None or entry.litellm_alias is None:
            continue
        _assert_model_allowed(entry.litellm_alias)
        try:
            return _attempt(
                entry=entry,
                tier_idx=tier_idx,
                role=entry.role,
                retry_budget=TIER_RETRY_BUDGETS.get(entry.role, 1),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                log_metadata=log_metadata,
                attempts_accumulator=attempts,
            )
        except LLMCallError as e:
            attempts.extend(a for a in e.attempts if a not in attempts)
            continue

    total_ms = int((time.monotonic() - overall_start) * 1000)
    logger.error(
        "llm.all_tiers_failed",
        llm_latency_ms=total_ms,
        llm_tiers_attempted=[f"{f}:{r}" for f, r in tiers],
        **log_metadata,
    )
    raise LLMCallError(
        "All tiers failed for call_llm(); see attempts[] for details.",
        attempts=attempts,
    )


def _attempt(
    *,
    entry: ModelRegistryEntry,
    tier_idx: int,
    role: str,
    retry_budget: int,
    messages: Sequence[Message],
    temperature: float,
    max_tokens: int,
    log_metadata: dict[str, Any],
    attempts_accumulator: list[TierAttempt] | None = None,
) -> LLMResponse:
    """Run one entry with retries + per-attempt logging."""
    router = _build_router()
    attempts = attempts_accumulator if attempts_accumulator is not None else []
    overall_start = time.monotonic()
    router_name = f"tier-{tier_idx}"

    for attempt_no in range(retry_budget):
        attempt_start = time.monotonic()
        try:
            response = router.completion(
                model=router_name,
                messages=list(messages),
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
            tokens_out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
            attempt_ms = int((time.monotonic() - attempt_start) * 1000)
            attempts.append(
                TierAttempt(
                    tier=tier_idx,
                    family=entry.family,
                    role=role,
                    model=entry.litellm_alias or entry.key,
                    backend=entry.backend,
                    latency_ms=attempt_ms,
                    succeeded=True,
                )
            )
            total_ms = int((time.monotonic() - overall_start) * 1000)
            _emit_invocation_log(
                tier=tier_idx,
                role=role,
                entry=entry,
                latency_ms=total_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                log_metadata=log_metadata,
            )
            return LLMResponse(
                content=content,
                model=entry.litellm_alias or entry.key,
                backend=entry.backend,
                tier=tier_idx,
                family=entry.family,
                role=role,
                latency_ms=total_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=estimate_cost_usd(entry.key, tokens_in, tokens_out),
                attempts=list(attempts),
            )
        except Exception as e:
            attempt_ms = int((time.monotonic() - attempt_start) * 1000)
            error_msg = f"{type(e).__name__}: {e}"
            attempts.append(
                TierAttempt(
                    tier=tier_idx,
                    family=entry.family,
                    role=role,
                    model=entry.litellm_alias or entry.key,
                    backend=entry.backend,
                    latency_ms=attempt_ms,
                    error=error_msg,
                    succeeded=False,
                )
            )
            logger.warning(
                "llm.invocation_failed",
                llm_tier=str(tier_idx),
                llm_model=entry.litellm_alias,
                llm_backend=entry.backend,
                llm_latency_ms=attempt_ms,
                llm_attempt=attempt_no + 1,
                llm_retry_budget=retry_budget,
                llm_error=error_msg,
                **log_metadata,
            )
            if attempt_no + 1 < retry_budget:
                time.sleep(BACKOFF_BASE_SECONDS * (2**attempt_no))
                continue
            break

    raise LLMCallError(
        f"Tier {tier_idx} ({entry.key}) exhausted its retry budget.",
        attempts=attempts,
    )


def _emit_invocation_log(
    *,
    tier: int,
    role: str,
    entry: ModelRegistryEntry,
    latency_ms: int,
    tokens_in: int,
    tokens_out: int,
    log_metadata: dict[str, Any],
) -> None:
    """Emit the canonical ``llm.invocation`` structlog event."""
    payload: dict[str, Any] = {
        "llm.tier": str(tier),
        "llm.role": role,
        "llm.model_key": entry.key,
        "llm.model_alias": entry.litellm_alias,
        "llm.backend": entry.backend,
        "llm.latency_ms": latency_ms,
        "llm.tokens_in": tokens_in,
        "llm.tokens_out": tokens_out,
    }
    if tier > 1:
        payload["llm.fallback_reason"] = f"tier-{tier - 1}_failed_or_timeout"
    payload.update(log_metadata)
    logger.info("llm.invocation", **payload)


def _active_profile() -> ModelProfile:
    """Back-compat alias for :func:`gemini_hackathon.model_registry.active_profile`."""
    return active_profile()


# ---------------------------------------------------------------------------
# Utility helpers.
# ---------------------------------------------------------------------------


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    """Best-effort USD cost estimate (placeholder per-1k pricing).

    Local models (Unsloth Studio, llama-swap) are free by definition; unknown
    models are reported as 0.0 rather than guessed at.
    """
    pricing: dict[str, tuple[float, float]] = {
        "gemini-3.5-flash": (0.000075, 0.0003),
        "gemini-3.5-flash-aistudio": (0.000075, 0.0003),
        "gemma-4-26b-a4b": (0.0, 0.0),  # local
        "minimax-m3": (0.0002, 0.0006),
    }
    in_rate, out_rate = pricing.get(model, (0.0, 0.0))
    return round((tokens_in / 1000.0) * in_rate + (tokens_out / 1000.0) * out_rate, 6)


def normalise_messages(messages: Sequence[Message]) -> list[Message]:
    """Validate + normalise an OpenAI-compatible message list."""
    out: list[Message] = []
    for msg in messages:
        if "role" not in msg or "content" not in msg:
            raise ValueError(f"Message must have `role` and `content` keys; got {msg!r}")
        if msg["role"] not in {"system", "user", "assistant"}:
            raise ValueError(f"Invalid message role: {msg['role']!r}")
        out.append({"role": msg["role"], "content": str(msg["content"])})
    return out


def parse_model_string(model: str) -> tuple[str | None, str]:
    """Split a LiteLLM model string into ``(provider, name)``."""
    if "/" in model:
        provider, _, name = model.partition("/")
        return provider, name
    return None, model


__all__ = [
    "BACKOFF_BASE_SECONDS",
    "DEFAULT_GEMINI_BACKEND",
    "DEV_TIERS",
    "HACKATHON_TIERS",
    "PUBLIC_PROFILE",
    "SAFE_ENV_KEYS",
    "SECRET_ENV_KEYS",
    "TIER_RETRY_BUDGETS",
    "TIER_TIMEOUT_SECONDS",
    "GeminiBackend",
    "LLMCallError",
    "LLMResponse",
    "Message",
    "ModelExcludedError",
    "ModelPolicyError",
    "TierAttempt",
    "TierTimeoutError",
    "build_model_list",
    "call_llm",
    "estimate_cost_usd",
    "gemini_tier1_role",
    "normalise_messages",
    "parse_model_string",
    "public_model_roster",
    "public_tier_table",
    "reset_router",
    "resolve_gemini_backend",
    "safe_env_snapshot",
    "tiers_for_profile",
]
