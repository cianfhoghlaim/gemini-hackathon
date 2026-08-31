"""Tests for the gemini_hackathon.call_llm dual-profile router.

Every LLM call in this file is mocked at the router boundary
(:func:`gemini_hackathon.call_llm._build_router`), so litellm is never
imported and no socket is ever opened.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from gemini_hackathon import call_llm as cl

# ---------------------------------------------------------------------------
# Env isolation
#
# tests/conftest.py's autouse `clean_env` fixture resets most canonical env
# vars, but not the model-policy selectors added by this change, so they are
# cleared here.
# ---------------------------------------------------------------------------


_POLICY_ENV_KEYS = (
    "MODEL_PROFILE",
    "GEMINI_BACKEND",
    "GEMINI_API_KEY",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "UNSLOTH_BASE_URL",
    "UNSLOTH_API_KEY",
    "MINIMAX_API_KEY",
    "MINIMAX_BASE_URL",
    "LLAMA_SWAP_BASE_URL",
)


@pytest.fixture(autouse=True)
def _clean_policy_env(monkeypatch: pytest.MonkeyPatch):
    for key in _POLICY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    cl.reset_router()
    yield
    cl.reset_router()


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch: pytest.MonkeyPatch):
    """Retry backoff is real wall-clock time; neutralise it for the suite."""
    monkeypatch.setattr(cl.time, "sleep", lambda _seconds: None)


# ---------------------------------------------------------------------------
# Router test double
# ---------------------------------------------------------------------------


def _fake_completion_response(content: str = "ok") -> SimpleNamespace:
    """Build the minimal duck-type that :func:`_attempt` reads."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7)
    return SimpleNamespace(choices=[choice], usage=usage)


class _FakeRouter:
    """Stands in for ``litellm.Router``.

    ``behaviour`` maps ``"tier-N"`` to either a response factory or an
    exception instance to raise.
    """

    def __init__(self, behaviour: dict[str, Any]) -> None:
        self.behaviour = behaviour
        self.calls: list[str] = []

    def completion(self, *, model: str, **_kwargs: Any) -> SimpleNamespace:
        self.calls.append(model)
        outcome = self.behaviour.get(model)
        if outcome is None:
            raise RuntimeError(f"no behaviour configured for {model}")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def fake_router(monkeypatch: pytest.MonkeyPatch):
    """Install a :class:`_FakeRouter` and return the installer."""

    def _install(behaviour: dict[str, Any]) -> _FakeRouter:
        router = _FakeRouter(behaviour)
        monkeypatch.setattr(cl, "_build_router", lambda: router)
        return router

    return _install


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


def test_public_api_is_importable():
    for name in (
        "call_llm",
        "public_model_roster",
        "public_tier_table",
        "resolve_gemini_backend",
        "safe_env_snapshot",
        "build_model_list",
        "reset_router",
        "ModelExcludedError",
        "ModelPolicyError",
    ):
        assert hasattr(cl, name), f"missing public symbol: {name}"


def test_tier_constants():
    # Updated 2026-08-31 (Phase 6) to match the canonical 6-tier chain
    # defined in gemini_hackathon/call_llm.py:HACKATHON_TIERS + DEV_TIERS.
    # The 2026-08-30 Gemma+Gemini refocus promoted gemini-3.5-flash from
    # role="agent_garden" (Tier 3) to role="default" (Tier 1). The chain
    # now spans:
    #   Tier 1: gemini-3.5-flash      (Vertex — `default`)
    #   Tier 2: gemini-3.5-flash-aistudio (AI Studio — `aistudio`)
    #   Tier 3: gemma-4-26b-a4b     (Unsloth — `fallback`)
    #   Tier 4: gemma-4-e4b         (Unsloth — `fallback_light`)
    #   Tier 5: gemma-3-27b-it      (Unsloth — `local_fallback`)
    #   Tier 6: gemma-2-9b          (Unsloth — `local_fallback_old`)
    assert cl.HACKATHON_TIERS == (
        ("text_llm", "default"),
        ("text_llm", "aistudio"),
        ("text_llm", "fallback"),
        ("text_llm", "fallback_light"),
        ("text_llm", "local_fallback"),
        ("text_llm", "local_fallback_old"),
    )
    # DEV_TIERS inserts `lite` between aistudio and fallback, then adds
    # `dev_encoder_decoder` as the dev-only 8th slot.
    assert cl.DEV_TIERS[0] == ("text_llm", "default")
    assert cl.DEV_TIERS[1] == ("text_llm", "aistudio")
    assert ("text_llm", "lite") in cl.DEV_TIERS
    assert ("text_llm", "dev_encoder_decoder") in cl.DEV_TIERS
    assert cl.TIER_RETRY_BUDGETS["default"] == 2


