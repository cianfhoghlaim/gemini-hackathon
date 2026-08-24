# Deployment — gemini_hackathon

> **Last updated:** 2026-08-24

This document describes the deployment options for
`gemini_hackathon`:

1. **Local development** with `uv` (the canonical Python
   package manager)
2. **Docker Compose** (the canonical local-containerised
   deployment)
3. **Google Cloud Run** (the chosen hackathon deployment target)

---

## 1. Local development with uv

`uv` is the canonical Python package manager for this repo. The
`uv` workflow is:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repo
git clone https://github.com/your-org/gemini_hackathon.git
cd gemini_hackathon

# Create the virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install the dependencies (from pyproject.toml)
uv pip install -e .

# Install the dev dependencies (pytest, mypy, ruff, etc.)
uv pip install -e ".[dev]"

# Run the theming extraction notebook
uv run marimo edit notebooks/theming_extraction.py

# Run the tests
uv run pytest tests/

# Validate the OpenSpec change
openspec validate 2026-08-24-gemini-hackathon-public-v1 --strict
```

The one-shot setup script (`setup.sh`) automates the steps
above:

```bash
./setup.sh
```

The script:

1. Installs `uv` if not already installed
2. Creates the virtual environment
3. Installs the dependencies + the dev dependencies
4. Starts the local llama.cpp server (for the Tier 2 fallback)
5. Prints the next-steps instructions

---

## 2. Docker Compose

The Docker Compose stack at `docker-compose.yaml` brings up:

- **`backend`** — the Hono + oRPC backend on port `8080`
- **`frontend`** — the TanStack Start frontend on port `3000`
- **`llamacpp`** — the local llama.cpp server for the Tier 2
  fallback on port `8081`
- **`langfuse`** — the Langfuse observability server on port
  `3001`
- **`mlflow`** — the MLflow experiment tracking server on port
  `5000`
- **`convex`** — the Convex self-hosted server on port `3210`
- **`motherduck-proxy`** — the MotherDuck proxy (managed service,
  not self-hosted) on port `6543`

### Bring up the stack

```bash
# Pull the latest images
docker compose pull

# Bring up the stack
docker compose up -d

# Tail the logs
docker compose logs -f

# Verify the backend is healthy
curl http://localhost:8080/health

# Verify the frontend is healthy
curl http://localhost:3000/health

# Verify Langfuse is healthy
curl http://localhost:3001/api/public/health

# Verify MLflow is healthy
curl http://localhost:5000/health
```

### Tear down the stack

```bash
# Stop the stack (keeps the data)
docker compose down

# Stop the stack + remove the volumes
docker compose down -v
```

---

## 3. Google Cloud Run deployment

Google Cloud Run is the **chosen hackathon deployment target**.
Cloud Run is a serverless container platform that scales to zero
when idle, which is perfect for a hackathon project.

### Prerequisites

1. A Google Cloud project (the hackathon project is
   `gemini-hackathon`)
2. The `gcloud` CLI installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project gemini-hackathon
   ```
3. The Cloud Run Admin API enabled:
   ```bash
   gcloud services enable run.googleapis.com
   ```
4. The Artifact Registry API enabled (for the container images):
   ```bash
   gcloud services enable artifactregistry.googleapis.com
   ```

### Step 1 — Build the container image

```bash
# Create the Artifact Registry repository (one-time)
gcloud artifacts repositories create gemini-hackathon \
    --repository-format=docker \
    --location=europe-west1 \
    --description="gemini_hackathon container images"

# Build + push the backend image
gcloud builds submit \
    --tag europe-west1-docker.pkg.dev/gemini-hackathon/gemini-hackathon/backend:latest \
    ./backend

# Build + push the frontend image
gcloud builds submit \
    --tag europe-west1-docker.pkg.dev/gemini-hackathon/gemini-hackathon/frontend:latest \
    ./web
```

### Step 2 — Deploy the backend to Cloud Run

