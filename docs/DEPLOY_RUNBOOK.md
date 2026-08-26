# Deployment runbook — gemini_hackathon

End-to-end Cloud Run deployment. **Everything is env-driven.** No
hardcoded project IDs, regions, or service accounts.

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
