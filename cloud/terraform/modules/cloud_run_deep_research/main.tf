# ============================================================================
# cloud/terraform/modules/cloud_run_deep_research/main.tf
#
# The 12th Terraform module (NEW 2026-09-13 per the
# `2026-09-06-adk-gemini-deep-research-control-plane-v1` openspec change).
#
# Wraps the universal `cloudrun_service` module with deep-research-specific
# defaults:
#   - service_name  : "gemini-hackathon-deep-research"
#   - container_port: 8080 (matches the FastAPI app)
#   - min_instances : 0  (scale-to-zero when no traffic)
#   - max_instances : 3  (deep-research workloads are bursty; cap instances)
#   - memory        : 4Gi (deep-research runs long synthesis chains)
#   - cpu           : 2
#   - timeout       : 900s (15 minutes — covers long Gemini Deep Research runs)
#   - GOOGLE_API_KEY mounted via Secret Manager (NOT in env vars)
#
# The actual workload is the `gemini_hackathon_backend.agents.gemini_deep_research`
# module, served by a FastAPI app exposing `/deep-research` (POST).
#
# Why a discrete service (not just a route on the main `gemini-hackathon`
# Cloud Run):
#   1. Deep Research runs can take 5-15 minutes; isolating them prevents
#      long-lived requests from consuming the main service's concurrency
#      budget (which is shared with the NCCA panel chat).
#   2. Independent scaling: deep-research spikes independently of chat traffic.
#   3. Independent IAM: only the deep-research service needs the
#      `roles/aiplatform.user` role + the GOOGLE_API_KEY secret.
# ============================================================================

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "service_account" {
  description = "Service account email (created by iam_gcp_ai_agent_adk module)"
  type        = string
}

variable "image" {
  description = "Artifact Registry image URL (region-docker.pkg.dev/.../image:tag)"
  type        = string
}

variable "google_api_key_secret_id" {
  description = "Secret Manager secret ID for GOOGLE_API_KEY (the Gemini Deep Research API key)"
  type        = string
  default     = "google-api-key"
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default = {
    component     = "deep-research"
    managed-by    = "terraform"
    openspec-ref  = "2026-09-06-adk-gemini-deep-research-control-plane-v1"
  }
}

# Re-export the universal cloudrun_service module with deep-research defaults.
module "service" {
  source = "../cloudrun_service"

  project_id     = var.project_id
  service_name   = "gemini-hackathon-deep-research"
  image          = var.image
  region         = var.region
  service_account = var.service_account

  cpu            = "2"
  memory         = "4Gi"
  min_instances  = 0
  max_instances  = 3
  timeout_seconds = 900
  container_port  = 8080

  env_vars = {
    MODEL_PROFILE      = "hackathon"
    GEMINI_BACKEND     = "vertex"
    PYTHONUNBUFFERED   = "1"
    DEEP_RESEARCH_MODE = "enabled"
  }

  # Mount GOOGLE_API_KEY via Secret Manager — never baked into the image
  # or set as a plain env var (per the
  # `2026-09-06-adk-gemini-deep-research-control-plane-v1` spec scenario).
  secret_env_vars = {
    GOOGLE_API_KEY = var.google_api_key_secret_id
  }

  labels = var.labels
}

output "service_url" {
  description = "The deployed Cloud Run service URL"
  value       = module.service.service_url
}

output "service_name" {
  description = "The deployed Cloud Run service name"
  value       = module.service.service_name
}
