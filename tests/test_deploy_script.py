"""Light tests for the Cloud Run deploy scaffold.

We don't actually deploy (that needs a real GCP project + service
account). We assert:
- the cloudbuild.yaml is well-formed (has required steps).
- the terraform manifest declares the variables we expect.
- the deploy shell script does the right thing when env vars are set
  AND fails fast when they aren't.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parent.parent


def test_cloudbuild_yaml_has_required_steps():
    text = (REPO / "cloudbuild.yaml").read_text()
    for required in [
        "name: \"gcr.io/cloud-builders/docker:latest\"",
        "docker push",
        "gcloud",
        "gcloud",
        "UNSLOTH_API_KEY",
        "_REGION: europe-west1",
    ]:
        assert required in text, f"missing {required!r} in cloudbuild.yaml"


def test_terraform_manifest_declares_project_and_region():
    text = (REPO / "cloud" / "terraform" / "cloud_run.tf").read_text()
    assert 'variable "project_id"' in text
    assert 'variable "region"' in text
    assert "google_artifact_registry_repository" in text
    assert "google_cloud_run_service" in text
    assert "google_secret_manager_secret" in text


def test_deploy_script_rejects_missing_env_vars():
    """The deploy script must fail fast when GCP_PROJECT is unset."""
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    env = {"PATH": "/usr/bin:/bin"}  # intentionally omit GCP_PROJECT et al.
    result = subprocess.run(
        ["bash", str(REPO / "cloud" / "scripts" / "deploy-cloud-run.sh")],
        env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "GCP_PROJECT" in result.stderr or "GCP_PROJECT" in result.stdout


def test_deploy_script_accepts_minimal_env():
    """With env set, the script attempts the API-enable call — and fails
    locally because there's no GCP_PROJECT *that exists*, but the env
    gate has been passed."""
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    env = {
        "PATH": "/usr/bin:/bin",
        "GCP_PROJECT": "definitely-not-a-real-project-for-testing",
        "GCP_REGION": "europe-west1",
        "UNSLOTH_API_KEY": "sk-not-real",
        "UNSLOTH_BASE_URL": "http://127.0.0.1:8888/v1",
        "GEMINI_API_KEY": "sk-not-real",
    }
    result = subprocess.run(
        ["bash", str(REPO / "cloud" / "scripts" / "deploy-cloud-run.sh")],
        env=env, capture_output=True, text=True, timeout=10,
    )
    # The script should get past the env gate (the first line) and then
    # fail on the first gcloud call (no creds in this env). Either way
    # the env gate has been passed.
    combined = (result.stdout + result.stderr).lower()
    assert "enabling apis" in combined or "definitely-not-a-real-project" in combined


def test_secrets_helper_section_in_deploy_script():
    """The deploy script contains a usage comment + the required env-var
    list so an operator can `cat scripts/deploy-cloud-run.sh` and run it."""
    text = (REPO / "cloud" / "scripts" / "deploy-cloud-run.sh").read_text()
    for required in [
        "GCP_PROJECT",
        "GCP_REGION",
        "UNSLOTH_API_KEY",
        "UNSLOTH_BASE_URL",
        "GEMINI_API_KEY",
    ]:
        assert required in text
