# ============================================================================
# cloud/terraform/modules/artifact_registry_repo/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the Artifact Registry repository module.
# Provisions a Docker-format Artifact Registry repository.
# See openspec/changes/2026-08-30-gcp-first-iac-refactor-v1/specs/infrastructure/spec.md
# for the contract this module satisfies.
# ============================================================================

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

resource "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.location
  repository_id = var.repository_id
  format        = var.format
  description   = var.description

  docker_config {
    immutable_tags = var.immutable_tags
  }
}
