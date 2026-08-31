# Deployment runbook — gemini_hackathon

End-to-end Cloud Run + Firebase + HF Spaces deployment. **Everything is env-driven.** No
hardcoded project IDs, regions, or service accounts.

## One-shot deploy (recommended)

If you have all 3 CLIs installed (`gcloud`, `firebase`, `hf`), use the
orchestrator target:

```bash
# Prereqs (one-time)
brew install --cask google-cloud-sdk    # or: https://cloud.google.com/sdk/docs/install
npm install -g firebase-tools
uv tool install "huggingface_hub[cli]"

# Auth + project
gcloud auth login
gcloud auth application-default login
gcloud config set project $GCP_PROJECT     # e.g. agentic-hackathon-august-26
firebase login

# Provision secrets (one-time per project)
make seed-gsm   # uploads secrets.yaml entries to GSM (see GSM_README.md)

# Deploy everything
make deploy     # runs cloudbuild + firebase-deploy + hf-publish-all
```

`make deploy` runs the 3 deploy stages sequentially:
1. **`cloudbuild`** — `gcloud builds submit --config=cloudbuild.yaml` → Cloud Run v2 service `gemini-hackathon-adk-dev`
2. **`firebase-deploy`** — Functions (themesApi, duckdbAsset, stitchSync) + Hosting + Firestore rules + indexes
3. **`hf-publish-all`** — All 6 Hugging Face Spaces (aistear, bunscoil, junior_cycle, leaving_certificate, learning_graphs, editorial_studio)

Each stage guards its prerequisite CLI (gcloud / firebase / hf) and exits with a clear error if missing.

## Per-stage deploy (advanced)

If you only want one stage (e.g. deploy the backend without touching Firebase), use the individual targets:

```bash
make cloudbuild          # Cloud Run only
make firebase-deploy     # Firebase only
make hf-publish-all      # HF Spaces only
```

## Prerequisites

1. **A GCP project** with billing enabled.
2. **gcloud CLI** installed and authenticated: `gcloud auth login && gcloud config set project $GCP_PROJECT`.
3. **3 secret values** (in `.env` or your shell):
   - `UNSLOTH_API_KEY` (the Unsloth Studio key, `sk-unsloth-...`)
   - `UNSLOTH_BASE_URL` (the Unsloth Studio `/v1` endpoint, e.g. `http://34.105.66.41:8888/v1`)
   - `GEMINI_API_KEY` (only required if you want the AI Studio fallback; Vertex AI uses ADC, no key needed)
4. The **deploy script** that ships in this repo: `cloud/scripts/deploy-cloud-run.sh`.

## One-time: provision secrets + service account

```bash
# 1. Create secrets (idempotent)
echo -n "$UNSLOTH_API_KEY" | gcloud secrets create UNSLOTH_API_KEY \
    --project=$GCP_PROJECT \
    --replication-policy=automatic --data-file=-
echo -n "$UNSLOTH_BASE_URL" | gcloud secrets create UNSLOTH_BASE_URL \
    --project=$GCP_PROJECT \
    --replication-policy=automatic --data-file=-
echo -n "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY \
    --project=$GCP_PROJECT \
    --replication-policy=automatic --data-file=-

# 2. Create the deploy SA + IAM bindings
gcloud iam service-accounts create gemini-hackathon \
    --project=$GCP_PROJECT \
    --display-name="gemini_hackathon Cloud Run SA"
gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member="serviceAccount:gemini-hackathon@${GCP_PROJECT}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member="serviceAccount:gemini-hackathon@${GCP_PROJECT}.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member="serviceAccount:gemini-hackathon@${GCP_PROJECT}.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

## Terraform (infrastructure-as-code)

```bash
cd cloud/terraform
terraform init
terraform plan \
    -var="project_id=$GCP_PROJECT" \
    -var="region=$GCP_REGION" \
    -var="service_account=gemini-hackathon@${GCP_PROJECT}.iam.gserviceaccount.com" \
    -var="allow_unauthenticated=true"
terraform apply -auto-approve
```

Outputs:

- `service_url` — the Cloud Run service URL (e.g. `https://gemini-hackathon-xyz.run.app`).
- `image_url` — the Artifact Registry path.

## Or, use the one-shot script

```bash
cd ~/dev/gemini_hackathon
export GCP_PROJECT=my-project
export GCP_REGION=europe-west1
export GCP_SA=gemini-hackathon@${GCP_PROJECT}.iam.gserviceaccount.com
export UNSLOTH_API_KEY=sk-unsloth-...
export UNSLOTH_BASE_URL=http://my-host/v1
export GEMINI_API_KEY=sk-...
./cloud/scripts/deploy-cloud-run.sh
```

The script does, in order:

1. Enables `run.googleapis.com`, `artifactregistry.googleapis.com`, `cloudbuild.googleapis.com`, `secretmanager.googleapis.com`.
2. Creates the Artifact Registry repo `gemini-hackathon` (idempotent).
3. Creates the SA if missing.
4. Provisions (or updates) the 3 Secret Manager entries.
5. Grants SA access to secrets + AR.
6. Submits `cloudbuild.yaml` to Cloud Build — which builds the image, pushes it, and deploys to Cloud Run.
7. Smoke-tests `GET /api/health` against the live service.

## What the deploy does

- **`Dockerfile`** is multi-stage (uv for resolution, distroless runtime).
- **`cloudbuild.yaml`** is the canonical CI/CD path. Same env-driven as the script.
- **`cloud/terraform/cloud_run.tf`** is the IaC path. Provision secrets first (the script does it for you).

## Test the live service

