# Tasks for 2026-08-30-gcp-first-iac-refactor-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-30-gcp-first-iac-refactor-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/{infrastructure,observability,lakehouse}/spec.md` (3 spec deltas)
- [x] T0.3: `openspec validate 2026-08-30-gcp-first-iac-refactor-v1 --strict` passes
- [ ] T0.4: git commit + git push origin main

## Phase 1 — ADK OTel env-var alignment (per the Stackdriver AI Agent ADK doc)
- [x] T1.1: `gemini_hackathon_backend/pyproject.toml` — add 4 new OTel deps
- [x] T1.2: `gemini_hackathon_backend/observability.py` — rewrite `try_init_adk_otel()` to use the OTLP path
  - Replace `get_gcp_exporters` with `OTLPSpanExporter(endpoint="...telemetry.googleapis.com...")`
  - Setdefault the 6 Stackdriver env vars
  - Keep the OpenInference Langfuse dual-export as-is
- [x] T1.3: `cloud/terraform/cloud_run_adk.tf` — replace the 4 env vars with the full 6-var set
- [x] T1.4: New `cloud/terraform/modules/iam_gcp_ai_agent_adk/main.tf` — service account + 4 IAM roles
- [x] T1.5: `cloud_run_adk.tf` — bind the new service account to the existing ADK Cloud Run service
- [x] T1.6: `cloud_run_adk.tf` — add the 6th API `telemetry.googleapis.com` to `google_project_service.observability`
- [x] T1.7: `gemini_hackathon_backend/tests/test_observability_init.py` — update the 6-var assertions
- [x] T1.8: New `gemini_hackathon_backend/tests/test_stackdriver_envvars.py` — 4 tests verifying the 6 env vars are setdefault'd + the IAM role set is correct
- [x] T1.9: pytest 27 → 31; `web tsc --noEmit` zero errors
- [x] T1.10: git commit + git push

## Phase 2 — Consolidated `compose.yaml` (one file, three targets)
- [x] T2.1: Merge `docker-compose.yml` + `docker-compose.local.yaml` into a single `compose.yaml` with `x-google-cloudrun:` extensions
- [x] T2.2: Drop the (currently empty) `infra/stacks/` directory
- [x] T2.3: `docker compose config` validates
- [x] T2.4: `gcloud run compose up compose.yaml --dry-run` (local dry-run) succeeds
- [x] T2.5: New `docker-compose.dev-cloudrun.yaml` override (the Secret Manager + WIF env var injection for dev Cloud Run)
- [x] T2.6: pytest 31 → 31 (no test count change); `web tsc --noEmit` zero errors
- [x] T2.7: git commit + git push

## Phase 3 — Lance namespace integration
- [x] T3.1: `pyproject.toml` — add `lance-namespace>=0.4` (Apache 2.0)
- [x] T3.2: New `gemini_hackathon_backend/lakehouse/namespace.py`:
  - `connect_lance_namespace(backend: str, ...)` factory
  - Backends: `"dir"` (dev), `"iceberg"` (prod/BigLake)
  - The `lance.connect(...)` call is the canonical entry point
- [x] T3.3: Wrap `cocoindex_flows/_shared/_vector_target.py` to mount the namespace when `LANCE_NAMESPACE_BACKEND` is set
- [x] T3.4: New `gemini_hackathon_backend/tests/test_lance_namespace_e2e.py` — write + read via the dev Directory backend
- [x] T3.5: `gemini_hackathon_backend/tests/test_lance_namespace_e2e.py` — verify the BigLake Iceberg URL is built correctly (mocked, no actual network)
- [x] T3.6: pytest 31 → 35
- [x] T3.7: git commit + git push

