# 2026-08-30-gcp-first-iac-refactor-v1

> **Phase 0 of the GCP-first infrastructure refactor for `gemini_hackathon`
> (see AGENTS.md).** Replaces the Oracle Cloud free tier + the
> `biiep-hackathon-2026-08-31/bonneagar` Komodo + Pangolin + Locket +
> Infisical IaC pattern with **GCP-native Cloud Run + Terraform modules
> + Google Secret Manager + Workload Identity Federation**, while
> keeping the `stacks/{langfuse,mlflow,lakehouse}` self-hosted
> docker-compose stack for **local dev only**.

## Why

The previous `bonneagar/` infrastructure (the upstream Cianfhoghlaim
89-stack IaC mesh) used four non-GCP components — **Komodo**
(orchestration daemon), **Pangolin** (private-resource gateway),
**Locket** (secret-fetching sidecar), and **Infisical** (multi-tenant
secret backend). They made sense when the only hosting target was the
Oracle Cloud free tier + a MacBook M4 Max + Hetzner; they do not make
sense on GCP, where managed equivalents (`Cloud Build`, `Cloud Run`
URLs, `Secret Manager` volume mounts, `Workload Identity Federation`)
exist out of the box.

The Gemini Hackathon parallel work in this repo has already moved most
of the application to the canonical ADK 2 + Cloud Run substrate
(`gemini_hackathon_backend/`, `cloud/terraform/cloud_run_adk.tf`,
`docker-compose.local.yaml`). What remains is the IaC reorg that drops
the 4 non-GCP components, replaces them with the GCP-native equivalents,
and adopts the **canonical Stackdriver AI Agent ADK instrumentation**
([docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk](https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk))
that Google recommends for ADK 2 agents as of 2026-08-26.

User direction (2026-08-30):
1. **Keep the local docker-compose stack for Langfuse + MLflow** as
   the dev environment. Do NOT move Langfuse to Langfuse Cloud and do
   NOT replace MLflow with Vertex AI Experiments.
2. **Scope: just the 4 NEW gemini-hackathon stacks** (backend,
   frontend, observability, lakehouse) per `AGENTS.md:56-66`, plus the
   3 closely-related bonneagar stacks (langfuse, mlflow, lakehouse).
   NOT the 89 wholesale-copied cianfhoghlaim stacks.

## What changes

### A — Drop the 4 non-GCP components

- **Komodo** (orchestration daemon) → **Cloud Build** + `gcloud run compose up`
- **Pangolin** (reverse proxy) → **Cloud Run `*.run.app` URLs** + **Cloud DNS** + **Cloud Armor**
- **Locket** (sidecar secret fetcher) → **Google Secret Manager volume mounts** on Cloud Run
- **Infisical** (multi-tenant secret backend) → **Google Secret Manager + Workload Identity Federation**

### B — Switch from `get_gcp_exporters` to the OTLP path (canonical 2026)

The current `gemini_hackathon_backend/observability.py` (Phase 1 of
the prior session) uses `google.adk.telemetry.google_cloud.get_gcp_exporters()`.
The canonical 2026 GCP-native path per the Stackdriver AI Agent ADK
doc is the **OTLP exporter** to the unified **Telemetry (OTLP) API**.

Required package changes in `gemini_hackathon_backend/pyproject.toml`:
```
# Add
"opentelemetry-instrumentation-google-genai>=0.4b0",
"opentelemetry-instrumentation-vertexai>=2.0b0",
"opentelemetry-exporter-otlp-proto-grpc>=1.27",
"opentelemetry-instrumentation-sqlite3>=0.41b0",
# Keep the existing
"opentelemetry-exporter-gcp-logging>=1.9.0",
"openinference-instrumentation-google-adk>=0.1.0",
```

Required env vars (replaces the current 4-var set with the canonical 6-var set per the Stackdriver doc):
```
OTEL_SERVICE_NAME='gemini-hackathon-adk'
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED='true'
OTEL_SEMCONV_STABILITY_OPT_IN='gen_ai_latest_experimental'
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT='EVENT_ONLY'
ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS='false'
GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY='true'
```

Required APIs:
```
gcloud services enable aiplatform.googleapis.com \
  serviceusage.googleapis.com \
  telemetry.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudtrace.googleapis.com
```

Required IAM roles (new Terraform module `cloud/terraform/modules/iam_gcp_ai_agent_adk`):
- `roles/telemetry.tracesWriter`
- `roles/logging.logWriter`
- `roles/monitoring.metricWriter`
- `roles/aiplatform.user`

### C — Lakehouse (Lance namespace + BigLake)

- Add `lance-namespace` (Apache 2.0) to `pyproject.toml`
- New `gemini_hackathon_backend/lakehouse/namespace.py`:
  - `lance.connect("dir", root=...)` for local dev
  - `lance.connect("iceberg", ...)` for prod (BigLake Iceberg REST)
- Wrap `cocoindex_flows/_shared/_vector_target.py` to mount the namespace when `LANCE_NAMESPACE_BACKEND` is set

### D — Consolidated `compose.yaml`

Merge `docker-compose.yml` (app + llama-swap + duckdb) with
`docker-compose.local.yaml` (Langfuse v3 + MLflow v2.20) into a single
`compose.yaml` with `x-google-cloudrun:` extensions. The 6-service
Langfuse + MLflow stack stays in `compose.yaml` for local dev (per
user direction).

### E — Terraform modules

`cloud/terraform/modules/` with 11 modules:
`cloudrun_service`, `cloudrun_secret_mount`, `cloudsql_postgres`,
`memorystore_valkey`, `gcs_bucket`, `bigquery_dataset`,
`firestore_database`, `artifact_registry_repo`, `workload_identity_gha`,
`cloudbuild_trigger`, `iam_gcp_ai_agent_adk`.

`cloud/terraform/envs/{dev,prod}/` — wiring files per env.

## Acceptance

- `grep -rE "komodo|pangolin|locket" gemini_hackathon/cloud gemini_hackathon/docker-compose.yml` returns 0 matches
- `grep "infisical" gemini_hackathon/cloud/terraform/*.tf` returns 0 matches
- `gemini_hackathon_backend/observability.py:try_init_adk_otel()` uses `opentelemetry-exporter-otlp-proto-grpc` (NOT `get_gcp_exporters`)
- All 6 Stackdriver env vars are setdefault'd
- `compose.yaml` (single file) has `x-google-cloudrun:` extensions
- `docker compose config` validates
- `pytest gemini_hackathon_backend/tests/` passes 19 → 27 → 35 (incrementally per phase)
- `mise run lint && mise run py:typecheck && mise run turbo typecheck` green
- `web tsc --noEmit` zero errors
- `openspec validate 2026-08-30-gcp-first-iac-refactor-v1 --strict` passes

## Dependencies

- **Blocked by:** nothing (the prior 9 phases are merged to main).
- **Unblocks:** nothing (this is the wrap-up of the multi-stage work).
- **Cross-repo:** the upstream cianfhoghlaim monorepo's bonneagar/ is unchanged.

## Compatibility

- **Local dev**: `docker compose up` boots the full stack.
- **Dev Cloud Run**: `gcloud run compose up compose.yaml` deploys the application service. Langfuse + MLflow + lakehouse remain on the dev machine.
- **Prod Cloud Run**: `terraform apply` from `cloud/terraform/envs/prod/` provisions the GCP-native equivalents.
- **No code changes required** for the user-facing APIs: only env vars + Python deps change.