```bash
SERVICE_URL=$(terraform -chdir=cloud/terraform output -raw service_url)
# Or from the script:
SERVICE_URL=$(gcloud run services describe gemini-hackathon --region=$GCP_REGION --format="value(status.url)")

curl -s $SERVICE_URL/api/health | jq
curl -s $SERVICE_URL/api/themes | jq '.count'
curl -s $SERVICE_URL/api/models | jq '.[].key'
curl -s -X POST $SERVICE_URL/api/agents/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "what does the syllabus say about algebra?", "subnation": "ireland"}' | jq
```

## Rollback

```bash
gcloud run services delete gemini-hackathon --region=$GCP_REGION --quiet
terraform -chdir=cloud/terraform destroy -auto-approve
```

The Artifact Registry repo is preserved (deleting it costs nothing extra).

## Cost notes

- **Memory**: 2Gi / instance. Default concurrency 80.
- **Min instances**: 1 (set this to 0 in `cloud_run.tf` to scale to zero when idle; the 30s cold start is the trade-off).
- **Vertex AI**: stays inside the $150 hackathon credit allotment for the standard chat / RAG traffic. Don't accidentally hit Pro pricing.
- **Unsloth Studio**: runs on the user's GCE VM separate from this Cloud Run deployment — the URL is passed in via `UNSLOTH_BASE_URL`.

## What's on the service (10 endpoints)

`GET /api/health`, `GET /api/themes`, `GET /api/models`, `GET /api/duckdb`, `POST /api/agents/find-resources`, `POST /api/agents/chat`, `POST /api/assets/generate`, plus the TanStack Start SSR pages (`/`, `/subjects`, `/subjects/$slug`, `/safeguarding`, `/find-resources`, `/agents`, `/archipelago`, `/compare`).

See `docs/ARCHITECTURE.md` for the Mermaid diagram and the per-subnation user-context flow.

## Troubleshooting

- **`400` on `/api/agents/chat`** → the request body is malformed. Check that `messages` is a non-empty list and `model` (if set) is one of the public_roster keys.
- **`500` from the agent** → the LLM call failed (typically missing creds). The endpoint returns the error verbatim with a `hint` field — check the env vars (`GOOGLE_CLOUD_PROJECT`, `GEMINI_API_KEY`, `UNSLOTH_API_KEY`).
- **`404` on `/api/duckdb`** → the `.duckdb` file hasn't been materialised yet. Run `mise run compare:demo` first (which calls `run_comparison` and writes the rows).
- **`timeout` on Cloud Build** → bump `timeout:` in `cloudbuild.yaml` if your image is large.

## Phase 0 (2026-08-30) — GCP-first IaC refactor addendum

This addendum covers the **new** Terraform-based deployment target
that replaced the prior Oracle Cloud free tier hosting. The local dev
path (the original content above) is unchanged.

### Dev Cloud Run (Phase 0)

```bash
gcloud auth login
gcloud config set project $DEV_PROJECT

# Enable the 6 observability APIs (one-time)
gcloud services enable aiplatform.googleapis.com \
  serviceusage.googleapis.com \
  telemetry.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudtrace.googleapis.com

# Build + push the image
gcloud builds submit --config=cloudbuild.yaml \
  --project=$DEV_PROJECT \
  --substitutions=_IMAGE_URL="$REGION-docker.pkg.dev/$DEV_PROJECT/gemini-hackathon/backend:$SHA"

# Deploy via Compose
gcloud run compose up compose.yaml \
  -f docker-compose.dev-cloudrun.yaml \
  --project=$DEV_PROJECT --region=$REGION --max-instances=10
```

### Prod Cloud Run (Terraform)

```bash
cd cloud/terraform/envs/prod

# 1. Init (downloads the GCS backend state)
terraform init

# 2. Plan (review the diff!)
terraform plan -out=tfplan
cat tfplan | head -100  # or use terraform show tfplan
# Manual review required. Look for:
#   - 6 google_project_service.observability resources enabled
#   - 1 google_service_account.adk created
#   - 4 google_project_iam_member.adk_roles bound
#   - 4 google_secret_manager_secret.cloudrun_secret_*_secret created
#   - 1 google_cloud_run_v2_service.gemini-hackathon_backend deployed
#   - 1 google_cloud_run_v2_service.gemini-hackathon-frontend deployed
#   - All 6 Stackdriver env vars present on the backend service

# 3. Apply (after review)
terraform apply tfplan
```

### Verify the Stackdriver integration

```bash
# Get the backend URL
BACKEND_URL=$(terraform output -raw backend_url)

# /healthz returns the 5-key observability state
curl -fsS "${BACKEND_URL}/healthz" | jq .

# The Application Monitoring dashboard in the GCP console
# (Optimize > Observability > Application Monitoring) auto-populates
# from the OTLP spans
open "https://console.cloud.google.com/monitoring/traces/explorer?project=$DEV_PROJECT"
```

### Local dev with the same 6-env-var contract

```bash
# Set the 6 Stackdriver env vars (the contract is the same locally)
export OTEL_SERVICE_NAME='gemini-hackathon-adk'
export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED='true'
export OTEL_SEMCONV_STABILITY_OPT_IN='gen_ai_latest_experimental'
export OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT='EVENT_ONLY'
export ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS='false'
export GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY='true'
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT='http://localhost:4318'  # local OTLP collector

# Run the app
uv run uvicorn gemini_hackathon_backend.main:app --reload
```

### Roll back

```bash
cd cloud/terraform/envs/prod
terraform plan -destroy -out=tfplan-destroy
terraform apply tfplan-destroy
```

The `disable_on_destroy = false` on the `google_project_service`
resources ensures the APIs stay enabled after a destroy (other stacks in
the same project may still need them).
