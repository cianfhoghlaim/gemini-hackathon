# Spec Delta: gcp-infra (Phase 3 — GCP infrastructure completion)

This delta is applied by the OpenSpec change
[`2026-08-31-gcp-infra-secrets-v1`](../proposal.md). It describes
the **ADDED** Requirements to the canonical `gcp-infra` capability
that this change introduces.

## ADDED Requirements

### Requirement: All 12 Terraform modules SHALL be wired in envs/dev/main.tf
The system SHALL meet the requirement: All 12 Terraform modules SHALL be wired in envs/dev/main.tf.

The `cloud/terraform/envs/dev/main.tf` file SHALL instantiate every
module under `cloud/terraform/modules/`, in addition to the 4
already-wired modules (`observability_apis`,
`iam_gcp_ai_agent_adk`, `cloudrun_service` ×2,
`cloudrun_secret_mount` ×4). The 8 newly-wired modules are:
`cloudsql_postgres`, `memorystore_valkey`, `gcs_bucket`,
`bigquery_dataset`, `firestore_database`, `artifact_registry_repo`,
`workload_identity_gha`, `cloudbuild_trigger`.

Each module instantiation SHALL pass the canonical `project_id` and
`region` variables from `envs/dev/main.tf`. The
`cloudsql_postgres` module SHALL default `tier` to `db-f1-micro`
and `deletion_protection` to `false` for dev. The
`memorystore_valkey` module SHALL default `tier` to `STANDARD` and
`memory_size_gb` to `1`. The `gcs_bucket` module SHALL default
`location` to `europe-west1` and `uniform_bucket_level_access` to
`true`. The `bigquery_dataset` module SHALL default `location` to
`europe-west1` and `default_table_expiration_ms` to `0`. The
`firestore_database` module SHALL default `type` to `FIRESTORE_NATIVE`
and `location_id` to `eur3`. The `artifact_registry_repo` module
SHALL default `format` to `DOCKER`. The `workload_identity_gha`
module SHALL default `repo` to `cianmacandeisigh/gemini_hackathon`.
The `cloudbuild_trigger` module SHALL default `branch_name` to
`main` and `cloudbuild_yaml` to `cloudbuild.yaml`.

#### Scenario: terraform validate against cloud/terraform/envs/dev/
- **WHEN** the user runs `cd cloud/terraform/envs/dev && terraform init -backend=false && terraform validate`
- **THEN** validation passes (no errors, no unsupported-argument warnings)

### Requirement: Cloud Run v2 service identity SHALL be sourced from the iam module
The system SHALL meet the requirement: Cloud Run v2 service identity SHALL be sourced from the iam module.

The `cloud/terraform/cloud_run_adk.tf` resource
`google_cloud_run_v2_service.adk` SHALL set its `service_account`
field to the output of the `iam_gcp_ai_agent_adk` module, NOT a
hardcoded `${var.project_id}.iam.gserviceaccount.com` literal. The
output name SHALL be `email` (the canonical output of
`iam_gcp_ai_agent_adk`). The same contract SHALL apply to
`cloud_run_journey.tf` (the journey service account).

The legacy `cloud_run.tf` (Phase 0) SHALL retain its existing
`var.service_account` variable contract (which is already a `var`,
not hardcoded); only `cloud_run_adk.tf` + `cloud_run_journey.tf`
require the Phase 3 change.

#### Scenario: envs/dev apply-time wiring
- **WHEN** `terraform apply` runs against `cloud/terraform/envs/dev/`
- **THEN** the ADK Cloud Run service's `service_account` field equals `module.iam_adk.email`

### Requirement: cloudbuild.yaml SHALL use Cloud Run v2 deploy API
The system SHALL meet the requirement: cloudbuild.yaml SHALL use Cloud Run v2 deploy API.

The `cloudbuild.yaml` deploy step SHALL NOT use `gcloud run deploy`
(v1 API). Instead, it SHALL write a Cloud Run v2 manifest
(`cloud_run_adk_manifest.yaml`) to the build workspace and call
`gcloud run services replace <manifest> --region=$_REGION
--project=$PROJECT_ID`. The manifest SHALL declare the same image
URL + env vars + secret refs as the v1 deploy step.

