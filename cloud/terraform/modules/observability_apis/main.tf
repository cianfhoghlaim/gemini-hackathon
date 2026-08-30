# ============================================================================
# cloud/terraform/modules/observability_apis/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the 6 GCP APIs required by the
# Stackdriver AI Agent ADK instrumentation pipeline per
# https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk
# (last updated 2026-08-26).
#
# APIs:
#   - aiplatform.googleapis.com       (Vertex AI)
#   - serviceusage.googleapis.com     (Service Usage — required to enable others)
#   - telemetry.googleapis.com        (unified Telemetry API - the canonical 2026 endpoint)
#   - logging.googleapis.com          (Cloud Logging)
#   - monitoring.googleapis.com       (Cloud Monitoring)
#   - cloudtrace.googleapis.com       (Cloud Trace — legacy, kept for compat)
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

locals {
  observability_apis = toset([
    "aiplatform.googleapis.com",
    "serviceusage.googleapis.com",
    "telemetry.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
  ])
}

resource "google_project_service" "observability" {
  for_each                   = local.observability_apis
  project                    = var.project_id
  service                    = each.value
  disable_dependent_services = false
  disable_on_destroy         = false
}

output "enabled_apis" {
  description = "The 6 observability APIs enabled on the project"
  value       = sort(local.observability_apis)
}