# Terraform manifest for the gemini_hackathon Cloud Run deployment.
#
# All values come from variables — no hardcoded project IDs, regions,
# service accounts, or secrets. Pass at plan/apply time:
#
#   terraform init
#   terraform plan \
#       -var="project_id=my-gcp-project" \
#       -var="region=europe-west1" \
#       -var="service_account=cloudrun-sa@my-gcp-project.iam.gserviceaccount.com"
#   terraform apply -auto-approve ...

variable "project_id" {
  description = "GCP project ID hosting the gemini_hackathon service"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run + Artifact Registry"
  type        = string
  default     = "europe-west1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "gemini-hackathon"
}

variable "service_account" {
  description = "Service account the Cloud Run service runs as (empty = use default)"
  type        = string
  default     = ""
}

variable "min_instances" {
  description = "Minimum Cloud Run instances (0 = scale to zero)"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum Cloud Run instances"
  type        = number
  default     = 10
}

variable "memory" {
  description = "Memory per Cloud Run instance"
  type        = string
  default     = "2Gi"
}

variable "cpu" {
  description = "CPU per Cloud Run instance"
  type        = number
  default     = 2
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated requests to the Cloud Run service"
  type        = bool
  default     = true
}

# ---------------------------------------------------------------------------
# API enablement — everything Phases 1-7 depend on. `disable_on_destroy =
# false` so a `terraform destroy` doesn't take down APIs other stacks in the
# same project rely on.
# ---------------------------------------------------------------------------

locals {
  required_apis = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",       # Vertex AI (Gemini, embeddings, Vector Search)
    "documentai.googleapis.com",       # Document AI (OCR ensemble path 1)
    "bigquery.googleapis.com",         # BIEP warehouse (dlt destination)
    "storage.googleapis.com",          # GCS raw/derived/assets buckets
    "firestore.googleapis.com",        # MasteryLedger + session + vector FindNearest
    "workflows.googleapis.com",        # Cloud Workflows (ingest -> extract -> embed)
    "cloudscheduler.googleapis.com",   # nightly corpus ingestion trigger
    "pubsub.googleapis.com",           # OCR completion fan-out (replaces OCR_WEBHOOK_URL)
    "run.googleapis.com",              # Cloud Run Jobs share this API
    "cloudtrace.googleapis.com",       # observability (legacy, kept for compat)
    "logging.googleapis.com",          # observability (Cloud Logging)
    "monitoring.googleapis.com",       # observability (Cloud Monitoring)
    "telemetry.googleapis.com",        # observability (unified Telemetry API - canonical 2026 path)
  ]
}

resource "google_project_service" "required" {
  for_each                  = toset(local.required_apis)
  project                   = var.project_id
  service                   = each.value
  disable_dependent_services = false
  disable_on_destroy        = false
}

# ---------------------------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------------------------

resource "google_artifact_registry_repository" "gemini_hackathon" {
  project       = var.project_id
  location      = var.region
  repository_id = "gemini-hackathon"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# Cloud Run service
# ---------------------------------------------------------------------------

resource "google_cloud_run_service" "gemini_hackathon" {
  project  = var.project_id
  location = var.region
  name     = var.service_name

  depends_on = [google_project_service.required]

  template {
    spec {
      container_concurrency = 80
      timeout_seconds       = 300

      containers {
        image = "${google_artifact_registry_repository.gemini_hackathon.repository_url}:latest"

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
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
          name  = "GOOGLE_CLOUD_LOCATION"
          value = var.region
        }
        env {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        }

        # Secrets mounted from Secret Manager. The Secret Manager entries
        # must exist before apply. Provision them with:
        #   echo -n "sk-unsloth-..." | gcloud secrets create UNSLOTH_API_KEY --data-file=-
        env {
          name = "UNSLOTH_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.unsloth_api_key.secret_id
              version = "latest"
            }
          }
        }
        env {
          name = "UNSLOTH_BASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.unsloth_base_url.secret_id
              version = "latest"
            }
          }
        }
        env {
          name = "GEMINI_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.gemini_api_key.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name_suffix = ""
  lifecycle {
    ignore_changes = [traffic[0].latest_revision]
  }
}