## Phase 4 — GCP service enablement + IAM (1 PR, manual)
- [x] T4.1: New `cloud/terraform/modules/observability_apis/main.tf` — 6 `google_project_service` resources
- [x] T4.2: New `cloud/terraform/modules/iam_gcp_ai_agent_adk/main.tf` — service account + 4 IAM roles + WIF pool
- [x] T4.3: `cloud/terraform/envs/dev/main.tf` — wire the 2 new modules
- [x] T4.4: pytest 35 → 35; `terraform validate` (no actual apply)
- [x] T4.5: git commit + git push

## Phase 5 — Terraform module scaffold (1 PR)
- [x] T5.1: 11 new Terraform module directories under `cloud/terraform/modules/`
- [x] T5.2: `cloud/terraform/envs/dev/main.tf` — wire the 11 modules for the dev project
- [x] T5.3: `cloud/terraform/envs/prod/main.tf` — wire the 11 modules for the prod project
- [x] T5.4: `terraform validate` (no actual apply)
- [x] T5.5: git commit + git push

## Phase 6 — `envs/dev/` apply (1 PR, manual `terraform apply` — DEFERRED to user)
- [ ] T6.1: `cd cloud/terraform/envs/dev && terraform init && terraform plan`
- [ ] T6.2: Manual `terraform apply` (gated; user reviews the plan first)
- [ ] T6.3: `curl $BACKEND_URL/healthz | jq .` returns 5-key observability state
- [ ] T6.4: `gcloud services list --enabled` shows the 6 APIs
- [ ] T6.5: git commit + git push

## Phase 7 — Production promotion gates (1 PR — DEFERRED to user)
- [ ] T7.1: `cloud/terraform/envs/prod/main.tf` — Memorystore Standard M3, Cloud SQL Enterprise HA, `min-instances=1`, IAP on frontend
- [ ] T7.2: `terraform plan` returns 0 unexpected diffs
- [ ] T7.3: Cloud Armor WAF policy reviewed
- [ ] T7.4: Secrets Manager IAM reviewed
- [ ] T7.5: Workload Identity Federation pool reviewed
- [ ] T7.6: git commit + git push

## Phase 8 — End-to-end observability verification (1 PR)
- [x] T8.1: New `gemini_hackathon_backend/tests/test_gcp_observability_e2e.py`:
  - `try_init_adk_otel()` returns non-None when `GCP_PROJECT_ID` is set
  - The 6 Stackdriver env vars are setdefault'd
  - The 5-key state dict is stable + includes `adk_otel`
  - Langfuse dual-export config is correct when `LANGFUSE_BASE_URL` is set
- [x] T8.2: New `tests/integration/test_full_pipeline.py`:
  - Read 1 BI source PDF → extract via 5 BAML functions → upsert to Lance namespace → emit observability events
  - Asserts every step lands in Cloud Trace + Cloud Logging + (when configured) Langfuse
- [x] T8.3: pytest 35 → 39
- [x] T8.4: git commit + git push

## Phase 9 — Documentation + handover (1 PR)
- [x] T9.1: New `docs/IAC.md` — replaces the bonneagar IaC docs
- [x] T9.2: `docs/DEPLOYMENT.md` — Google Secret Manager + WIF + Cloud Run + the 6-env-var set
- [x] T9.3: New `docs/DEPLOY_RUNBOOK.md` — `terraform apply` step-by-step
- [x] T9.4: New `docs/STACKDRIVER_AI_AGENT_ADK_INTEGRATION.md` — reference to the Stackdriver doc + the 6 env vars + the 4 IAM roles + the sample
- [x] T9.5: `ARCHITECTURE.md` — update with the GCP-native refactor
- [x] T9.6: `README.md` — link to the 4 NEW deployment docs
- [x] T9.7: git commit + git push

## Phase validation
- [ ] V1: `pytest` (root) — no new failures; 7 pre-existing failures per `docs/KNOWN_ISSUES.md` stay at 7
- [ ] V2: `web tsc --noEmit` — zero errors
- [ ] V3: `baml-cli check && baml-cli generate` — ok
- [ ] V4: `openspec archive 2026-08-30-gcp-first-iac-refactor-v1 --yes` (after deploy)