```bash
gcloud run deploy gemini-hackathon-backend \
    --image=europe-west1-docker.pkg.dev/gemini-hackathon/gemini-hackathon/backend:latest \
    --region=europe-west1 \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=60 \
    --max-instances=10 \
    --set-env-vars=MINIMAX_API_KEY=projects/gemini-hackathon/secrets/minimax-api-key/versions/latest \
    --set-env-vars=GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-application-credentials.json \
    --set-secrets=MINIMAX_API_KEY=minimax-api-key:latest \
    --set-secrets=GOOGLE_APPLICATION_CREDENTIALS=google-application-credentials:latest
```

The `MINIMAX_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS`
secrets are sourced from **Google Secret Manager** (per the
upstream secrets-management contract).

### Step 3 — Deploy the frontend to Cloud Run

```bash
gcloud run deploy gemini-hackathon-frontend \
    --image=europe-west1-docker.pkg.dev/gemini-hackathon/gemini-hackathon/frontend:latest \
    --region=europe-west1 \
    --platform=managed \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --timeout=30 \
    --max-instances=10 \
    --set-env-vars=NEXT_PUBLIC_API_URL=https://gemini-hackathon-backend-xxx.a.run.app \
    --set-env-vars=NEXT_PUBLIC_CONVEX_URL=https://gemini-hackathon-convex-xxx.convex.cloud
```

### Step 4 — Wire the custom domain

```bash
# Map the custom domain (per the upstream Cloudflare + Cloud Run
# ingress contract)
gcloud run domain-mappings create \
    --service=gemini-hackathon-frontend \
    --domain=gemini-hackathon.cianfhoghlaim.ie \
    --region=europe-west1
```

### Step 5 — Verify the deployment

```bash
# Verify the backend is healthy
curl https://gemini-hackathon-backend-xxx.a.run.app/health

# Verify the frontend is healthy
curl https://gemini-hackathon.cianfhoghlaim.ie/

# Verify the OpenSpec change validates
openspec validate 2026-08-24-gemini-hackathon-public-v1 --strict
```

---

## 4. Environment variables

The following environment variables MUST be set in any
deployment (local, Docker, or Cloud Run):

| Variable | Source | Description |
|----------|--------|-------------|
| `MINIMAX_API_KEY` | Infisical / Google Secret Manager | The minimax-m3 API key (Tier 1) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Infisical / Google Secret Manager | The service-account JSON path for Vertex AI (Tier 3) |
| `VERTEX_PROJECT` | Static (default `gemini-hackathon`) | The Google Cloud project for Vertex AI |
| `VERTEX_LOCATION` | Static (default `europe-west1`) | The Google Cloud region for Vertex AI |
| `LLAMACPP_API_BASE` | Static (default `http://localhost:8081`) | The llama.cpp server URL (Tier 2) |
| `LANGFUSE_PUBLIC_KEY` | Infisical / Google Secret Manager | The Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Infisical / Google Secret Manager | The Langfuse secret key |
| `LANGFUSE_HOST` | Static (default `https://cloud.langfuse.com`) | The Langfuse host |
| `CONVEX_URL` | Infisical / Google Secret Manager | The Convex deployment URL |
| `MOTHERDUCK_TOKEN` | Infisical / Google Secret Manager | The MotherDuck API token |

The Infisical paths follow the upstream `secrets-management`
contract:

```
infisical://dev-baile/gemini_hackathon/minimax-api-key
infisical://dev-baile/gemini_hackathon/google-application-credentials
infisical://dev-baile/gemini_hackathon/langfuse-public-key
infisical://dev-baile/gemini_hackathon/langfuse-secret-key
infisical://dev-baile/gemini_hackathon/convex-url
infisical://dev-baile/gemini_hackathon/motherduck-token
```

---

## 5. References

- [`README.md`](../README.md) — the main project README
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — the architecture
  deep-dive
- [`docs/MODEL_POLICY.md`](MODEL_POLICY.md) — the model policy
- [`docs/THEMING.md`](THEMING.md) — the theming guide
- [`Dockerfile`](../Dockerfile) — the multi-stage `uv`-based
  container image
- [`docker-compose.yaml`](../docker-compose.yaml) — the
  Docker Compose stack
- [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) —
  the GitHub Actions CI workflow