# 2026-08-31-gcp-infra-secrets-v1

> **Phase 3 of the gemini_hackathon polish plan.** Completes the
> GCP infrastructure layer started by Phase 0
> (`2026-08-30-gcp-first-iac-refactor-v1`). Six concrete sub-tasks:
> 1. Wire the 6 remaining stub Terraform modules in
>   `cloud/terraform/envs/dev/main.tf`.
> 2. Replace 3 hardcoded service-account references with module outputs.
> 3. Migrate `cloudbuild.yaml` from Cloud Run v1 (`gcloud run deploy`)
>   to Cloud Run v2 (`gcloud run services replace`).
> 4. Document the secrets-loader contract (`ADK_LOAD_SECRETS` /
>   `ADK_LOCAL_SECRETS` + 12 new catalogue entries).
> 5. Restore the real Stitch upload logic in
>   `functions/src/stitch.ts` (currently returns literal `"stub"`).
> 6. Add a `terraform-plan` GitHub Actions workflow.

Phases 0-2 fixed critical bugs + wired the local + GCP data plane
code paths. This change completes the **infrastructure layer** so the
deploy path can stand up the full project surface (12 Terraform
modules + GSM-loaded env vars + Cloud Build v2 + Stitch upload + CI
terraform-plan gate).

## Why

Per Phase 2's handover, 6 of 12 Terraform modules were stubbed — the
`envs/dev/main.tf` only wires `observability_apis`,
`iam_gcp_ai_agent_adk`, `cloudrun_service` (×2 invocations), and
`cloudrun_secret_mount` (×4 invocations). The remaining 6 modules
(`cloudsql_postgres`, `memorystore_valkey`, `gcs_bucket`,
`bigquery_dataset`, `firestore_database`, `artifact_registry_repo`)
plus `workload_identity_gha` and `cloudbuild_trigger` have empty
`main.tf` files — the `module_id` output only.

The Cloud Build deploy step uses `gcloud run deploy` (v1 API),
which is deprecated for `google_cloud_run_v2_service` (the Terraform
resource). The `cloud_run_adk.tf:266` hardcoded service-account
email must come from the `iam_gcp_ai_agent_adk` module output.

The secrets loader (`gemini_hackathon/secrets_loader.py`) honours
`ADK_LOAD_SECRETS` / `ADK_LOCAL_SECRETS` but these two toggles are
not documented in `.env.example` or in `secrets.yaml`. 12 of the 27
env vars read by the application have no `gsm_secret_id` entry.

The Stitch upload (`functions/src/stitch.ts`) is stubbed — the
intended production code path that calls
`stitch.instances.create({ sourceMd })` is replaced by a hardcoded
`return { instanceId: "stub", assetId: "stub" }`. When the Google
Stitch SDK ships (post-2026-08), the function should call it.

No CI workflow validates Terraform changes — a single HCL typo in
`cloud/terraform/envs/dev/main.tf` would only surface at `terraform
apply` time, after the `main` branch is already broken.

## What Changes

- **NEW** `cloud/terraform/envs/dev/main.tf` — 8 module instantiations
  added (Phase 3.1): `cloudsql_postgres`, `memorystore_valkey`,
  `gcs_bucket`, `bigquery_dataset`, `firestore_database`,
  `artifact_registry_repo`, `workload_identity_gha`, `cloudbuild_trigger`.
- **NEW** `cloud/terraform/cloud_run_adk.tf:266` references the
  `module.iam_adk.email` output (Phase 3.2). The legacy
  `cloud_run.tf` + `cloud_run_journey.tf` also lose their
  hardcoded `service_account` lines in favour of the module output.
- **MODIFIED** `cloudbuild.yaml` deploy step rewritten as Cloud Run
  v2 (Phase 3.3) — uses `gcloud run services replace
  manifest.yaml --region=$_REGION` with the manifest written by
  the previous step.
