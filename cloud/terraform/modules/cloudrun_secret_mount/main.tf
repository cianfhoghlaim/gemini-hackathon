# ============================================================================
# cloud/terraform/modules/cloudrun_secret_mount/main.tf
#
# Phase 0 (GCP-first IaC refactor) — provisions a Secret Manager secret
# AND grants the cloudrun_service service account access to it.
#
# The actual volume mount wiring lives in the cloudrun_service module's
# secret_volumes input. This module is the canonical "create + grant"
# step for the secrets that the volume mounts reference.
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

variable "secret_id" {
  description = "Secret Manager secret ID"
  type        = string
}

variable "replication" {
  description = "Replication policy: 'automatic' or 'manual'"
  type        = string
  default     = "automatic"
}

variable "service_account_email" {
  description = "Service account email that needs access (e.g. the ADK SA)"
  type        = string
}

resource "google_secret_manager_secret" "secret" {
  project   = var.project_id
  secret_id = var.secret_id

  replication {
    automatic = var.replication == "automatic" ? true : null
    dynamic "user_managed" {
      for_each = var.replication == "manual" ? [1] : []
      content {
        replicas {
          location = "europe-west1"
        }
      }
    }
  }
}

resource "google_secret_manager_secret_iam_member" "cloudrun_access" {
  project  = var.project_id
  secret_id = google_secret_manager_secret.secret.secret_id
  role     = "roles/secretmanager.secretAccessor"
  member   = "serviceAccount:${var.service_account_email}"
}

output "secret_id" {
  description = "The Secret Manager secret ID (use in cloudrun_service.secret_env_vars)"
  value       = google_secret_manager_secret.secret.secret_id
}