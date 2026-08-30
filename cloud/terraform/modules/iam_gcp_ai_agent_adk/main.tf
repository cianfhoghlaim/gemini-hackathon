# ============================================================================
# cloud/terraform/modules/iam_gcp_ai_agent_adk/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the 4 IAM roles for the ADK OTel pipeline
# per the Stackdriver AI Agent ADK instrumentation doc
# (https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk).
#
# Roles:
#   - roles/telemetry.tracesWriter       — write spans to the Telemetry API
#   - roles/logging.logWriter             — write log entries to Cloud Logging
#   - roles/monitoring.metricWriter      — write custom metrics to Cloud Monitoring
#   - roles/aiplatform.user              — invoke the ADK runtime on Vertex AI
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

variable "service_account_id" {
  description = "Service account ID (lowercase, no @)"
  type        = string
  default     = "gemini-hackathon-adk"
}

variable "display_name" {
  description = "Human-readable display name"
  type        = string
  default     = "Gemini Hackathon ADK service account"
}

resource "google_service_account" "adk" {
  project      = var.project_id
  account_id   = var.service_account_id
  display_name = var.display_name
  description  = "Service account for the gemini-hackathon-adk Cloud Run service (Phase 0 GCP-first IaC refactor). Carries the 4 Stackdriver AI Agent ADK instrumentation IAM roles."
}

# The 4 canonical roles for the Stackdriver AI Agent ADK instrumentation.
locals {
  adk_iam_roles = toset([
    "roles/telemetry.tracesWriter",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/aiplatform.user",
  ])
}

resource "google_project_iam_member" "adk_roles" {
  for_each = local.adk_iam_roles
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.adk.email}"
}

output "email" {
  description = "Service account email (use in cloudrun_service bindings)"
  value       = google_service_account.adk.email
}

output "adk_iam_roles" {
  description = "The 4 Stackdriver AI Agent ADK IAM roles bound to this service account"
  value       = sort(local.adk_iam_roles)
}