- **MODIFIED** `.env.example` gains the 2-toggles + `GCP_PROJECT`
  block at the top.
- **MODIFIED** `secrets.yaml` gains 12 new entries (Phase 3.4):
  `ADK_LOAD_SECRETS`, `ADK_LOCAL_SECRETS`, `GCP_PROJECT`,
  `DEPLOYED_AGENT_ENGINE_ID`, `DOCUMENT_AI_LOCATION`,
  `DOCUMENT_AI_PROCESSOR_ID`, `BIGQUERY_DATASET`, `GCS_BUCKET`,
  `FIRESTORE_DATABASE_ID`, `OTEL_SERVICE_NAME`,
  `CLOUD_RUN_SERVICE_URL`, `WORKLOAD_IDENTITY_PROVIDER`.
- **MODIFIED** `functions/src/stitch.ts` — the `bootstrapDesignSystem`
  helper tries the real `StitchClient.instances.create` call when
  `STITCH_API_KEY` is set; falls back to the stub IDs otherwise
  (Phase 3.5).
- **NEW** `functions/test/stitch.test.ts` (Phase 3.5) — Node `node:test`
  coverage of the stub fallback + the real-call branch.
- **NEW** `tests/test_secrets_loader_env.py` — `pytest` coverage of
  the 2 toggles (local-mode vs GSM-mode + ADK_LOAD_SECRETS opt-in).
- **NEW** `tests/test_audit_gsm.py` — `pytest` coverage of the audit
  logic against a mocked `SecretManagerServiceClient`.
- **NEW** `.github/workflows/terraform-plan.yml` (Phase 3.6) —
  `terraform init -backend=false` + `terraform validate` +
  `terraform plan` on every PR touching `cloud/terraform/**`.
- **NEW** `docs/IAC.md` §9 "All 12 modules wired" — describes the
  final state of the IaC surface.
- **NEW** `docs/KNOWN_ISSUES.md` entry — Terraform 1.6+ required
  (the CI workflow pins `terraform_version: 1.6.0`).

## Impact

- **Affected specs**: 1 capability delta (`gcp-infra`).
- **Affected code**: 4 Terraform files, 1 YAML, 1 TypeScript, 1 Python
  secrets YAML, 1 dotenv example, 1 CI workflow, 3 new test files.
- **Affected deployments**: this change has NO production impact —
  all edits are inside Cloud Build + Terraform + secrets loader code
  paths, not the data plane. The deploy-time GCP resources are
  unchanged (still provisioned by `terraform apply` against
  `cloud/terraform/envs/{dev,prod}/`).
- **Phase 4-5 surfaces** (`gemini_hackathon_gradio/`, `web/`,
  `hf_spaces/`) are explicitly out of scope.

## Dependencies

- Phase 0 (`603637c` + `d7d0f3e`) — unblocked `uv sync --all-extras`.
- Phase 1 (`d1ef175`) — wired the local data plane.
- Phase 2 (`57fe477`) — added the GCP data plane destinations.
- `secrets-management` skill (`.agents/skills/secrets-management/`)
  documents the canonical GSM + WIF contract this change extends.
- `openspec` skill (`.agents/skills/openspec/`) for the change
  validation flow.

## Acceptance gates

- `pytest tests/` shows ≥383 passed (381 Phase 2 baseline + 2 new).
- `bash scripts/verify.sh` stays ≥6/8 green (no regressions).
- `terraform validate` against `cloud/terraform/envs/dev/` passes
  (init + validate work without GCP credentials).
- `python scripts/audit_gsm.py --json` shows 0 `missing_in_gsm` /
  `orphan_in_gsm` / `dead_in_dotenv` against the current
  `secrets.yaml` ↔ `.env.example` (the live API check is deferred
  to the user — Phase 3 has no real GSM creds).
- `openspec validate 2026-08-31-gcp-infra-secrets-v1 --strict` passes.
- `cd functions && npm test` passes (Node 20+ required).
