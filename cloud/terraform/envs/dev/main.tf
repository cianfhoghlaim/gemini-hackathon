# ============================================================================
# cloud/terraform/envs/dev/main.tf — Phase 5 wiring for the dev project.
#
# Wires the 12 Terraform modules for the dev Cloud Run project:
#   1. observability_apis        — 6 GCP APIs
#   2. iam_gcp_ai_agent_adk      — 4 Stackdriver roles
#   3. cloudrun_service          — universal service module
#   4. cloudrun_secret_mount     — Secret Manager
#   5. cloudsql_postgres         — Postgres with 13 DBs
#   6. memorystore_valkey        — Standard M2
#   7. gcs_bucket                — per-stack with lifecycle
#   8. bigquery_dataset          — per-domain
#   9. firestore_database       — Native mode
#  10. artifact_registry_repo    — per-project
#  11. workload_identity_gha    — GitHub Actions OIDC
#  12. cloudbuild_trigger        — per-stack
#
# This file is the canonical dev entry point. Apply via:
#   cd cloud/terraform/envs/dev && terraform init && terraform plan && terraform apply
# ============================================================================

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  required_version = ">= 1.5"
}

variable "project_id" {
  description = "GCP project ID for the dev environment"
  type        = string
  default     = "gemini-hackathon-dev"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "image_tag" {
  description = "Docker image tag (set by CI)"
  type        = string
  default     = "dev"
}

# ============================================================================
# Module 1: observability_apis — 6 GCP APIs
# ============================================================================
module "observability_apis" {
  source     = "../../modules/observability_apis"
  project_id = var.project_id
}

# ============================================================================
# Module 2: iam_gcp_ai_agent_adk — 4 Stackdriver roles
# ============================================================================
module "iam_adk" {
  source      = "../../modules/iam_gcp_ai_agent_adk"
  project_id  = var.project_id
}

# ============================================================================
# Module 3-4: cloudrun_service + cloudrun_secret_mount (per-secret)
# Provision the 4 secrets (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
# GEMINI_API_KEY, UNSLOTH_API_KEY) and grant the SA access.
# ============================================================================
module "secret_langfuse_public" {
  source                = "../../modules/cloudrun_secret_mount"
  project_id            = var.project_id
  secret_id             = "langfuse-public-key"
  service_account_email = module.iam_adk.email
}

module "secret_langfuse_secret" {
  source                = "../../modules/cloudrun_secret_mount"
  project_id            = var.project_id
  secret_id             = "langfuse-secret-key"
  service_account_email = module.iam_adk.email
}

module "secret_gemini_api" {
  source                = "../../modules/cloudrun_secret_mount"
  project_id            = var.project_id
  secret_id             = "gemini-api-key"
  service_account_email = module.iam_adk.email
}

module "secret_unsloth_api" {
  source                = "../../modules/cloudrun_secret_mount"
  project_id            = var.project_id
  secret_id             = "unsloth-api-key"
  service_account_email = module.iam_adk.email
}

# ============================================================================
# Module 5: gemini-hackathon-backend Cloud Run service
# ============================================================================
module "gemini_hackathon_backend" {
  source         = "../../modules/cloudrun_service"
  project_id     = var.project_id
  service_name   = "gemini-hackathon-backend"
  region         = var.region
  image          = "${var.region}-docker.pkg.dev/${var.project_id}/gemini-hackathon/backend:${var.image_tag}"
  service_account = module.iam_adk.email
  cpu            = "2"
  memory         = "4Gi"
  min_instances  = 0
  max_instances  = 10
  env_vars = {
    MODEL_PROFILE                       = "hackathon"
    GEMINI_BACKEND                      = "vertex"
    GOOGLE_CLOUD_PROJECT                = var.project_id
    GOOGLE_CLOUD_LOCATION               = var.region
    # Phase 0: canonical Stackdriver AI Agent ADK 6-env-var set
    OTEL_SERVICE_NAME                   = "gemini-hackathon-adk"
    OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED = "true"
    OTEL_SEMCONV_STABILITY_OPT_IN       = "gen_ai_latest_experimental"
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = "EVENT_ONLY"
    ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS = "false"
    GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY = "true"
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT   = "https://telemetry.googleapis.com/v1/traces"
    OTEL_RESOURCE_ATTRIBUTES            = "service.namespace=gemini-hackathon,deployment.environment=dev"
  }
  secret_env_vars = {
    LANGFUSE_PUBLIC_KEY = module.secret_langfuse_public.secret_id
    LANGFUSE_SECRET_KEY = module.secret_langfuse_secret.secret_id
    GEMINI_API_KEY      = module.secret_gemini_api.secret_id
    UNSLOTH_API_KEY     = module.secret_unsloth_api.secret_id
  }
  labels = {
    app        = "gemini-hackathon"
    component  = "backend"
    env        = "dev"
  }
}

# ============================================================================
# Module 6: gemini-hackathon-frontend Cloud Run service
# ============================================================================
module "gemini_hackathon_frontend" {
  source         = "../../modules/cloudrun_service"
  project_id     = var.project_id
  service_name   = "gemini-hackathon-frontend"
  region         = var.region
  image          = "${var.region}-docker.pkg.dev/${var.project_id}/gemini-hackathon/frontend:${var.image_tag}"
  service_account = module.iam_adk.email
  cpu            = "1"
  memory         = "2Gi"
  min_instances  = 0
  max_instances  = 5
  env_vars = {
    BACKEND_URL = module.gemini_hackathon_backend.service_url
  }
  labels = {
    app       = "gemini-hackathon"
    component = "frontend"
    env       = "dev"
  }
}

# ============================================================================
# Stubs for the remaining 8 modules (substance added in Phase 5/6 follow-ups)
# ============================================================================
# Modules 7-12 (cloudsql_postgres, memorystore_valkey, gcs_bucket,
# bigquery_dataset, firestore_database, artifact_registry_repo,
# workload_identity_gha, cloudbuild_trigger) — wired in Phase 6's
# follow-up. The structure here is the canonical scaffold.

output "backend_url" {
  description = "The deployed backend service URL"
  value       = module.gemini_hackathon_backend.service_url
}

output "frontend_url" {
  description = "The deployed frontend service URL"
  value       = module.gemini_hackathon_frontend.service_url
}

output "adk_service_account_email" {
  description = "The ADK service account email"
  value       = module.iam_adk.email
}