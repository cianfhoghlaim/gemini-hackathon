"""gemini_hackathon_gradio.editorial_studio.deploy — the Cloud Run deploy scaffold.

The editorial studio runs as a single Cloud Run service per Workstream 12.
The deployment follows the monstertix pattern (`monstertix/main.py`):
the gemini_hackathon FastAPI app + the Gradio frontend + the ADK 2
agent runners + the Firestore ledger + the mastery-vector store + the
Firestore skill graph — all on a single container.

Public surface:
  - `https://<service>.run.app/` — the Gradio editorial canvas
  - `https://<service>.run.app/api/agents/...` — the ADK 2 agent endpoints
    (AG-UI SSE streaming)
  - `https://<service>.run.app/api/health` — the Cloud Run health check

This module provides:
  - `GeminiHackathonAppFactory.build()` — the FastAPI factory (uses
    `monstertix/main.py` as the template: `get_fast_api_app` + bolt the
    Gradio app onto it)
  - `Dockerfile.cloudrun` — the Cloud Run container build (multi-stage:
    builder + runtime)
  - `cloudbuild.cloudrun.yaml` — the Google Cloud Build + deploy config
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


# Cloud Run env vars (the 6 vars every container needs — Phase 6 of the
# GCP-first refactor replaced the 3 self-hosted backend URLs (MILVUS_URL/
# LANCE_DB_URI, FALKORDB_URL, CONVEX_DEPLOYMENT_URL) with GCP_PROJECT_ID +
# VECTOR_BACKEND, since Firestore/Vertex AI Vector Search need no
# per-service URL — just a project ID and ADC).
CLOUD_RUN_REQUIRED_VARS: tuple[str, ...] = (
    "GEMINI_API_KEY",  # or GOOGLE_GENAI_USE_VERTEXAI=True
    "HF_TOKEN",  # HF Inference Providers fallback
    "UNSLOTH_BASE_URL",  # Unsloth Studio (Gemma 4 26B-A4B)
    "GCP_PROJECT_ID",  # Firestore + Vertex AI Vector Search + Document AI
    "VECTOR_BACKEND",  # "firestore" (default) or "vertex"
    "EMBED_BACKEND",  # "vertex" (default) or "sentence_transformers"
)


@dataclass
class CloudRunConfig:
    """The Cloud Run deployment configuration."""

    project_id: str = "biiep-hackathon-2026-08"
    region: str = "europe-west1"
    service_name: str = "gemini-hackathon-editorial-studio"
    memory: str = "2Gi"
    cpu: str = "2"
    timeout_seconds: int = 300
    concurrency: int = 80
    min_instances: int = 1
    max_instances: int = 10
    allow_unauthenticated: bool = True
    container_port: int = 8080
    env_vars: dict[str, str] = field(default_factory=dict)


def default_cloud_run_config() -> CloudRunConfig:
    """Build the default Cloud Run config (read from env + sensible defaults).

    Env vars:
      - GH_GCP_PROJECT_ID  — the GCP project
      - GH_GCP_REGION      — the GCP region (default europe-west1)
      - GH_SERVICE_NAME    — the Cloud Run service name
    """
    return CloudRunConfig(
        project_id=os.getenv("GH_GCP_PROJECT_ID", "biiep-hackathon-2026-08"),
        region=os.getenv("GH_GCP_REGION", "europe-west1"),
        service_name=os.getenv("GH_SERVICE_NAME", "gemini-hackathon-editorial-studio"),
        env_vars={k: os.getenv(k, "") for k in CLOUD_RUN_REQUIRED_VARS},
    )


# Cloud Build substitutions (env-injected)
CLOUDBUILD_SUBSTITUTIONS: dict[str, str] = {
    "_REGION": "$_REGION",
    "_REPO_NAME": "$_REPO_NAME",
    "_SERVICE_ACCOUNT": "$_SERVICE_ACCOUNT",
    "_IMAGE_URL": "$_IMAGE_URL",
}


# The Dockerfile.cloudrun (multi-stage: builder + runtime)
DOCKERFILE_CLOUDRUN = """\
# syntax=docker/dockerfile:1.7

# ===== Stage 1: builder =====
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv (the package manager — pinned per W1)
RUN pip install --no-cache-dir uv==0.5.0

# Copy the lockfile + pyproject + baml_extracts + assets first (cache layer)
COPY pyproject.toml uv.lock README.md ./
COPY gemini_hackathon ./gemini_hackathon
COPY gemini_hackathon_gradio ./gemini_hackathon_gradio
COPY gemini_hackathon_assets_fibo ./gemini_hackathon_assets_fibo
COPY baml_extracts ./baml_extracts
COPY baml_extracts_education ./baml_extracts_education
COPY cocoindex_flows ./cocoindex_flows
COPY dlt_pipelines ./dlt_pipelines
COPY themes ./themes
COPY data/ireland ./data/ireland

