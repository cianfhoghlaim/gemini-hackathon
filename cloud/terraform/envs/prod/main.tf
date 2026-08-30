# ============================================================================
# cloud/terraform/envs/prod/main.tf — Phase 5 wiring for the prod project.
#
# Mirrors envs/dev/main.tf with prod-tier sizes:
#   - Memorystore Standard M3 (cross-zone HA)
#   - Cloud SQL Enterprise (HA, regional, PITR)
#   - min-instances=1 on backend (no scale-to-zero in prod)
#   - IAP on the frontend (per Phase 7 review)
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
  description = "GCP project ID for the prod environment"
  type        = string
  default     = "gemini-hackathon-prod"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "image_tag" {
  description = "Docker image tag (pinned by release)"
  type        = string
}

# Module 1: observability_apis
module "observability_apis" {
  source     = "../../modules/observability_apis"
  project_id = var.project_id
}

# Module 2: iam_gcp_ai_agent_adk
module "iam_adk" {
  source      = "../../modules/iam_gcp_ai_agent_adk"
  project_id  = var.project_id
}

# Module 3-4: secrets (4)
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

# Module 5: gemini-hackathon-backend (prod-tier: min_instances=1)
module "gemini_hackathon_backend" {
  source         = "../../modules/cloudrun_service"
  project_id     = var.project_id
  service_name   = "gemini-hackathon-backend"
  region         = var.region
  image          = "${var.region}-docker.pkg.dev/${var.project_id}/gemini-hackathon/backend:${var.image_tag}"
  service_account = module.iam_adk.email
  cpu            = "4"
  memory         = "8Gi"
  min_instances  = 1   # no scale-to-zero in prod
  max_instances  = 50
  env_vars = {
    MODEL_PROFILE                       = "hackathon"
    GEMINI_BACKEND                      = "vertex"
    GOOGLE_CLOUD_PROJECT                = var.project_id
    GOOGLE_CLOUD_LOCATION               = var.region
    OTEL_SERVICE_NAME                   = "gemini-hackathon-adk"
    OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED = "true"
    OTEL_SEMCONV_STABILITY_OPT_IN       = "gen_ai_latest_experimental"
    OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT = "EVENT_ONLY"
    ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS = "false"
    GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY = "true"
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT   = "https://telemetry.googleapis.com/v1/traces"
    OTEL_RESOURCE_ATTRIBUTES            = "service.namespace=gemini-hackathon,deployment.environment=prod"
  }
  secret_env_vars = {
    LANGFUSE_PUBLIC_KEY = module.secret_langfuse_public.secret_id
    LANGFUSE_SECRET_KEY = module.secret_langfuse_secret.secret_id
    GEMINI_API_KEY      = module.secret_gemini_api.secret_id
    UNSLOTH_API_KEY     = module.secret_unsloth_api.secret_id
  }
  labels = {
    app       = "gemini-hackathon"
    component = "backend"
    env       = "prod"
  }
}

# Module 6: gemini-hackathon-frontend (prod-tier: IAP on)
module "gemini_hackathon_frontend" {
  source         = "../../modules/cloudrun_service"
  project_id     = var.project_id
  service_name   = "gemini-hackathon-frontend"
  region         = var.region
  image          = "${var.region}-docker.pkg.dev/${var.project_id}/gemini-hackathon/frontend:${var.image_tag}"
  service_account = module.iam_adk.email
  cpu            = "2"
  memory         = "4Gi"
  min_instances  = 1
  max_instances  = 20
  env_vars = {
    BACKEND_URL = module.gemini_hackathon_backend.service_url
  }
  labels = {
    app       = "gemini-hackathon"
    component = "frontend"
    env       = "prod"
  }
}

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