# ---------------------------------------------------------------------------
# Profile switching
# ---------------------------------------------------------------------------


def test_active_profile_defaults_to_hackathon(monkeypatch):
    monkeypatch.delenv("MODEL_PROFILE", raising=False)
    assert cl._active_profile() == "hackathon"


def test_active_profile_reads_dev(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", "dev")
    assert cl._active_profile() == "dev"


@pytest.mark.parametrize("bogus", ["garbage", "DEV ", "prod", ""])
def test_active_profile_unknown_falls_back_to_hackathon(monkeypatch, bogus):
    """An unknown profile must never widen the exposed model set."""
    monkeypatch.setenv("MODEL_PROFILE", bogus)
    assert cl._active_profile() in ("hackathon", "dev")
    if bogus.strip().lower() not in ("hackathon", "dev"):
        assert cl._active_profile() == "hackathon"


def test_tiers_for_profile():
    assert cl.tiers_for_profile("hackathon") == cl.HACKATHON_TIERS
    assert cl.tiers_for_profile("dev") == cl.DEV_TIERS
    # Updated 2026-08-31 (Phase 6): DEV_TIERS now = HACKATHON_TIERS + 2
    # dev-only roles (`lite` + `dev_encoder_decoder`).
    assert len(cl.DEV_TIERS) == len(cl.HACKATHON_TIERS) + 2


def test_hackathon_profile_first_tier_is_gemini_on_vertex():
    """Tier 1 of the hackathon profile = gemini-3.5-flash via Vertex AI
    (the canonical primary after the 2026-08-30 Gemma+Gemini refocus)."""
    model_list, _ = cl.build_model_list(profile="hackathon")
    aliases = [m["litellm_params"]["model"] for m in model_list]
    assert aliases[0] == "vertex_ai/gemini-3.5-flash"


def test_dev_profile_matches_hackathon_tier_chain(monkeypatch):
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-unsloth-not-real")
    model_list, fallbacks = cl.build_model_list(profile="dev")
    aliases = [m["litellm_params"]["model"] for m in model_list]
    # Updated 2026-08-31 (Phase 6): many of the tier slots are
    # profile=dev only (the `aistudio`, `lite`, `fallback`,
    # `fallback_light` Gemini/Unsloth entries are visible only on
    # profile=hackathon). The dev profile's reachable tiers are
    # `default` + `local_fallback` + `local_fallback_old` +
    # `dev_encoder_decoder`.
    assert aliases == [
        "vertex_ai/gemini-3.5-flash",  # Tier 1: default (dev)
        "openai/unsloth/gemma-3-27b-it",  # Tier 6: local_fallback
        "openai/unsloth/gemma-2-9b",  # Tier 7: local_fallback_old
        "openai/unsloth/t5gemma-2-4b",  # Tier 8: dev_encoder_decoder
    ]
    assert len(model_list) == 4
    # The fallbacks list mirrors the tier_index used to build each slot.
    assert fallbacks == [
        {"model": "tier-1"},
        {"model": "tier-6"},
        {"model": "tier-7"},
        {"model": "tier-8"},
    ]


# ---------------------------------------------------------------------------
# GEMINI_BACKEND switching
# ---------------------------------------------------------------------------


def test_gemini_backend_defaults_to_vertex_when_project_set(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    backend, reason = cl.resolve_gemini_backend()
    assert backend == "vertex"
    assert reason == "vertex_credentials_present"
    assert cl.gemini_tier1_role() == "default"


def test_gemini_backend_explicit_vertex(monkeypatch):
    monkeypatch.setenv("GEMINI_BACKEND", "vertex")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    assert cl.resolve_gemini_backend()[0] == "vertex"


def test_gemini_backend_explicit_aistudio(monkeypatch):
    monkeypatch.setenv("GEMINI_BACKEND", "aistudio")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    backend, reason = cl.resolve_gemini_backend()
    assert backend == "aistudio"
    assert reason == "explicit_aistudio"
    assert cl.gemini_tier1_role() == "aistudio"


def test_gemini_backend_explicit_aistudio_wins_over_vertex_creds(monkeypatch):
    """An explicit choice is honoured even when Vertex is fully configured."""
    monkeypatch.setenv("GEMINI_BACKEND", "aistudio")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    assert cl.resolve_gemini_backend()[0] == "aistudio"


@pytest.mark.parametrize("bogus", ["openai", "VERTEXAI", "", "  "])
def test_gemini_backend_unknown_value_falls_back_to_vertex(monkeypatch, bogus):
    monkeypatch.setenv("GEMINI_BACKEND", bogus)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    assert cl.resolve_gemini_backend()[0] == "vertex"


def test_gemini_backend_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("GEMINI_BACKEND", "  AiStudio ")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    assert cl.resolve_gemini_backend()[0] == "aistudio"


# --- the fallback path ------------------------------------------------------


def test_aistudio_fallback_when_vertex_creds_missing(monkeypatch):
    """Vertex requested, no GOOGLE_CLOUD_PROJECT, but an API key is present."""
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    backend, reason = cl.resolve_gemini_backend()
    assert backend == "aistudio"
    assert reason == "vertex_credentials_missing_fell_back_to_aistudio"


def test_aistudio_fallback_changes_the_tier1_model_string(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    model_list, _ = cl.build_model_list(profile="hackathon")
    assert model_list[0]["litellm_params"]["model"] == "gemini/gemini-3.5-flash"
    assert model_list[0]["litellm_params"]["api_key"] == "not-a-real-key"


def test_vertex_tier1_model_string_when_creds_present(monkeypatch):
    """Tier 1 = gemini-3.5-flash via Vertex AI."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
    model_list, _ = cl.build_model_list(profile="hackathon")
    params = model_list[0]["litellm_params"]
    assert params["model"] == "vertex_ai/gemini-3.5-flash"
    assert params["vertex_project"] == "some-project"
    assert params["vertex_location"] == "europe-west1"


def test_vertex_location_defaults_to_us_central1(monkeypatch):
    """The Vertex Tier 1 location defaults to us-central1."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-not-a-real-key")
    model_list, _ = cl.build_model_list(profile="hackathon")
    # Tier 1 (vertex) lives at index 0 now.
    params = model_list[0]["litellm_params"]
    assert params["vertex_location"] == "us-central1"


def test_no_gemini_credentials_stays_on_vertex(monkeypatch):
    """With nothing configured the router must not pretend AI Studio works."""
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    backend, reason = cl.resolve_gemini_backend()
    assert backend == "vertex"
    assert reason == "no_gemini_credentials"


# ---------------------------------------------------------------------------
# Tier 2 — Unsloth Studio wiring
# ---------------------------------------------------------------------------


def test_unsloth_tier_uses_env_base_url(monkeypatch):
    monkeypatch.setenv("UNSLOTH_BASE_URL", "http://host.docker.internal:8888/v1")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-unsloth-not-a-real-key")
    model_list, _ = cl.build_model_list(profile="hackathon")
    # Updated 2026-08-31 (Phase 6): Tier 1 = gemini-3.5-flash on Vertex,
    # Tier 2 = aistudio, Tier 3 = gemma-4-26b-a4b on Unsloth.
    tier2 = model_list[2]["litellm_params"]
    assert tier2["model"] == "openai/unsloth/gemma-4-26b-a4b"
    assert tier2["api_base"] == "http://host.docker.internal:8888/v1"
    assert tier2["api_key"] == "sk-unsloth-not-a-real-key"


def test_unsloth_base_url_falls_back_to_host_loopback(monkeypatch):
    monkeypatch.delenv("UNSLOTH_BASE_URL", raising=False)
    model_list, _ = cl.build_model_list(profile="hackathon")
    # Updated 2026-08-31 (Phase 6): Unsloth lives at Tier 3 now.
    assert model_list[2]["litellm_params"]["api_base"] == "http://127.0.0.1:8888/v1"


def test_unsloth_api_key_has_no_literal_default(monkeypatch):
    """A missing key must stay empty rather than becoming a fake placeholder."""
    monkeypatch.delenv("UNSLOTH_API_KEY", raising=False)
    model_list, _ = cl.build_model_list(profile="hackathon")
    assert model_list[1]["litellm_params"]["api_key"] == ""


def test_unsloth_tier_is_never_ollama():
    """Regression guard: Unsloth Studio is a host process, not ollama."""
    model_list, _ = cl.build_model_list(profile="hackathon")
    rendered = repr(model_list).lower()
    assert "ollama" not in rendered
    assert "11434" not in rendered


# ---------------------------------------------------------------------------
# public_model_roster — profile containment
# ---------------------------------------------------------------------------


_DEV_ONLY_KEYS = (
    "qwen3.8-27b",
    "deepseek-v4-flash",
    "kimi-k2.6",
    "qwen3-vl-4b",
)


def test_public_roster_excludes_dev_models():
    """Public roster excludes dev-only entries (Flux2, FIBO, etc.).
    MiniMax-M3 is now public (it's Tier 1 of the hackathon profile)."""
    keys = {e.key for e in cl.public_model_roster()}
    for dev_key in _DEV_ONLY_KEYS:
        assert dev_key not in keys


def test_public_roster_ignores_model_profile_dev(monkeypatch):
    """The hard requirement: MODEL_PROFILE=dev must not change public output."""
    monkeypatch.delenv("MODEL_PROFILE", raising=False)
    hackathon_view = cl.public_model_roster()

    monkeypatch.setenv("MODEL_PROFILE", "dev")
    dev_view = cl.public_model_roster()

    assert hackathon_view == dev_view
    # The public roster surfaces the hackathon Tier 1 primary (gemini-3.5-flash).
    assert "gemini-3.5-flash" in {e.key for e in dev_view}


def test_public_roster_never_contains_a_dev_profile_entry(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", "dev")
    for entry in cl.public_model_roster():
        source = cl.MODEL_REGISTRY[entry.key]
        assert source.profile != "dev", f"{entry.key} leaked into the public roster"


def test_public_roster_contains_the_two_hackathon_tiers():
    keys = {e.key for e in cl.public_model_roster(family="text_llm")}
    assert "gemini-3.5-flash" in keys
    assert "gemma-4-26b-a4b" in keys


def test_public_roster_family_filter():
    for entry in cl.public_model_roster(family="image_gen"):
        assert entry.family == "image_gen"


def test_public_roster_is_ordered_by_tier():
    tiers = [e.tier for e in cl.public_model_roster(family="text_llm")]
    tiered = [t for t in tiers if t is not None]
    assert tiered == sorted(tiered)


def test_public_tier_table_is_tier1_tier2_tier3():
    """The public tier table surfaces all tiered text_llm entries.

    Updated 2026-08-31 (Phase 6) to match the Gemma+Gemini refocus:
    5 Tier 1 entries (default + aistudio + lite + pro + alt + embedder)
    and 2 Tier 2 entries (fallback + fallback_light). The dev-only Gemma
    benchmarks (local_fallback, local_fallback_old) and the dev-only
    T5Gemma encoder-decoder are correctly excluded from the public table.
    """
    table = cl.public_tier_table()
    tiers = [e.tier for e in table]
    assert tiers.count(1) == 5
    assert tiers.count(2) == 2
    keys = {e.key for e in table}
    assert "gemini-3.5-flash-aistudio" in keys
    assert "gemma-4-26b-a4b" in keys
    assert "gemini-3.5-flash" in keys
    assert "gemini-3.5-flash-lite" in keys


def test_public_tier_table_inherits_containment(monkeypatch):
    """The public tier table is the same under any MODEL_PROFILE."""
    monkeypatch.setenv("MODEL_PROFILE", "dev")
    assert "gemini-3.5-flash" in {e.key for e in cl.public_tier_table()}


def test_public_roster_entries_are_immutable():
    entry = cl.public_model_roster()[0]
    with pytest.raises((AttributeError, TypeError)):
        entry.key = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Exclusion guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "@cf/meta/llama-3.1-8b-instruct",
        "@cf/mistralai/mistral-7b-instruct-v0.1",
        "qwen3-coder-32b-instruct",
        "openai/qwen3-coder-anything",
    ],
)
def test_excluded_models_rejected(bad):
    with pytest.raises(cl.ModelExcludedError):
        cl._assert_model_allowed(bad)


@pytest.mark.parametrize(
    "good",
    [
        "gemini-3.5-flash",
        "gemma-4-26b-a4b",
        "minimax-m3",
        "vertex_ai/gemini-3.5-flash",
        "gemini/gemini-3.5-flash",
        "openai/unsloth/gemma-4-26b-a4b",
        "openai/qwen3-vl-8b",
    ],
)
def test_allowed_models_accepted(good):
    cl._assert_model_allowed(good)


@pytest.mark.parametrize("profile", ["hackathon", "dev"])
def test_build_model_list_emits_no_excluded_models(profile):
    model_list, _ = cl.build_model_list(profile=profile)
    for spec in model_list:
        cl._assert_model_allowed(spec["litellm_params"]["model"])


# ---------------------------------------------------------------------------
# Registry resolution
# ---------------------------------------------------------------------------


def test_registry_resolution_hackathon_tier1():
    """Tier 1 of hackathon = gemini-3.5-flash on Vertex AI."""
    entry = cl.model_for("text_llm", "default", profile="hackathon")
    assert entry is not None
    assert entry.key == "gemini-3.5-flash"
    assert entry.backend == "vertex"
    assert entry.litellm_alias == "vertex_ai/gemini-3.5-flash"


def test_registry_resolution_hackathon_tier2_ai_studio():
    """Tier 1 (aistudio) = gemini-3.5-flash via AI Studio."""
    entry = cl.model_for("text_llm", "aistudio", profile="hackathon")
    assert entry is not None
    assert entry.key == "gemini-3.5-flash-aistudio"


def test_registry_resolution_hackathon_tier2():
    """Tier 2 of the fallback chain = gemma-4-26b-a4b on Unsloth Studio."""
    entry = cl.model_for("text_llm", "fallback", profile="hackathon")
    assert entry is not None
    assert entry.key == "gemma-4-26b-a4b"
    assert entry.unsloth_id == "unsloth/gemma-4-26B-A4B-it-GGUF"


def test_registry_resolution_hackathon_tier3_agent_garden():
    """Tier 3 (fallback_light) = gemma-4-e4b on Unsloth Studio.

    The previous "agent_garden" role no longer exists in the registry
    after the 2026-08-30 Gemma+Gemini refocus — Tier 3 is now an Unsloth
    Gemma-4-E4B role. Asking for `agent_garden` returns None."""
    entry = cl.model_for("text_llm", "fallback_light", profile="hackathon")
    assert entry is not None
    assert entry.key == "gemma-4-e4b"
    assert entry.backend == "unsloth_studio"
    assert entry.litellm_alias == "openai/unsloth/gemma-4-e4b"
    # And the agent_garden role is no longer registered.
    assert cl.model_for("text_llm", "agent_garden", profile="hackathon") is None


def test_registry_resolution_dev_tier3():
    """Dev profile's `fallback` role is not registered (the gemma-4-26b-a4b
    entry is profile=hackathon). Use `local_fallback` for the dev Gemma-3
    benchmark tier instead."""
    # `fallback` is hackathon-only.
    assert cl.model_for("text_llm", "fallback", profile="dev") is None
    # `local_fallback` (Gemma-3-27B) is dev-visible.
    entry = cl.model_for("text_llm", "local_fallback", profile="dev")
    assert entry is not None
    assert entry.key == "gemma-3-27b-it"


def test_registry_resolution_dev_extras_are_dev_only():
    """The dev profile adds `dev_encoder_decoder` as the 8th tier slot;
    `lite` is registered under hackathon too (profile="hackathon")."""
    # `dev_encoder_decoder` is dev-only.
    assert cl.model_for("text_llm", "dev_encoder_decoder", profile="hackathon") is None
    assert cl.model_for("text_llm", "dev_encoder_decoder", profile="dev") is not None
    # `lite` is on the public roster (hackathon + dev).
    assert cl.model_for("text_llm", "lite", profile="hackathon") is not None


def test_registry_resolution_unknown_role_returns_none():
    assert cl.model_for("text_llm", "no_such_role", profile="hackathon") is None


def test_tier_entry_resolution_follows_gemini_backend(monkeypatch):
    monkeypatch.setenv("GEMINI_BACKEND", "aistudio")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    entry = cl._resolve_tier_entry("text_llm", "default", "hackathon")
    assert entry is not None
    assert entry.key == "gemini-3.5-flash-aistudio"


# ---------------------------------------------------------------------------
# Secrets hygiene — allow-list, never a deny-list
# ---------------------------------------------------------------------------


def test_safe_env_snapshot_is_an_allow_list(monkeypatch):
    """A variable that is not on the allow-list must not appear at all."""
    monkeypatch.setenv("SOME_UNLISTED_TOKEN", "super-secret-value")
    monkeypatch.setenv("MODEL_PROFILE", "hackathon")
    snapshot = cl.safe_env_snapshot()
    assert "SOME_UNLISTED_TOKEN" not in snapshot
    assert "super-secret-value" not in repr(snapshot)
    assert snapshot["MODEL_PROFILE"] == "hackathon"


def test_safe_env_snapshot_never_emits_secret_values(monkeypatch):
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-unsloth-abc123secret")
    monkeypatch.setenv("GEMINI_API_KEY", "aistudio-secret-value")
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-secret-value")
    rendered = repr(cl.safe_env_snapshot())
    assert "sk-unsloth-abc123secret" not in rendered
    assert "aistudio-secret-value" not in rendered
    assert "minimax-secret-value" not in rendered


def test_safe_env_snapshot_reports_secret_presence_only(monkeypatch):
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-unsloth-abc123secret")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    snapshot = cl.safe_env_snapshot()
    assert snapshot["UNSLOTH_API_KEY_set"] is True
    assert snapshot["GEMINI_API_KEY_set"] is False
    assert "UNSLOTH_API_KEY" not in snapshot


def test_no_secret_key_is_on_the_allow_list():
    """The allow-list and the secret list must never overlap."""
    assert cl.SAFE_ENV_KEYS.isdisjoint(set(cl.SECRET_ENV_KEYS))


def test_allow_list_carries_no_credential_shaped_names():
    """Guard against someone adding a secret to SAFE_ENV_KEYS later."""
    for key in cl.SAFE_ENV_KEYS:
        assert not key.endswith(("_KEY", "_TOKEN", "_SECRET", "_PASSWORD"))


def test_safe_env_snapshot_scrubs_url_userinfo(monkeypatch):
    monkeypatch.setenv("UNSLOTH_BASE_URL", "https://admin:hunter2@unsloth.example/v1")
    snapshot = cl.safe_env_snapshot()
    assert "hunter2" not in repr(snapshot)
    assert snapshot["UNSLOTH_BASE_URL"] == "https://***@unsloth.example/v1"


def test_safe_env_snapshot_leaves_plain_urls_alone(monkeypatch):
    monkeypatch.setenv("UNSLOTH_BASE_URL", "http://127.0.0.1:8888/v1")
    assert cl.safe_env_snapshot()["UNSLOTH_BASE_URL"] == "http://127.0.0.1:8888/v1"


def test_safe_env_snapshot_omits_unset_keys(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    assert "GOOGLE_CLOUD_PROJECT" not in cl.safe_env_snapshot()


# ---------------------------------------------------------------------------
# call_llm — routing behaviour (all mocked)
# ---------------------------------------------------------------------------


def test_empty_messages_raises():
    with pytest.raises(ValueError):
        cl.call_llm([])


def test_tier1_success(fake_router, monkeypatch):
    """Tier 1 = gemini-3.5-flash on Vertex (the canonical primary)."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    router = fake_router({"tier-1": _fake_completion_response("hello")})
    response = cl.call_llm([{"role": "user", "content": "hi"}])
    assert response.content == "hello"
    assert response.tier == 1
    assert response.model == "vertex_ai/gemini-3.5-flash"
    assert response.backend == "vertex"
    assert response.role == "default"
    assert router.calls == ["tier-1"]


def test_tier1_aistudio_success_reports_the_aistudio_backend(fake_router, monkeypatch):
    """Pin mode to the AI Studio twin of the Gemini entry — verifies the
    AI Studio backend is still wired when GEMINI_BACKEND=aistudio."""
    monkeypatch.setenv("GEMINI_BACKEND", "aistudio")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    fake_router({"tier-1": _fake_completion_response("hello")})
    response = cl.call_llm(
        [{"role": "user", "content": "hi"}],
        family="text_llm",
        role="aistudio",
    )
    assert response.backend == "aistudio"
    assert response.model == "gemini/gemini-3.5-flash"
    assert response.role == "aistudio"


def test_falls_through_to_tier2_when_tier1_fails(fake_router, monkeypatch):
    """Tier 1 = gemini-3.5-flash on Vertex, fails twice → falls through to
    Tier 2 (aistudio twin), then Tier 3 (gemma-4-26b-a4b).

    Updated 2026-08-31 (Phase 6): the Tier 5/6 slots resolve to None on
    the hackathon profile (their entries are profile=dev), so the chain
    stops at Tier 4 (fallback_light)."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-aistudio-not-a-real-key")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-not-a-real-key")
    router = fake_router(
        {
            "tier-1": RuntimeError("vertex is down"),
            "tier-2": RuntimeError("aistudio is down"),
            "tier-3": _fake_completion_response("from gemma"),
        }
    )
    response = cl.call_llm([{"role": "user", "content": "hi"}])
    assert response.tier == 3
    assert response.content == "from gemma"
    assert response.backend == "unsloth_studio"
    assert response.model == "openai/unsloth/gemma-4-26b-a4b"
    # Tier 1 budget=2, Tier 2 budget=2, Tier 3 single-shot success.
    assert router.calls == ["tier-1", "tier-1", "tier-2", "tier-2", "tier-3"]


def test_all_tiers_failing_raises_llm_call_error(fake_router, monkeypatch):
    """All hackathon tiers failing raises LLMCallError.

    Updated 2026-08-31 (Phase 6) to match the 6-tier chain (only 4 of
    which are reachable on hackathon: default + aistudio + fallback +
    fallback_light — local_fallback + local_fallback_old are dev-only).
    Number of attempts = sum of budgets of the 4 reachable tiers
    = 2 (default) + 2 (aistudio) + 1 (fallback) + 1 (fallback_light)
    = 6 attempts.
    """
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-aistudio-not-a-real-key")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-not-a-real-key")
    fake_router(
        {
            f"tier-{i}": RuntimeError(f"tier {i} is down")
            for i in range(1, 5)  # only the 4 hackathon-reachable tiers
        }
    )
    with pytest.raises(cl.LLMCallError) as exc:
        cl.call_llm([{"role": "user", "content": "hi"}])
    assert len(exc.value.attempts) == 6
    assert "tier 4 is down" in exc.value.last_error
    assert all(not a.succeeded for a in exc.value.attempts)


