#!/usr/bin/env -S uv run --python .venv-secrets --script
"""Audit script: compares secrets.yaml (catalogue) ↔ GSM API ↔ .env (local).

Reports three gaps:
  - In secrets.yaml but missing in GSM (not yet uploaded)
  - In GSM but not in secrets.yaml (orphaned; should be added or deleted)
  - In .env but not referenced in secrets.yaml (dead local value)

Usage:
    uv run python scripts/audit_gsm.py
    uv run python scripts/audit_gsm.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRETS_YAML = REPO_ROOT / "secrets.yaml"
DOTENV_PATH = REPO_ROOT / ".env"


def _load_yaml() -> dict:
    with SECRETS_YAML.open() as fh:
        return yaml.safe_load(fh)


def _load_dotenv_values() -> dict[str, str]:
    if not DOTENV_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for raw in DOTENV_PATH.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        values[key] = val
    return values


def _iter_entries(config: dict) -> dict[str, dict]:
    entries_blob = config.get("entries")
    if entries_blob:
        return entries_blob
    return {name: entry for name, entry in config.items() if isinstance(entry, dict)}


def _list_gsm_secrets(project: str) -> dict[str, dict]:
    try:
        from google.cloud import secretmanager  # type: ignore[import-not-found]
    except ImportError:
        print("google-cloud-secret-manager not installed.", file=sys.stderr)
        sys.exit(2)

    client = secretmanager.SecretManagerServiceClient()
    out: dict[str, dict] = {}
    for secret in client.list_secrets(request={"parent": f"projects/{project}"}):
        # secret.name = projects/.../secrets/<id>
        secret_id = secret.name.rsplit("/", 1)[-1]
        # Get the latest version metadata (do NOT access payload value)
        versions = list(client.list_secret_versions(request={"parent": secret.name, "filter": "state:ENABLED"}))
        latest = versions[0].name if versions else None
        out[secret_id] = {"resource": secret.name, "latest_version": latest}
    return out


def audit(project: str) -> dict:
    config = _load_yaml()
    catalogue = _iter_entries(config)
    dotenv = _load_dotenv_values()
    gsm = _list_gsm_secrets(project)

    catalogue_ids = {entry["gsm_secret_id"] for entry in catalogue.values()}
    catalogue_env_vars = {entry["env_var"] for entry in catalogue.values()}

    missing_in_gsm = sorted(catalogue_ids - set(gsm.keys()))
    orphan_in_gsm = sorted(set(gsm.keys()) - catalogue_ids)
    dead_in_dotenv = sorted(set(dotenv.keys()) - catalogue_env_vars)
    present_in_dotenv = sorted(set(dotenv.keys()) & catalogue_env_vars)

    return {
        "project": project,
        "catalogue_count": len(catalogue),
        "gsm_count": len(gsm),
        "dotenv_count": len(dotenv),
        "missing_in_gsm": missing_in_gsm,
        "orphan_in_gsm": orphan_in_gsm,
        "dead_in_dotenv": dead_in_dotenv,
        "present_in_dotenv": present_in_dotenv,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=None, help="Override GCP project")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    config = _load_yaml()
    project = args.project or os.environ.get("GCP_PROJECT") or config.get("project", "agentic-hackathon-august-26")

    try:
        result = audit(project)
    except Exception as exc:
        print(f"AUDIT FAILED: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"=== audit_gsm: project={project} ===")
    print(f"  catalogue (secrets.yaml): {result['catalogue_count']} entries")
    print(f"  GSM (live API):           {result['gsm_count']} secrets")
    print(f"  .env (local):             {result['dotenv_count']} values")
    print()
    if result["missing_in_gsm"]:
        print(f"  MISSING in GSM (need seed): {result['missing_in_gsm']}")
    else:
        print("  ✓ all catalogue secrets present in GSM")
    if result["orphan_in_gsm"]:
        print(f"  ORPHAN in GSM (not in catalogue, candidate for cleanup): {result['orphan_in_gsm']}")
    if result["dead_in_dotenv"]:
        print(f"  DEAD in .env (not referenced in catalogue): {result['dead_in_dotenv']}")
    if not result["missing_in_gsm"] and not result["orphan_in_gsm"] and not result["dead_in_dotenv"]:
        print("  ✓ fully consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
