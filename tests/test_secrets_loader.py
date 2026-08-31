"""Tests for `gemini_hackathon.secrets_loader` — the GSM-first secrets
catalog loader.

Updated 2026-08-31 (Phase 6): these tests exercise the 4 public entry points
(`_is_local_mode`, `_load_yaml`, `load_secrets`, `inject_into_environ`) +
the 2 internal helpers (`_load_from_dotenv`, `_load_from_gsm`). All tests
are offline — no live Google Secret Manager calls.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def reload_secrets_loader():
    """Reload `gemini_hackathon.secrets_loader` to drop the lru_cache."""
    import gemini_hackathon.secrets_loader as mod

    importlib.reload(mod)
    mod.load_secrets.cache_clear()
    return mod


def test_is_local_mode_defaults_to_false(reload_secrets_loader):
    """No `ADK_LOCAL_SECRETS` env var → not local mode."""
    import gemini_hackathon.secrets_loader as mod

    os.environ.pop("ADK_LOCAL_SECRETS", None)
    assert mod._is_local_mode() is False


def test_is_local_mode_truthy_values(monkeypatch, reload_secrets_loader):
    """`1`, `true`, `yes` activate local mode (case-insensitive)."""
    import gemini_hackathon.secrets_loader as mod

    for val in ("1", "true", "yes", "TRUE", "Yes"):
        monkeypatch.setenv("ADK_LOCAL_SECRETS", val)
        assert mod._is_local_mode() is True


def test_is_local_mode_falsy_values(monkeypatch, reload_secrets_loader):
    """`0`, `false`, `no`, blank → not local mode."""
    import gemini_hackathon.secrets_loader as mod

    for val in ("0", "false", "no", "", " "):
        monkeypatch.setenv("ADK_LOCAL_SECRETS", val)
        assert mod._is_local_mode() is False


def test_load_yaml_returns_project_and_entries(reload_secrets_loader):
    """`secrets.yaml` parses into `{project, entries}` with the canonical shape."""
    import gemini_hackathon.secrets_loader as mod

    config = mod._load_yaml()
    assert "project" in config
    # The committed secrets.yaml has at least the 11 canonical mapped entries
    # we ship out of the box (see secrets.yaml:1-99). Each entry has
    # `gsm_secret_id`, `env_var`, and `required: bool`.
    assert "entries" in config or any(
        isinstance(v, dict) and "env_var" in v for k, v in config.items()
    )


def test_load_from_dotenv_raises_if_missing(tmp_path, monkeypatch, reload_secrets_loader):
    """`ADK_LOCAL_SECRETS=1` requires `.env`; missing raises FileNotFoundError."""
    import gemini_hackathon.secrets_loader as mod

    monkeypatch.setenv("ADK_LOCAL_SECRETS", "1")
    # Point the loader's _DOTENV_PATH at a nonexistent directory.
    monkeypatch.setattr(mod, "_DOTENV_PATH", tmp_path / "does-not-exist" / ".env")

    with pytest.raises(FileNotFoundError, match=r"\.env"):
        mod._load_from_dotenv()


def test_load_from_dotenv_reads_values(tmp_path, monkeypatch, reload_secrets_loader):
    """Happy path: `.env` keys are loaded with the right value filter."""
    import gemini_hackathon.secrets_loader as mod

    monkeypatch.setenv("ADK_LOCAL_SECRETS", "1")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FOO_KEY=foo-value\nBAR_KEY=bar-value\nEMPTY_KEY=\nCOMMENTED_KEY=  # trailing comment\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "_DOTENV_PATH", env_file)

    values = mod._load_from_dotenv()
    assert values["FOO_KEY"] == "foo-value"
    assert values["BAR_KEY"] == "bar-value"
    # Empty values are filtered out.
    assert "EMPTY_KEY" not in values


def _drop_google_cloud_namespace() -> None:
    """Drop ``google.cloud`` + ``google.cloud.secretmanager`` from sys.modules.

    Same trick as `tests/dlt/test_gcs_substrate.py`:
    once `google.cloud` has any submodule imported, the namespace-package
    `__getattr__` re-imports sub-modules from disk instead of consulting
    sys.modules. Clear the cache so the lazy `from google.cloud import
    secretmanager` inside `_load_from_gsm` reads the patched module.
    """
    for mod_name in list(sys.modules):
        if mod_name == "google.cloud" or mod_name.startswith("google.cloud.secretmanager"):
            del sys.modules[mod_name]


def test_load_from_gsm_resolves_required_secrets(monkeypatch, reload_secrets_loader):
    """`_load_from_gsm` parses secrets.yaml + calls SecretManagerServiceClient."""
    import gemini_hackathon.secrets_loader as mod

    fake_response = MagicMock(name="Response")
    fake_response.payload.data = b"secret-value-bytes"

    fake_client = MagicMock(name="SecretManagerServiceClient")
    fake_client.access_secret_version.return_value = fake_response

    fake_sm_module_pkg = MagicMock(name="google.cloud.secretmanager")
    fake_sm_module_pkg.SecretManagerServiceClient.return_value = fake_client

    # Reload BEFORE setting the _load_yaml override so the lambda survives.
    importlib.reload(mod)
    mod.load_secrets.cache_clear()

    # Build a minimal secrets.yaml config: 1 required + 1 optional.
    sample_config = {
        "project": "agentic-hackathon-august-26",
        "entries": {
            "required-key": {
                "gsm_secret_id": "required-key",
                "env_var": "REQUIRED_KEY",
                "required": True,
            },
            "optional-key": {
                "gsm_secret_id": "optional-key",
                "env_var": "OPTIONAL_KEY",
                "required": False,
            },
        },
    }
    monkeypatch.setattr(mod, "_load_yaml", lambda: sample_config)

    _drop_google_cloud_namespace()
    with patch.dict(
        sys.modules,
        {
            "google.cloud.secretmanager": fake_sm_module_pkg,
        },
    ):
        secrets = mod._load_from_gsm()

    assert secrets["REQUIRED_KEY"] == "secret-value-bytes"
    assert secrets["OPTIONAL_KEY"] == "secret-value-bytes"
    assert fake_client.access_secret_version.call_count == 2


def test_load_from_gsm_optional_missing_logs_warning(monkeypatch, reload_secrets_loader, caplog):
    """Optional GSM secret missing → warning logged, not raised."""
    import gemini_hackathon.secrets_loader as mod

    fake_client = MagicMock(name="SecretManagerServiceClient")
    fake_client.access_secret_version.side_effect = RuntimeError("not found")

    fake_sm_module_pkg = MagicMock(name="google.cloud.secretmanager")
    fake_sm_module_pkg.SecretManagerServiceClient.return_value = fake_client

    importlib.reload(mod)
    mod.load_secrets.cache_clear()

    sample_config = {
        "project": "agentic-hackathon-august-26",
        "entries": {
            "opt-key": {"gsm_secret_id": "opt-key", "env_var": "OPT_KEY", "required": False},
        },
    }
    monkeypatch.setattr(mod, "_load_yaml", lambda: sample_config)

    _drop_google_cloud_namespace()
    with patch.dict(
        sys.modules,
        {
            "google.cloud.secretmanager": fake_sm_module_pkg,
        },
    ):
        caplog.set_level(logging.WARNING)
        secrets = mod._load_from_gsm()

    assert "OPT_KEY" not in secrets
    assert fake_client.access_secret_version.call_count == 1
    # Logger.warning was called with the canonical "Optional GSM secret" prefix.
    assert any("GSM secret" in rec.message or "opt-key" in rec.message for rec in caplog.records)


def test_load_secrets_local_mode_uses_dotenv(tmp_path, monkeypatch, reload_secrets_loader):
    """`ADK_LOCAL_SECRETS=1` → `load_secrets` reads `.env`, not GSM."""
    import gemini_hackathon.secrets_loader as mod

    # Reset lru_cache before adjusting env.
    importlib.reload(mod)
    mod.load_secrets.cache_clear()

    monkeypatch.setenv("ADK_LOCAL_SECRETS", "1")
    env_file = tmp_path / ".env"
    env_file.write_text("LITELLM_MASTER_KEY=sk-not-a-real-key\n", encoding="utf-8")
    monkeypatch.setattr(mod, "_DOTENV_PATH", env_file)

    secrets = mod.load_secrets()
    assert secrets.get("LITELLM_MASTER_KEY") == "sk-not-a-real-key"


def test_inject_into_environ_sets_defaults(monkeypatch, reload_secrets_loader):
    """`inject_into_environ` writes the loaded secret values via setdefault
    (does NOT clobber existing `os.environ` keys)."""
    import gemini_hackathon.secrets_loader as mod

    sample = {"MY_API_KEY": "from-gsm", "EXISTING_KEY": "should-be-set-if-absent"}
    monkeypatch.setenv("EXISTING_KEY", "already-set")  # pre-existing
    monkeypatch.delenv("MY_API_KEY", raising=False)

    monkeypatch.setattr(mod, "load_secrets", lambda: sample)

    returned = mod.inject_into_environ()
    assert returned == sample
    assert os.environ.get("MY_API_KEY") == "from-gsm"
    # pre-existing key is preserved (setdefault semantics)
    assert os.environ.get("EXISTING_KEY") == "already-set"
