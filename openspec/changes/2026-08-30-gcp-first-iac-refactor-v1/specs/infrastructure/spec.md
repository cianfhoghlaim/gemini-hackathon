# Spec Delta: infrastructure (Phase 0 — IaC + container management)

This delta is applied by the OpenSpec change
[`2026-08-30-gcp-first-iac-refactor-v1`](../proposal.md). It describes the
**ADDED** Requirements to the canonical `infrastructure` capability
that this change adds.

## ADDED Requirements

### Requirement: GCP-native container management SHALL replace the bonneagar Komodo + Pangolin mesh

The system SHALL NOT depend on **Komodo** (orchestration daemon),
**Pangolin** (private-resource reverse proxy), or **Locket**
(secret-fetching sidecar). It SHALL use the GCP-native equivalents:

- **Cloud Build** for container image build + push to **Artifact Registry**
- **`gcloud run compose up compose.yaml`** for Cloud Run deploy (per the [official 2026 docs](https://docs.cloud.google.com/run/docs/deploy-run-compose))
- **Cloud Run `*.run.app` URLs** + **Cloud DNS** + **Cloud Armor** for ingress
- **Google Secret Manager** + **Workload Identity Federation** for secrets (no JSON keys)

#### Scenario: `docker compose config` validates the new `compose.yaml`

- **WHEN** `docker compose config` is run on the consolidated `compose.yaml`
- **THEN** the command SHALL exit 0 with no parse errors
- **AND** every service SHALL have the appropriate `x-google-cloudrun:` extensions

#### Scenario: `grep` finds zero references to the abandoned components

- **WHEN** `grep -rE "komodo|pangolin|locket" gemini_hackathon/cloud gemini_hackathon/docker-compose.yml` is run
- **THEN** the command SHALL return 0 matches

#### Scenario: `grep` finds zero references to Infisical in the prod Terraform

- **WHEN** `grep "infisical" gemini_hackathon/cloud/terraform/*.tf` is run
- **THEN** the command SHALL return 0 matches
- **AND** all secrets SHALL be referenced via `google_secret_manager_secret` + `value_from.secret_key_ref`

### Requirement: The 4 NEW gemini-hackathon stacks SHALL be deployed via Terraform modules

The system SHALL provide a `cloud/terraform/modules/` directory with the
canonical 11 reusable modules:

- `cloudrun_service` (universal — used by all 4 NEW stacks)
- `cloudrun_secret_mount` (Secret Manager → volume)
- `cloudsql_postgres` (Postgres with 13 DBs)
- `memorystore_valkey` (Standard M2, 5 GB)
- `gcs_bucket` (per-stack with lifecycle to Nearline)
- `bigquery_dataset` (per-domain)
- `firestore_database` (Native mode)
- `artifact_registry_repo` (per-project)
- `workload_identity_gha` (GitHub Actions OIDC)
- `cloudbuild_trigger` (per-stack)
- `iam_gcp_ai_agent_adk` (the 4 IAM roles for ADK OTel)

#### Scenario: `terraform validate` succeeds

- **WHEN** `cd cloud/terraform/envs/dev && terraform init && terraform validate` is run
- **THEN** the command SHALL exit 0
- **AND** the 11 modules SHALL be referenced by `envs/dev/main.tf`

### Requirement: Three deployment targets, one `compose.yaml`

The system SHALL provide a single `compose.yaml` (replacing the
separate `docker-compose.yml` + `docker-compose.local.yaml`) that
supports three deployment targets:

- **Local dev**: `docker compose up --build` (boots app + Langfuse + MLflow + lakehouse on the dev machine)
- **Dev Cloud Run**: `gcloud run compose up compose.yaml --project=$DEV_PROJECT --region=europe-west1 --max-instances=10` (boots just the app service on Cloud Run; Langfuse + MLflow + lakehouse stay on the dev machine)
- **Prod Cloud Run**: `terraform apply` from `cloud/terraform/envs/prod/` (provisions the full GCP-native equivalents)

#### Scenario: `gcloud run compose up` succeeds on a dev Cloud Run project

- **WHEN** the user runs `gcloud run compose up compose.yaml --project=$DEV_PROJECT --region=europe-west1`
- **THEN** the command SHALL deploy a single Cloud Run service with the `gemini-hackathon-backend` container + the `llama-swap` sidecar
- **AND** the service SHALL be reachable at `https://gemini-hackathon-adk-$HASH.europe-west1.run.app`
- **AND** the `/healthz` endpoint SHALL return the 5-key observability state
