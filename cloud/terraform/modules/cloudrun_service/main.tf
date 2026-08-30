# ============================================================================
# cloud/terraform/modules/cloudrun_service/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the universal Cloud Run service module.
# Used by all 4 NEW gemini-hackathon stacks (backend, frontend,
# observability-client, mlflow-client).
#
# Inputs:
#   - service_name        : the Cloud Run service name
#   - image              : Artifact Registry image URL
#   - region             : GCP region (e.g. europe-west1)
#   - service_account    : service account email (created by iam_gcp_ai_agent_adk)
#   - cpu / memory        : resource limits
#   - min_instances / max_instances : auto-scaling
#   - env_vars           : plain env vars (non-secret)
#   - secret_env_vars    : env vars backed by Secret Manager (no JSON keys)
#   - secret_volumes     : Secret Manager files mounted as volumes
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

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "image" {
  description = "Artifact Registry image URL (region-docker.pkg.dev/.../image:tag)"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "service_account" {
  description = "Service account email (created by iam_gcp_ai_agent_adk)"
  type        = string
}

variable "cpu" {
  description = "CPU limit per instance"
  type        = string
  default     = "2"
}

variable "memory" {
  description = "Memory limit per instance"
  type        = string
  default     = "4Gi"
}

variable "min_instances" {
  description = "Minimum instance count (set 0 for scale-to-zero)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum instance count"
  type        = number
  default     = 10
}

variable "env_vars" {
  description = "Plain (non-secret) env vars as { name = value }"
  type        = map(string)
  default     = {}
}

variable "secret_env_vars" {
  description = "Env vars backed by Secret Manager as { name = secret_id }"
  type        = map(string)
  default     = {}
}

variable "secret_volumes" {
  description = "Secret Manager volumes as [{ name = ..., secret_id = ..., version = ..., mount_path = ... }]"
  type = list(object({
    name       = string
    secret_id  = string
    version    = string
    mount_path = string
  }))
  default = []
}

variable "timeout_seconds" {
  description = "Request timeout (seconds)"
  type        = number
  default     = 900
}

variable "container_port" {
  description = "Container port (the application listens on this)"
  type        = number
  default     = 8080
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}

resource "google_cloud_run_v2_service" "service" {
  project  = var.project_id
  name     = var.service_name
  location = var.region

  template {
    service_account = var.service_account
    timeout_seconds = var.timeout_seconds

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    dynamic "volumes" {
      for_each = var.secret_volumes
      content {
        name = volumes.value.name
        secret {
          secret = volumes.value.secret_id
          items {
            version = volumes.value.version
            path    = volumes.value.mount_path
          }
        }
      }
    }

    containers {
      image = var.image

      ports {
        container_port = var.container_port
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }

      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_env_vars
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      dynamic "volume_mounts" {
        for_each = var.secret_volumes
        content {
          name       = volume_mounts.value.name
          mount_path = volume_mounts.value.mount_path
        }
      }

      startup_probe {
        http_get {
          path = "/healthz"
        }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 3
      }
    }
  }

  labels = var.labels
}

output "service_url" {
  description = "The deployed Cloud Run service URL"
  value       = google_cloud_run_v2_service.service.status[0].url
}

output "service_name" {
  description = "The deployed Cloud Run service name"
  value       = google_cloud_run_v2_service.service.name
}