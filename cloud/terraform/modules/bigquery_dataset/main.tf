# ============================================================================
# cloud/terraform/modules/bigquery_dataset/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the BigQuery dataset module.
# Provisions a per-domain BigQuery dataset.
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

resource "google_bigquery_dataset" "dataset" {
  project                    = var.project_id
  dataset_id                 = var.dataset_id
  location                   = var.location
  delete_contents_on_destroy = false

  default_table_expiration_ms = var.default_table_expiration_ms

  labels = var.labels
}