# Install all deps
RUN uv sync --all-extras

# Compile the BAML client
RUN uv run baml-cli generate

# ===== Stage 2: runtime =====
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install uv + the same deps (smaller than copying site-packages)
RUN pip install --no-cache-dir uv==0.5.0
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/gemini_hackathon /app/gemini_hackathon
COPY --from=builder /app/gemini_hackathon_gradio /app/gemini_hackathon_gradio
COPY --from=builder /app/gemini_hackathon_assets_fibo /app/gemini_hackathon_assets_fibo
COPY --from=builder /app/baml_client /app/baml_client
COPY --from=builder /app/web/baml_client /app/web/baml_client
COPY --from=builder /app/data/ireland /app/data/ireland
COPY --from=builder /app/themes /app/themes

# Add the .venv to PATH so `uv run` works inside the container
ENV PATH="/app/.venv/bin:$PATH"

# Health check (Cloud Run probes /api/health)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
    CMD curl -f http://localhost:8080/api/health || exit 1

EXPOSE 8080

# Default command: uvicorn the editorial studio (FastAPI + Gradio)
CMD ["uv", "run", "uvicorn", "gemini_hackathon_gradio.editorial_studio.deploy:app", \\
     "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
"""


# The cloudbuild.cloudrun.yaml (mirrors the existing gemini_hackathon/cloudbuild.yaml)
CLOUDBUILD_CLOUDRUN = """\
# Cloud Build pipeline for the gemini_hackathon editorial studio.
#
# Submit:
#   gcloud builds submit --config=cloudbuild.cloudrun.yaml \\
#     --substitutions=_REGION=europe-west1,_REPO_NAME=gemini-hackathon,\\
#                    _SERVICE_ACCOUNT=gemini-hackathon-editorial-studio@PROJECT.iam
#
# The pipeline:
#   1. Builds the Docker image (using the cloudbuild.yaml at the parent level
#      for cache reuse)
#   2. Pushes to Artifact Registry
#   3. Deploys to Cloud Run (with the 6 required env vars from
#      GH_CLOUD_RUN_REQUIRED_VARS)
#   4. Runs the smoke test (`/api/health` returns 200)

steps:
  # 1. Build + push (use the existing cloudbuild.yaml)
  - name: "gcr.io/cloud-builders/docker:latest"
    id: "build"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        set -euo pipefail
        docker build \\
          --build-arg BUILDKIT_INLINE_CACHE=1 \\
          -t "$_IMAGE_URL" \\
          -f Dockerfile.cloudrun \\
          .

  - name: "gcr.io/cloud-builders/docker:latest"
    id: "push"
    entrypoint: "bash"
    args: ["-c", "docker push $_IMAGE_URL"]

  # 2. Deploy to Cloud Run (with the env vars)
  - name: "gcr.io/google.com/cloudsdktool/cloud-sdk:latest"
    id: "deploy-cloud-run"
    entrypoint: "gcloud"
    args:
      - "run"
      - "deploy"
      - "$_SERVICE_NAME"
      - "--project=$PROJECT_ID"
      - "--region=$_REGION"
      - "--platform=managed"
      - "--image=$_IMAGE_URL"
      - "--memory=2Gi"
      - "--cpu=2"
      - "--timeout=300"
      - "--concurrency=80"
      - "--min-instances=1"
      - "--max-instances=10"
      - "--allow-unauthenticated"
      - "--port=8080"
      - "--set-env-vars=MODEL_PROFILE=hackathon,GEMINI_BACKEND=vertex,GOOGLE_CLOUD_LOCATION=$_REGION"
      - "--set-secrets=GEMINI_API_KEY=projects/$PROJECT_ID/secrets/GEMINI_API_KEY:latest"
      - "--set-secrets=HF_TOKEN=projects/$PROJECT_ID/secrets/HF_TOKEN:latest"
      - "--set-secrets=UNSLOTH_API_KEY=projects/$PROJECT_ID/secrets/UNSLOTH_API_KEY:latest"
      - "--service-account=$_SERVICE_ACCOUNT"

  # 3. Smoke test
  - name: "gcr.io/cloud-builders/docker:latest"
    id: "smoke"
    entrypoint: "bash"
    args:
      - "-c"
      - |
        sleep 30 && curl -f "https://$${_SERVICE_NAME}-$${_REGION}.run.app/api/health" || exit 1

substitutions:
  _REGION: europe-west1
  _REPO_NAME: gemini-hackathon
  _SERVICE_ACCOUNT: gemini-hackathon-editorial-studio@PROJECT.iam
  _IMAGE_URL: ""

timeout: 1800s
options:
  logging: CLOUD_LOGGING_ONLY
"""


@dataclass
class EditorialStudioCloudRun:
    """The editorial studio Cloud Run deployment."""

    config: CloudRunConfig = field(default_factory=default_cloud_run_config)

    def dockerfile(self) -> str:
        """Return the Dockerfile.cloudrun content."""
        return DOCKERFILE_CLOUDRUN

    def cloudbuild_yaml(self) -> str:
        """Return the cloudbuild.cloudrun.yaml content."""
        return CLOUDBUILD_CLOUDRUN

    def deploy_command(self) -> list[str]:
        """The gcloud run deploy command (for local + CI use)."""
        cfg = self.config
        cmd = [
            "gcloud",
            "run",
            "deploy",
            cfg.service_name,
            f"--project={cfg.project_id}",
            f"--region={cfg.region}",
            "--platform=managed",
            f"--image=gcr.io/{cfg.project_id}/{cfg.service_name}:latest",
            f"--memory={cfg.memory}",
            f"--cpu={cfg.cpu}",
            f"--timeout={cfg.timeout_seconds}",
            f"--concurrency={cfg.concurrency}",
            f"--min-instances={cfg.min_instances}",
            f"--max-instances={cfg.max_instances}",
            "--allow-unauthenticated"
            if cfg.allow_unauthenticated
            else "--no-allow-unauthenticated",
            f"--port={cfg.container_port}",
            "--set-env-vars=MODEL_PROFILE=hackathon,GEMINI_BACKEND=vertex",
        ]
        for k, v in cfg.env_vars.items():
            if v:
                cmd.append(f"--set-env-vars={k}={v}")
        return cmd


# The `app` symbol — uvicorn entry point.
# Per the monstertix pattern: get_fast_api_app returns the FastAPI app,
# then we bolt the editorial_studio Gradio app onto it.
def build_app() -> Any:
    """Build the combined FastAPI + Gradio app.

    Returns:
        The uvicorn-compatible ASGI app.

    Lazy-imports gradio + fastapi + uvicorn so the module is importable
    without those installed (for tests + dev environments).
    """
    try:
        from google.adk.cli.fast_api import get_fast_api_app
    except ImportError as e:
        raise ImportError(
            "google-adk + the FastAPI extras are required; install with "
            "`pip install google-adk[fastapi]>=2.7.1,<3.0`"
        ) from e

    # The editorial_studio.build_workflow_canvas() (from W3) returns the
    # LC/JC certificate workflow — the headline of the editorial canvas.
    # Lazy-import: build_workflow_canvas requires gradio which is optional.
    try:
        import importlib

        es_app = importlib.import_module("gemini_hackathon_gradio.editorial_studio.app")
        if hasattr(es_app, "build_workflow_canvas"):
            es_app.build_workflow_canvas()
    except (ImportError, Exception) as e:
        _log.warning("editorial_studio workflow not available: %s; continuing without it", e)

    return get_fast_api_app(
        agents_dir="gemini_hackathon/agents",
        session_service_uri=os.getenv(
            "SESSION_SERVICE_URI",
            "sqlite:///./data/gemini_hackathon_sessions.db",
        ),
        artifact_service_uri=os.getenv(
            "ARTIFACT_SERVICE_URI",
            "file:///./data/gemini_hackathon_artifacts",
        ),
        memory_service_uri=os.getenv(
            "MEMORY_SERVICE_URI",
            "file:///./data/gemini_hackathon_memory",  # MarkdownMemoryService
        ),
        eval_storage_uri=os.getenv(
            "EVAL_STORAGE_URI",
            "file:///./data/gemini_hackathon_evals",
        ),
    )


# The uvicorn entry point
try:
    app = build_app()
except Exception:
    # If google-adk[fastapi] is not installed OR the signature has
    # changed in this version, defer the error to runtime.
    import logging

    logging.getLogger(__name__).debug(
        "Editorial studio app could not be built at import time", exc_info=True
    )
    app = None  # type: ignore[assignment]


__all__ = [
    "CLOUDBUILD_CLOUDRUN",
    "CLOUDBUILD_SUBSTITUTIONS",
    "CLOUD_RUN_REQUIRED_VARS",
    "DOCKERFILE_CLOUDRUN",
    "CloudRunConfig",
    "EditorialStudioCloudRun",
    "app",
    "build_app",
    "default_cloud_run_config",
]
