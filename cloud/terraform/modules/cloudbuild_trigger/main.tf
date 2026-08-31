# ============================================================================
# cloud/terraform/modules/cloudbuild_trigger/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the Cloud Build trigger module.
# Provisions a Cloud Build trigger that fires on pushes to the given branch
# and runs the cloudbuild.yaml at the repo root.
# ============================================================================

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

resource "google_cloudbuild_trigger" "trigger" {
  project     = var.project_id
  name        = var.trigger_name
  description = "Cloud Build trigger for ${var.repo_name} on branch ${var.branch_name}"
  location    = var.region

  trigger_template {
    repo_name   = var.repo_name
    branch_name = var.branch_name
  }

  build {
    step {
      name = "gcr.io/cloud-builders/gcloud"
      args = ["version"]
    }
  }

  substitutions = var.substitutions
  filename      = var.cloudbuild_yaml
  included_files = var.included_files
}
