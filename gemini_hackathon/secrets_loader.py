"""Google Cloud Secret Manager loader for gemini_hackathon.

Resolution contract:
  - If `ADK_LOCAL_SECRETS=1`: read from `.env` (gitignored) via python-dotenv.
  - Otherwise: use Application Default Credentials (ADC) and call
    `secretmanager.googleapis.com` to fetch each secret listed in
    `secrets.yaml`.

Usage:
    from gemini_hackathon.secrets_loader import load_secrets

    secrets = load_secrets()
    openai_key = secrets["OPENAI_API_KEY"]
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

LOGGER = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SECRETS_YAML = _REPO_ROOT / "secrets.yaml"
_DOTENV_PATH = _REPO_ROOT / ".env"


def _is_local_mode() -> bool:
    """Local mode is opt-in via ADK_LOCAL_SECRETS=1.

    Defaults to False so production deploys (Cloud Run, GCE, GKE)
    always use ADC + Secret Manager unless explicitly overridden.
    """
    return os.environ.get("ADK_LOCAL_SECRETS", "").strip().lower() in {"1", "true", "yes"}


def _load_yaml() -> dict[str, Any]:
    if not _SECRETS_YAML.exists():
        raise FileNotFoundError(
            f"secrets.yaml not found at {_SECRETS_YAML}. "
            "Did you forget to add the GSM ID catalogue?"
        )
    with _SECRETS_YAML.open() as fh:
        return yaml.safe_load(fh)


def _load_from_dotenv() -> dict[str, str]:
    """Read .env via python-dotenv (no GSM)."""
    try:
        from dotenv import dotenv_values
    except ImportError as exc:  # pragma: no cover
        raise ImportError("python-dotenv required for ADK_LOCAL_SECRETS=1") from exc

    if not _DOTENV_PATH.exists():
        raise FileNotFoundError(
            f".env not found at {_DOTENV_PATH} (ADK_LOCAL_SECRETS=1 requires it). "
            "Copy .env.example → .env and fill in the values, or unset ADK_LOCAL_SECRETS."
        )
    values = dotenv_values(_DOTENV_PATH)
    return {k: v for k, v in values.items() if v is not None and v != ""}


def _load_from_gsm() -> dict[str, str]:
    """Read each GSM secret ID listed in secrets.yaml and return {env_var: value}."""
    try:
        from google.cloud import secretmanager  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "google-cloud-secret-manager not installed. "
            "Run: uv pip install google-cloud-secret-manager"
        ) from exc

    config = _load_yaml()
    project = config.get("project", "agentic-hackathon-august-26")
    entries = config.get("entries") or {k: v for k, v in config.items() if isinstance(v, dict)}

    client = secretmanager.SecretManagerServiceClient()
    parent_prefix = f"projects/{project}"
    resolved: dict[str, str] = {}

    for _name, entry in entries.items():
        env_var = entry["env_var"]
        gsm_id = entry["gsm_secret_id"]
        required = entry.get("required", False)

        secret_path = f"{parent_prefix}/secrets/{gsm_id}/versions/latest"
        try:
            response = client.access_secret_version(request={"name": secret_path})
            value = response.payload.data.decode("utf-8")
            resolved[env_var] = value
            LOGGER.debug("Loaded GSM secret %s → %s", gsm_id, env_var)
        except Exception as exc:
            if required:
                raise RuntimeError(
                    f"Required GSM secret '{gsm_id}' (env {env_var}) "
                    f"could not be loaded from {secret_path}: {exc}"
                ) from exc
            LOGGER.warning("Optional GSM secret %s unavailable: %s", gsm_id, exc)

    return resolved


@lru_cache(maxsize=1)
def load_secrets() -> dict[str, str]:
    """Load the resolved env-var → value map.

    Cached for process lifetime. Call `load_secrets.cache_clear()` to force reload.
    """
    if _is_local_mode():
        LOGGER.info("ADK_LOCAL_SECRETS=1 → reading secrets from %s", _DOTENV_PATH)
        return _load_from_dotenv()

    LOGGER.info("Loading secrets from GSM (project=%s)", os.environ.get("GCP_PROJECT", "agentic-hackathon-august-26"))
    return _load_from_gsm()


def inject_into_environ() -> dict[str, str]:
    """Inject loaded secrets into `os.environ` for downstream libraries
    (BAML, LiteLLM, Langfuse, etc.) that read `os.environ` directly.

    Returns the resolved map for callers that want to log/inspect.
    """
    secrets = load_secrets()
    for key, value in secrets.items():
        os.environ.setdefault(key, value)
    return secrets


if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        result = load_secrets()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2))
