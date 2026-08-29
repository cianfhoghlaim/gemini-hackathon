# Cloud Run service for the British Isles Journey studio.
#
# Phase D.2 of the GCP-first refactor. One Cloud Run service hosts the
# unified 6-level Gradio studio + the ADK 2 orchestrator. Adds the same
# `google_project_service.required` API enablement pattern the existing
# `cloud_run.tf` uses (Phase 0), plus the journey-specific env vars
# (`JOURNEY_EVENT_CODE` etc.) baked in at deploy time.
#
# Same image the existing Cloud Build publishes — just a different
# service name + different env vars.

variable "journey_service_name" {
  description = "Cloud Run service name for the British Isles Journey studio + orchestrator"
  type        = string
  default     = "gemini-hackathon-journey"
}

variable "journey_min_instances" {
  description = "Min Cloud Run instances for the Journey (0 = scale to zero for idle workshops)"
  type        = number
  default     = 0
}

variable "journey_max_instances" {
  description = "Max Cloud Run instances for the Journey (cap so a misconfigured workshop can't spin up 1000 instances)"
  type        = number
  default     = 10
}

variable "journey_memory" {
  description = "Memory per Cloud Run instance (the 4-backend ledger fan-out is the heaviest level)"
  type        = string
  default     = "4Gi"
}

variable "journey_cpu" {
  description = "CPU per Cloud Run instance"
  type        = number
  default     = 2
}

variable "journey_event_code" {
  description = "Baked-in event code at deploy time"
  type        = string
  default     = "biep-demo"
}

variable "journey_image_tag" {
  description = "The Artifact Registry image tag the journey service runs"
  type        = string
  default     = "latest"
}

locals {
  journey_image = "${google_artifact_registry_repository.gemini_hackathon.repository_url}:${var.journey_image_tag}"
}

# Add to the local.required_apis list in cloud_run.tf if it isn't already
# there — done as a side-effect of the module being applied after cloud_run.tf,
# since `google_project_service.required` is the canonical enablement surface.
# (No new APIs required vs. cloud_run.tf — Vertex AI + Document AI + Firestore
# + Cloud Storage + Cloud Run + Cloud Build are all already enabled there.)

resource "google_cloud_run_v2_service" "journey" {
  project  = var.project_id
  location = var.region
  name     = var.journey_service_name

  template {
    scaling {
      min_instance_count = var.journey_min_instances
      max_instance_count = var.journey_max_instances
    }

    containers {
      image = local.journey_image

      resources {
        limits = {
          cpu    = var.journey_cpu
          memory = var.journey_memory
        }
      }

      env {
        name  = "MODEL_PROFILE"
        value = "hackathon"
      }
      env {
        name  = "GEMINI_BACKEND"
        value = "vertex"
      }
      env {
        name  = "EMBED_BACKEND"
        value = "vertex"
      }
      env {
        name  = "VECTOR_BACKEND"
        value = "firestore"
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      # Journey-specific env vars (the studio reads these)
      env {
        name  = "JOURNEY_EVENT_CODE"
        value = var.journey_event_code
      }
      env {
        name  = "JOURNEY_MAX_PARTICIPANTS"
        value = "200"
      }
      env {
        name  = "JOURNEY_FIRESTORE_DATABASE"
        value = "(default)"
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/api/health"
        }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/api/health"
        }
        period_seconds    = 30
        timeout_seconds   = 5
        failure_threshold = 3
      }
    }

    timeout = "600s"
    service_account = "gemini-hackathon-journey@${var.project_id}.iam.gserviceaccount.com"
  }

  # Allow unauthenticated access (the journey is a public workshop demo
  # surface; the actual workshop auth happens at the per-level API layer
  # once we wire Firebase Auth + custom claims in Phase E).
  ingress = "INGRESS_TRAFFIC_ALL"
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "journey_service_url" {
  value = google_cloud_run_v2_service.journey.status[0].url
}
