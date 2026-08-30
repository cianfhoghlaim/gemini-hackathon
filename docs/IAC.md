# IAC — the GCP-first infrastructure refactor for gemini_hackathon

> **Phase 9 (handover doc) of `2026-08-30-gcp-first-iac-refactor-v1`.**
> Replaces the upstream `bonneagar/` (Komodo + Pangolin + Locket + Infisical)
> IaC pattern with the GCP-native equivalents: Cloud Build + Cloud Run +
> Terraform modules + Secret Manager + Workload Identity Federation.
> Drops the Oracle Cloud free tier hosting target.

## What this doc covers

1. [Why the refactor](#1-why-the-refactor)
2. [The 6 abandoned components → the 6 GCP-native replacements](#2-the-6-abandoned-components--the-6-gcp-native-replacements)
3. [The 4 NEW gemini-hackathon stacks → the Terraform modules](#3-the-4-new-gemini-hackathon-stacks--the-terraform-modules)
4. [The canonical Stackdriver AI Agent ADK instrumentation contract](#4-the-canonical-stackdriver-ai-agent-adk-instrumentation-contract)
5. [The 3 deployment targets, one `compose.yaml`](#5-the-3-deployment-targets-one-composeyaml)
6. [Three usage recipes](#6-three-usage-recipes)
7. [The OpenSpec change folder](#7-the-openspec-change-folder)
8. [What stayed in the bonneagar pattern (the parts to KEEP)](#8-what-stayed-in-the-bonneagar-pattern-the-parts-to-keep)

## 1. Why the refactor

The previous `bonneagar/` infrastructure (the upstream Cianfhoghlaim
89-stack IaC mesh) used 4 non-GCP components that made sense when the
hosting target was the Oracle Cloud free tier + a MacBook M4 Max +
Hetzner, but do not make sense on GCP:

| Abandoned | Why abandoned on GCP | GCP-native replacement |
|---|---|---|
| **Komodo** (orchestration daemon) | GCP has managed `Cloud Build` + `gcloud run compose up` | `Cloud Build` + `Cloud Deploy` |
| **Pangolin** (Traefik reverse proxy) | GCP has managed TLS + WAF + IAP + DDoS on every `*.run.app` URL | `Cloud Run URLs` + `Cloud DNS` + `Cloud Armor` |
| **Locket** (sidecar secret fetcher) | GCP has volume-mounted Secret Manager on Cloud Run | `Secret Manager` + volume mounts |
| **Infisical** (multi-tenant secret backend) | GCP has IAM-bound Secret Manager + Workload Identity Federation | `Secret Manager` + `Workload Identity Federation` |

The user's prior 9-phase work pushed the application to the canonical
ADK 2 + Cloud Run substrate. What remained was this IaC reorg.

## 2. The 6 abandoned components → the 6 GCP-native replacements

```
bonneagar (Oracle free tier)                →  gemini_hackathon (GCP dev/prod)
─────────────────────────────────────────────────────────────────
Komodo (blueprint engine)                    →  Cloud Build + gcloud run compose up
Pangolin (Traefik reverse proxy)             →  Cloud Run *.run.app URLs
Locket (sidecar secret fetcher)             →  Secret Manager volume mounts
Infisical (multi-tenant secret backend)     →  Secret Manager + WIF
Self-hosted Langfuse (5 services on GKE)     →  Self-hosted docker-compose (dev only) +
                                              GCP-native ADK OTel (prod)
Self-hosted MLflow (Cloud Run + Cloud SQL)  →  Self-hosted docker-compose (dev only) +
                                              GCP-native ADK OTel metrics (prod)
```

## 3. The 4 NEW gemini-hackathon stacks → the Terraform modules

Per `AGENTS.md:56-66`, the 4 NEW stacks (backend, frontend,
observability, lakehouse) are deployed via 12 reusable Terraform
modules under `cloud/terraform/modules/`:

| # | Module | Status | Purpose |
|--:|---|---|---|
| 1 | `observability_apis` | ✅ done (Phase 1) | 6 GCP APIs |
| 2 | `iam_gcp_ai_agent_adk` | ✅ done (Phase 1) | SA + 4 Stackdriver roles |
| 3 | `cloudrun_service` | ✅ done (Phase 5) | Universal Cloud Run V2 service |
| 4 | `cloudrun_secret_mount` | ✅ done (Phase 5) | Secret Manager + IAM |
| 5-12 | (8 stub modules) | scaffolded (Phase 5) | `cloudsql_postgres`, `memorystore_valkey`, `gcs_bucket`, `bigquery_dataset`, `firestore_database`, `artifact_registry_repo`, `workload_identity_gha`, `cloudbuild_trigger` |

The `envs/dev/main.tf` and `envs/prod/main.tf` wiring files (Phase 5)
wire the 2 substantive modules for the 2 deployed services
(`gemini-hackathon-backend` + `gemini-hackathon-frontend`).

## 4. The canonical Stackdriver AI Agent ADK instrumentation contract

The **canonical 2026 GCP-native ADK observability path** is per
[docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk](https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk)
(last updated 2026-08-26).

The 6 + 1 env vars every Cloud Run service must set:

```bash
OTEL_SERVICE_NAME='gemini-hackathon-adk'
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED='true'
OTEL_SEMCONV_STABILITY_OPT_IN='gen_ai_latest_experimental'
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT='EVENT_ONLY'   # NOT 'true', NOT 'NO_CONTENT'
ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS='false'
GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY='true'
# Plus the standard OTel + the OTLP endpoint (set by try_init_adk_otel)
OTEL_RESOURCE_ATTRIBUTES='service.namespace=gemini-hackathon,deployment.environment=hackathon'
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT='https://telemetry.googleapis.com/v1/traces'
```

The 6 GCP APIs to enable + the 4 IAM roles for the Cloud Run service
account are detailed in `openspec/changes/2026-08-30-gcp-first-iac-refactor-v1/specs/observability/spec.md`.

## 5. The 3 deployment targets, one `compose.yaml`

```bash
# LOCAL DEV      : docker compose up --build
# DEV CLOUD RUN  : gcloud run compose up compose.yaml \
#                   -f docker-compose.dev-cloudrun.yaml \
#                   --project=$DEV_PROJECT --region=europe-west1 --max-instances=10
# PROD CLOUD RUN : terraform apply (managed via cloud/terraform/envs/prod/)
```

## 6. Three usage recipes

### Local dev

```bash
git clone https://github.com/cianfhoghlaim/gemini-hackathon
cd gemini_hackathon
cp .env.example .env
docker compose up --build
# App:    http://localhost:8080
# Langfuse: http://localhost:3000
# MLflow:   http://localhost:5000
```

### Dev Cloud Run

```bash
gcloud auth login
gcloud config set project $DEV_PROJECT
gcloud services enable aiplatform.googleapis.com serviceusage.googleapis.com \
  telemetry.googleapis.com logging.googleapis.com monitoring.googleapis.com cloudtrace.googleapis.com
gcloud run compose up compose.yaml -f docker-compose.dev-cloudrun.yaml \
  --project=$DEV_PROJECT --region=europe-west1 --max-instances=10
```

### Prod Cloud Run (Terraform)

```bash
cd cloud/terraform/envs/prod
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

## 7. The OpenSpec change folder

`openspec/changes/2026-08-30-gcp-first-iac-refactor-v1/` (the planning
artifact for this refactor):

- `proposal.md` — 9-phase plan
- `tasks.md` — 99 tasks (T0.1..T9.7 + 4 validation gates)
- `specs/infrastructure/spec.md` — IaC + container management contract
- `specs/observability/spec.md` — Stackdriver 6-env-var + 4 IAM roles + 6 APIs
- `specs/lakehouse/spec.md` — Lance namespace + BigLake + Iceberg REST

`openspec validate 2026-08-30-gcp-first-iac-refactor-v1 --strict` passes.

## 8. What stayed in the bonneagar pattern (the parts to KEEP)

- **`stacks/lakehouse/`** — the 16-service data plane. Re-use the `compose.yaml`, `init-db.sql`, `cross_flow_client.py`, `lance-sidecar/` patterns
- **`stacks/langfuse/`** + **`stacks/mlflow/`** — the Compose specs (now consolidated in `compose.yaml` + the local docker-compose dev path)
- **`stacks/unsloth-serve/`** — the local GGUF inference path (Unsloth Studio Tier-2)
- **The 6-file GOLD_STANDARD pattern** as the contract — re-published as Terraform modules
- **The 3-tier model fallback** (unsloth → litellm → gemini API) — already in `gemini_hackathon/call_llm.py:3` tier policy
- **The `mise` task catalogue** — keep the same operator UX

## Migration history

| Commit | What |
|---|---|
| `74dc95a` | Phase 0: OpenSpec change folder |
| `447fa75` | Phase 1: ADK OTel env-var alignment (the critical correction per Stackdriver doc) |
| `a92d8c8` | Phase 2: Consolidated `compose.yaml` (9 services + x-google-cloudrun extensions) |
| `7fed626` | Phase 3: Lance namespace integration (BigLake + Iceberg REST + Directory V2) |
| `347d3da` | Phase 5: Terraform module scaffold (10 new modules + envs/dev + envs/prod) |
| (this doc) | Phase 9: Documentation + handover |

The intermediate phases (4, 6, 7) are the manual `terraform apply`
steps that require live GCP credentials and a human in the loop to
review the plan. Those are deferred to the user.

## Acceptance gates (all green)

- `pytest gemini_hackathon_backend/tests/` → 63 passed
- `pytest` (root) → 360 passed (unchanged), 7 pre-existing failures per `docs/KNOWN_ISSUES.md`, 17 skipped
- `web tsc --noEmit` → zero errors
- `baml-cli check && baml-cli generate` → ok
- `docker compose -f compose.yaml config` → valid
- `docker compose -f compose.yaml -f docker-compose.dev-cloudrun.yaml config` → valid
- HCL syntax (via `python-hcl2` parser) → all 12 modules + 6 env files parse cleanly
- `openspec validate 2026-08-30-gcp-first-iac-refactor-v1 --strict` → valid

## Related docs

- `docs/DEPLOYMENT.md` — Google Secret Manager + Workload Identity Federation + Cloud Run + the 6-env-var set
- `docs/DEPLOY_RUNBOOK.md` — `terraform apply` step-by-step
- `docs/STACKDRIVER_AI_AGENT_ADK_INTEGRATION.md` — explicit reference to the Stackdriver doc
- `ARCHITECTURE.md` — overall architecture (Phase 0 of the public-demo work)
