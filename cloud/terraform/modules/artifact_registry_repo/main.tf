# ============================================================================
# cloud/terraform/modules/artifact_registry_repo/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the artifact_registry_repo Terraform module.
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
