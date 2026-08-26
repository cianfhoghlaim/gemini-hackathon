#!/usr/bin/env bash
# One-liner deploy of the gemini_hackathon Python backend to Google
# Cloud Run. Every value comes from env vars — never invent a project
# ID or region. Run from the repo root:
#
#   export GCP_PROJECT=my-gcp-project
#   export GCP_REGION=europe-west1
#   export GCP_SA=cloudrun-sa@${GCP_PROJECT}.iam.gserviceaccount.com
#   export UNSLOTH_API_KEY=sk-unsloth-...
#   export UNSLOTH_BASE_URL=https://my-unsloth-instance/v1
#   export GEMINI_API_KEY=sk-...
#   ./cloud/scripts/deploy-cloud-run.sh
#
# The script:
#   1. Enables the Cloud Run + Artifact Registry + Cloud Build APIs.
#   2. Creates the service account (if missing).
#   3. Provisions the 3 Secret Manager entries (idempotent).
#   4. Builds the container with Cloud Build (no local Docker required).
#   5. Deploys to Cloud Run with the right env + secret refs.
#   6. Smoke-tests the live endpoint with /api/health.

set -euo pipefail

: "${GCP_PROJECT:?Set GCP_PROJECT to your GCP project ID}"
: "${GCP_REGION:=europe-west1}"
: "${GCP_SA:=cloudrun-sa@${GCP_PROJECT}.iam.gserviceaccount.com}"
: "${UNSLOTH_API_KEY:?Set UNSLOTH_API_KEY (Infisical: dev-baile/unsloth/api_key)}"
: "${UNSLOTH_BASE_URL:?Set UNSLOTH_BASE_URL to the Unsloth Studio /v1 endpoint}"
: "${GEMINI_API_KEY:?Set GEMINI_API_KEY if using AI Studio instead of Vertex}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> Enabling APIs"
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    --project="$GCP_PROJECT"

echo "==> Ensuring Artifact Registry repo"
gcloud artifacts repositories create gemini-hackathon \
    --project="$GCP_PROJECT" \
    --location="$GCP_REGION" \
    --repository-format=docker 2>/dev/null || true

echo "==> Ensuring service account"
if ! gcloud iam service-accounts describe "$GCP_SA" --project="$GCP_PROJECT" >/dev/null 2>&1; then
    gcloud iam service-accounts create gemini-hackathon --project="$GCP_PROJECT" \
        --display-name="gemini-hackathon Cloud Run SA"
    GCP_SA="gemini-hackathon@${GCP_PROJECT}.iam.gserviceaccount.com"
fi

echo "==> Provisioning Secret Manager entries (idempotent)"
gcloud secrets create UNSLOTH_API_KEY --project="$GCP_PROJECT" --replication-policy=automatic 2>/dev/null || true
echo -n "$UNSLOTH_API_KEY" | gcloud secrets versions add UNSLOTH_API_KEY --project="$GCP_PROJECT" --data-file=-

gcloud secrets create UNSLOTH_BASE_URL --project="$GCP_PROJECT" --replication-policy=automatic 2>/dev/null || true
echo -n "$UNSLOTH_BASE_URL" | gcloud secrets versions add UNSLOTH_BASE_URL --project="$GCP_PROJECT" --data-file=-

gcloud secrets create GEMINI_API_KEY --project="$GCP_PROJECT" --replication-policy=automatic 2>/dev/null || true
echo -n "$GEMINI_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --project="$GCP_PROJECT" --data-file=-

echo "==> Granting SA access to secrets + AR"
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
    --member="serviceAccount:${GCP_SA}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
    --member="serviceAccount:${GCP_SA}" \
    --role="roles/artifactregistry.writer" >/dev/null
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
    --member="serviceAccount:${GCP_SA}" \
    --role="roles/run.invoker" >/dev/null

echo "==> Running Cloud Build (build + push + deploy)"
gcloud builds submit \
    --config=cloudbuild.yaml \
    --project="$GCP_PROJECT" \
    --substitutions=_REGION="$GCP_REGION",_REPO="$GCP_PROJECT/gemini-hackathon" \
    --no-source \
    --config-from-schema=false

echo "==> Smoke-testing the live endpoint"
SERVICE_URL=$(gcloud run services describe gemini-hackathon \
    --project="$GCP_PROJECT" \
    --region="$GCP_REGION" \
    --format="value(status.url)" 2>/dev/null || echo "")
if [ -n "$SERVICE_URL" ]; then
    echo "GET ${SERVICE_URL}/api/health"
    curl -fsS "${SERVICE_URL}/api/health" || echo "(health probe failed — check Cloud Run logs)"
fi

echo
echo "Done. Service URL above is your /api/{health,models,themes,chat/completions,agents/*,assets/*} base."