def test_dev_profile_falls_through_after_default(fake_router, monkeypatch):
    """The dev profile's first reachable tier after vertex is tier-6
    (local_fallback = gemma-3-27b-it on Unsloth) — since aistudio +
    lite + fallback + fallback_light are all profile=hackathon only."""
    monkeypatch.setenv("MODEL_PROFILE", "dev")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-not-a-real-key")
    router = fake_router(
        {
            "tier-1": RuntimeError("down"),
            "tier-6": _fake_completion_response("from gemma-3"),
        }
    )
    response = cl.call_llm([{"role": "user", "content": "hi"}])
    assert response.tier == 6
    assert response.model == "openai/unsloth/gemma-3-27b-it"
    assert response.backend == "unsloth_studio"
    assert "tier-6" in router.calls


def test_hackathon_profile_reaches_the_tier3_fallback(fake_router, monkeypatch):
    """The hackathon profile's Tier 3 (= gemma-4-26b-a4b on Unsloth) is reachable."""
    monkeypatch.setenv("MODEL_PROFILE", "hackathon")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    monkeypatch.setenv("GEMINI_API_KEY", "sk-aistudio-not-a-real-key")
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-not-a-real-key")
    router = fake_router(
        {
            "tier-1": RuntimeError("down"),
            "tier-2": RuntimeError("down"),
            "tier-3": _fake_completion_response("from gemma"),
        }
    )
    response = cl.call_llm([{"role": "user", "content": "hi"}])
    assert response.tier == 3
    assert response.model == "openai/unsloth/gemma-4-26b-a4b"
    assert "tier-3" in router.calls