#### Scenario: gcloud run services replace (Cloud Run v2)
- **WHEN** the Cloud Build pipeline deploys the backend
- **THEN** the deploy invocation is `gcloud run services replace
  cloud_run_adk_manifest.yaml --region=$_REGION
  --project=$PROJECT_ID`

### Requirement: Secrets loader contract SHALL be documented
The system SHALL meet the requirement: Secrets loader contract SHALL be documented.

The `.env.example` file SHALL document the 3 toggle env vars
consumed by `gemini_hackathon/secrets_loader.py`:
`ADK_LOAD_SECRETS` (opt-in; default `0`), `ADK_LOCAL_SECRETS`
(local-dev mode; default `1`), and `GCP_PROJECT` (the GCP project
for GSM lookups; default `agentic-hackathon-august-26`). The
`secrets.yaml` catalogue SHALL include 12 entries for the most-missed
env vars: `ADK_LOAD_SECRETS`, `ADK_LOCAL_SECRETS`, `GCP_PROJECT`,
`DEPLOYED_AGENT_ENGINE_ID`, `DOCUMENT_AI_LOCATION`,
`DOCUMENT_AI_PROCESSOR_ID`, `BIGQUERY_DATASET`, `GCS_BUCKET`,
`FIRESTORE_DATABASE_ID`, `OTEL_SERVICE_NAME`,
`CLOUD_RUN_SERVICE_URL`, `WORKLOAD_IDENTITY_PROVIDER`.

The `audit_gsm.py` script SHALL report 0 gaps
(`missing_in_gsm`, `orphan_in_gsm`, `dead_in_dotenv`) against
`secrets.yaml` ↔ `.env.example` after this change (the live API
check is deferred — no real GCP creds in Phase 3).

#### Scenario: audit_gsm with no real GCP creds
- **WHEN** the user runs `python scripts/audit_gsm.py --json`
  without GCP credentials
- **THEN** the output reports `missing_in_gsm: []`,
  `orphan_in_gsm: []`, `dead_in_dotenv: []`

### Requirement: Stitch upload SHALL fall back gracefully when API key absent
The system SHALL meet the requirement: Stitch upload SHALL fall back gracefully when API key absent.

The `functions/src/stitch.ts` `bootstrapDesignSystem` helper SHALL
attempt to call the (currently-fictional) `StitchClient.instances.create`
SDK when `STITCH_API_KEY` + `STITCH_PROJECT_ID` are set. When
either env var is unset, it SHALL log a warning
(`"STITCH_API_KEY not set — using stub IDs"`) and return
`{ instanceId: "stub", assetId: "stub" }`. The helper SHALL NOT
crash + bubble up an exception — the calling `/api/stitch` route
SHALL respond with HTTP 200 + the stub IDs.

#### Scenario: STITCH_API_KEY absent
- **WHEN** `process.env.STITCH_API_KEY` is undefined
- **THEN** `bootstrapDesignSystem` returns `{ instanceId: "stub", assetId: "stub" }`

### Requirement: Terraform plan CI workflow SHALL exist
The system SHALL meet the requirement: Terraform plan CI workflow SHALL exist.

The `.github/workflows/terraform-plan.yml` workflow SHALL trigger on
PRs touching `cloud/terraform/**`, pushes to `main` touching
`cloud/terraform/**`, and `workflow_dispatch`. The workflow SHALL
pin `hashicorp/setup-terraform@v3` to `terraform_version: 1.6.0`,
run `terraform init -backend=false` against
`cloud/terraform/envs/dev`, run `terraform validate -no-color`,
and run `terraform plan -no-color -input=false -lock=false` with
`TF_VAR_project_id=agentic-hackathon-august-26`. The plan step
SHALL have `continue-on-error: true` (the plan is informational;
the PR comment is the goal).

#### Scenario: PR opens against cloud/terraform/envs/dev/main.tf
- **WHEN** a contributor opens a PR adding a 13th Terraform module
- **THEN** the `terraform-plan` GitHub Actions workflow runs
  `terraform validate` + `terraform plan` and posts the plan output
