# ============================================================================
# cloud/terraform/modules/memorystore_valkey/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the memorystore_valkey Terraform module.
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