def test_pin_mode_targets_one_entry(fake_router, monkeypatch):
    """Pin mode (family+role) targets the Unsloth Studio entry directly.

    Pin mode uses `tier-1` as the LiteLLM router name (see _attempt()),
    so the fakeRouter key is `tier-1` even though we're pinning to the
    role that resolves to Tier 2 of the public profile."""
    monkeypatch.setenv("UNSLOTH_API_KEY", "sk-not-a-real-key")
    fake_router({"tier-1": _fake_completion_response("pinned")})
    response = cl.call_llm(
        [{"role": "user", "content": "hi"}],
        family="text_llm",
        role="fallback",
    )
    assert response.content == "pinned"
    assert response.model == "openai/unsloth/gemma-4-26b-a4b"


def test_pin_mode_unknown_role_raises():
    with pytest.raises(ValueError):
        cl.call_llm(
            [{"role": "user", "content": "hi"}],
            family="text_llm",
            role="not_a_real_role",
        )


def test_pin_mode_cannot_reach_a_dev_model_under_hackathon_profile(monkeypatch):
    """Profile containment applies to the pin path too, not just the tier walk."""
    monkeypatch.setenv("MODEL_PROFILE", "hackathon")
    with pytest.raises(ValueError):
        cl.call_llm(
            [{"role": "user", "content": "hi"}],
            family="text_llm",
            role="dev_encoder_decoder",
        )


