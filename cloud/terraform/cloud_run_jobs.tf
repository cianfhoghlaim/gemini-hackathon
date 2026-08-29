# Cloud Run Jobs for the BIEP ingestion + embedding pipeline.
#
# Phase 7 of the GCP-first refactor. Two jobs, sharing the same image
# `cloud_run.tf` already builds (gemini_hackathon:latest) — a Cloud Run
# Job is the same container with a different entrypoint command, so no
# second Dockerfile is needed.
#
#   ingest-corpus   python -m dlt_pipelines.corpus_downloader
#                   Fetches every catalog row in
#                   dlt_pipelines.official_doc_fetcher.KNOWN_OFFICIAL_URLS
#                   (all 8 non-Ireland British Isles jurisdictions — see
#                   Phase 3) to GCS + BigQuery. Triggered nightly by
#                   Cloud Scheduler.
#
#   embed-index     python -m scripts.run_cocoindex_factories
#                   Runs the 114-App 4-stage factory + the 8-jurisdiction
#                   factory (see cocoindex_flows/_factory/, Phase 4)
#                   against the freshly-ingested corpus, writing to the
#                   VectorTarget (Firestore/Vertex AI Vector Search).
#                   Triggered by Cloud Workflows after ingest-corpus
#                   succeeds — see cloud/workflows/biep_pipeline.yaml.
#
# Submit:
#   terraform apply -var="project_id=my-gcp-project" ...
# (after `terraform apply` on cloud_run.tf so the Artifact Registry repo
# + API enablement already exist — this file depends on that state.)

variable "jobs_image_tag" {
  description = "The Artifact Registry image tag both jobs run (same image as the Cloud Run service)"
  type        = string
  default     = "latest"
}

variable "ingest_schedule" {
  description = "Cloud Scheduler cron for the nightly corpus ingestion (default: 02:00 UTC daily)"
  type        = string
  default     = "0 2 * * *"
}

locals {
  jobs_image = "${google_artifact_registry_repository.gemini_hackathon.repository_url}:${var.jobs_image_tag}"
}

# ---------------------------------------------------------------------------
# Job 1 — ingest-corpus
# ---------------------------------------------------------------------------

resource "google_cloud_run_v2_job" "ingest_corpus" {
  project  = var.project_id
  location = var.region
  name     = "ingest-corpus"

  template {
    template {
      containers {
        image   = local.jobs_image
        command = ["python"]
        args    = ["-m", "dlt_pipelines.corpus_downloader"]

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "GOOGLE_CLOUD_LOCATION"
          value = var.region
        }
      }
      timeout     = "1800s" # 30 min — 35+ catalog rows across 8 jurisdictions
      max_retries = 2
    }
  }

  depends_on = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# Job 2 — embed-index
# ---------------------------------------------------------------------------

resource "google_cloud_run_v2_job" "embed_index" {
  project  = var.project_id
  location = var.region
  name     = "embed-index"

  template {
    template {
      containers {
        image   = local.jobs_image
        command = ["python"]
        args    = ["-m", "scripts.run_cocoindex_factories"]

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "GOOGLE_CLOUD_LOCATION"
          value = var.region
        }
        env {
          name  = "EMBED_BACKEND"
          value = "vertex"
        }
        env {
          name  = "VECTOR_BACKEND"
          value = "firestore"
        }
      }
      timeout     = "3600s" # 60 min — 114+8 Apps, each embedding a corpus
      max_retries = 1
    }
  }

  depends_on = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# Cloud Scheduler — nightly ingest-corpus trigger
# ---------------------------------------------------------------------------

resource "google_service_account" "scheduler_invoker" {
  project      = var.project_id
  account_id   = "biep-scheduler-invoker"
  display_name = "Cloud Scheduler -> Cloud Run Jobs invoker (BIEP pipeline)"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_can_run_ingest" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.ingest_corpus.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_invoker.email}"
}

resource "google_cloud_scheduler_job" "nightly_ingest" {
  project  = var.project_id
  region   = var.region
  name     = "biep-nightly-ingest"
  schedule = var.ingest_schedule
  time_zone = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.ingest_corpus.name}:run"
    oauth_token {
      service_account_email = google_service_account.scheduler_invoker.email
    }
  }

  depends_on = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "ingest_corpus_job_name" {
  value = google_cloud_run_v2_job.ingest_corpus.name
}

output "embed_index_job_name" {
  value = google_cloud_run_v2_job.embed_index.name
}
