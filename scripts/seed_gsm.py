#!/usr/bin/env -S uv run --python .venv-secrets --script
"""One-shot uploader: reads secrets.yaml + .env, creates each GSM secret
and uploads the resolved value (creating a new version if the secret already
exists).

Usage:
    # default: project from secrets.yaml
    uv run python scripts/seed_gsm.py

    # explicit project override
    GCP_PROJECT=my-other-project uv run python scripts/seed_gsm.py

    # dry-run: don't write, just print what would happen
    uv run python scripts/seed_gsm.py --dry-run
"""

from __future__ import annotations

import argparse
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
    """Read .env via raw parsing (no python-dotenv dependency in this script)."""
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


def _iter_entries(config: dict) -> list[tuple[str, dict]]:
    entries_blob = config.get("entries")
    if entries_blob:
        return [(name, entry) for name, entry in entries_blob.items()]
    return [(name, entry) for name, entry in config.items() if isinstance(entry, dict)]


def seed(project: str, dotenv: dict[str, str], dry_run: bool) -> tuple[int, int, int]:
    try:
        from google.cloud import secretmanager  # type: ignore[import-not-found]
        from google.api_core import exceptions as gexc  # type: ignore[import-not-found]
    except ImportError:
        print("google-cloud-secret-manager not installed. Run:", file=sys.stderr)
        print("  uv pip install --python .venv-secrets google-cloud-secret-manager", file=sys.stderr)
        sys.exit(2)

    config = _load_yaml()
    entries = _iter_entries(config)
    client = secretmanager.SecretManagerServiceClient()

    created = updated = skipped = 0
    for _name, entry in entries:
        env_var = entry["env_var"]
        gsm_id = entry["gsm_secret_id"]
        required = entry.get("required", False)
        value = dotenv.get(env_var)

        if not value:
            if required:
                print(f"  SKIP (required, no value in .env)  {gsm_id} ← {env_var}", file=sys.stderr)
            else:
                print(f"  SKIP (optional, no value in .env)  {gsm_id} ← {env_var}")
            skipped += 1
            continue

        secret_path = f"projects/{project}/secrets/{gsm_id}"
        if dry_run:
            print(f"  DRY  {secret_path}  ←  {env_var}  ({len(value)} chars)")
            continue

        # Step 1: ensure secret exists
        try:
            client.get_secret(request={"name": secret_path})
            exists = True
        except gexc.NotFound:
            exists = False

        if not exists:
            print(f"  CREATE  {secret_path}")
            client.create_secret(
                request={
                    "parent": f"projects/{project}",
                    "secret_id": gsm_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            created += 1
        else:
            print(f"  UPDATE  {secret_path}")

        # Step 2: add a new version
        client.add_secret_version(
            request={
                "parent": secret_path,
                "payload": {"data": value.encode("utf-8")},
            }
        )
        if exists:
            updated += 1

    return created, updated, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=None, help="Override GCP project (default: from secrets.yaml)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without writing")
    args = parser.parse_args()

    config = _load_yaml()
    project = args.project or os.environ.get("GCP_PROJECT") or config.get("project", "agentic-hackathon-august-26")

    print(f"=== seed_gsm: project={project} dry_run={args.dry_run} ===")
    dotenv = _load_dotenv_values()
    print(f"Read {len(dotenv)} values from .env")
    if not dotenv:
        print(f"WARNING: .env empty or missing at {DOTENV_PATH}", file=sys.stderr)
    created, updated, skipped = seed(project, dotenv, args.dry_run)
    print(f"=== done: {created} created, {updated} updated, {skipped} skipped ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