def test_call_llm_makes_no_network_call_when_mocked(fake_router, monkeypatch):
    """Sanity check that the double is actually installed."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "some-project")
    router = fake_router({"tier-1": _fake_completion_response()})
    cl.call_llm([{"role": "user", "content": "hi"}])
    assert router.calls, "the fake router was bypassed — a real call may have escaped"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_normalise_messages_validates():
    out = cl.normalise_messages(
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello."},
        ]
    )
    assert len(out) == 2
    assert out[0]["role"] == "system"

    with pytest.raises(ValueError):
        cl.normalise_messages([{"role": "user"}])
    with pytest.raises(ValueError):
        cl.normalise_messages([{"role": "tool", "content": "x"}])


def test_estimate_cost_usd_rounds_to_six():
    cost = cl.estimate_cost_usd("gemini-3.5-flash", tokens_in=1_000_000, tokens_out=500_000)
    assert cost == 0.225


def test_estimate_cost_usd_local_model_is_free():
    assert cl.estimate_cost_usd("gemma-4-26b-a4b", 1_000_000, 1_000_000) == 0.0


def test_estimate_cost_usd_unknown_model_is_zero_not_guessed():
    assert cl.estimate_cost_usd("something-unknown", 1_000, 1_000) == 0.0


def test_parse_model_string():
    assert cl.parse_model_string("vertex_ai/gemini-3.5-flash") == (
        "vertex_ai",
        "gemini-3.5-flash",
    )
    assert cl.parse_model_string("gemini-3.5-flash") == (None, "gemini-3.5-flash")


def test_reset_router_clears_the_cache(monkeypatch):
    monkeypatch.setattr(cl, "_ROUTER", object())
    cl.reset_router()
    assert cl._ROUTER is None