# Allow public invocation if the variable is true.
#
# NOTE: `google_iam_policy` takes repeatable `binding { role, members }`
# blocks, not a `binding_data = jsonencode(...)` argument — the latter does
# not exist on this data source and previously made this file unplannable.
data "google_iam_policy" "noauth" {
  count = var.allow_unauthenticated ? 1 : 0

  binding {
    role    = "roles/run.invoker"
    members = ["allUsers"]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  count       = var.allow_unauthenticated ? 1 : 0
  location    = google_cloud_run_service.gemini_hackathon.location
  project     = google_cloud_run_service.gemini_hackathon.project
  service     = google_cloud_run_service.gemini_hackathon.name
  policy_data = data.google_iam_policy.noauth[count.index].policy_data
}

# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------

resource "google_secret_manager_secret" "unsloth_api_key" {
  project   = var.project_id
  secret_id = "UNSLOTH_API_KEY"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "unsloth_base_url" {
  project   = var.project_id
  secret_id = "UNSLOTH_BASE_URL"
  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret" "gemini_api_key" {
  project   = var.project_id
  secret_id = "GEMINI_API_KEY"
  replication {
    automatic = true
  }
}

data "google_iam_policy" "cloudrun_secrets_reader" {
  binding {
    role    = "roles/secretmanager.secretAccessor"
    members = var.service_account == "" ? [] : ["serviceAccount:${var.service_account}"]
  }
}

resource "google_secret_manager_secret_iam_policy" "unsloth_api_key" {
  project     = google_secret_manager_secret.unsloth_api_key.project
  secret_id   = google_secret_manager_secret.unsloth_api_key.secret_id
  policy_data = data.google_iam_policy.cloudrun_secrets_reader.policy_data
}

resource "google_secret_manager_secret_iam_policy" "unsloth_base_url" {
  project     = google_secret_manager_secret.unsloth_base_url.project
  secret_id   = google_secret_manager_secret.unsloth_base_url.secret_id
  policy_data = data.google_iam_policy.cloudrun_secrets_reader.policy_data
}

resource "google_secret_manager_secret_iam_policy" "gemini_api_key" {
  project     = google_secret_manager_secret.gemini_api_key.project
  secret_id   = google_secret_manager_secret.gemini_api_key.secret_id
  policy_data = data.google_iam_policy.cloudrun_secrets_reader.policy_data
}

# ---------------------------------------------------------------------------
# GCS buckets (Phase 1 — the data substrate; replaces Garage S3)
# ---------------------------------------------------------------------------

resource "google_storage_bucket" "biep_raw" {
  project                     = var.project_id
  name                         = "${var.project_id}-biep-raw"
  location                     = var.region
  uniform_bucket_level_access = true
  force_destroy                = false
  depends_on                   = [google_project_service.required]
}

resource "google_storage_bucket" "biep_derived" {
  project                     = var.project_id
  name                         = "${var.project_id}-biep-derived"
  location                     = var.region
  uniform_bucket_level_access = true
  force_destroy                = false
  depends_on                   = [google_project_service.required]
}

resource "google_storage_bucket" "biep_assets" {
  project                     = var.project_id
  name                         = "${var.project_id}-biep-assets"
  location                     = var.region
  uniform_bucket_level_access = true
  force_destroy                = false
  depends_on                   = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# BigQuery dataset (Phase 1 — the DLT `bigquery_biep` named destination)
# ---------------------------------------------------------------------------

resource "google_bigquery_dataset" "biep" {
  project                    = var.project_id
  dataset_id                  = "biep"
  location                    = var.region
  delete_contents_on_destroy = false
  depends_on                  = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# Firestore (Phase 2/6 — MasteryLedger + vector FindNearest + session state)
#
# NOTE: a project can only have ONE Firestore database in Native mode named
# "(default)". If Firebase (firebase.json) already provisioned it via
# `firebase deploy`, import it instead of applying this resource:
#   terraform import google_firestore_database.default "projects/<id>/databases/(default)"
# ---------------------------------------------------------------------------

resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.required]

  lifecycle {
    prevent_destroy = true
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "service_url" {
  value = google_cloud_run_service.gemini_hackathon.status[0].url
}

output "image_url" {
  value = google_artifact_registry_repository.gemini_hackathon.repository_url
}

output "gcs_raw_bucket" {
  value = google_storage_bucket.biep_raw.name
}

output "gcs_derived_bucket" {
  value = google_storage_bucket.biep_derived.name
}

output "gcs_assets_bucket" {
  value = google_storage_bucket.biep_assets.name
}

output "bigquery_dataset" {
  value = google_bigquery_dataset.biep.dataset_id
}
