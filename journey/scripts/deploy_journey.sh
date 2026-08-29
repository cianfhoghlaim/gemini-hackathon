#!/usr/bin/env bash
# deploy_journey.sh — end-to-end Cloud Build + deploy + seed + smoke.
#
# Wraps the 5-step journey/cloudbuild.yaml into a single command, with the
# 3 deploy-time substitutions (region, image URL, event code) computed from
# the workshop host's gcloud config + a unique image tag.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo "")}
REGION=${GOOGLE_CLOUD_LOCATION:-europe-west1}
EVENT_CODE=${JOURNEY_EVENT_CODE:-biep-demo}
MAX_PARTICIPANTS=${JOURNEY_MAX_PARTICIPANTS:-200}
ADMIN_EMAIL=${JOURNEY_ADMIN_EMAIL:-$(gcloud config get-value account 2>/dev/null || echo "")}

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo "deploy_journey: GOOGLE_CLOUD_PROJECT not set and `gcloud config get-value project` returned empty."
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

ARTIFACT_REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/gemini-hackathon/gemini-hackathon-journey"
IMAGE_TAG="${EVENT_CODE}-$(date -u +%Y%m%d%H%M%S)"
IMAGE_URL="${ARTIFACT_REGISTRY}:${IMAGE_TAG}"

echo "==> Project:   $PROJECT_ID"
echo "==> Region:    $REGION"
echo "==> Image:     $IMAGE_URL"
echo "==> Event:     $EVENT_CODE"
echo "==> Max:       $MAX_PARTICIPANTS"
echo "==> Admin:     $ADMIN_EMAIL"
echo ""

gcloud builds submit "$REPO_ROOT" \
    --config="$REPO_ROOT/journey/cloudbuild.yaml" \
    --substitutions="_REGION=$REGION,_IMAGE_URL=$IMAGE_URL,_EVENT_CODE=$EVENT_CODE,_ADMIN_EMAIL=$ADMIN_EMAIL,_MAX_PARTICIPANTS=$MAX_PARTICIPANTS,_GCP_PROJECT=$PROJECT_ID" \
    --project="$PROJECT_ID"

SERVICE_URL=$(gcloud run services describe gemini-hackathon-journey \
    --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')
echo ""
echo "British Isles Journey is live at: $SERVICE_URL"
echo "Event dashboard:                  $SERVICE_URL/e/$EVENT_CODE"
echo "Per-learner progress (CLI):       uv run python -m journey.scripts.progress --event-code $EVENT_CODE --learner-id ALICE_EMAIL"
