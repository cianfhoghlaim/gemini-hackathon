# ============================================================================
# cloud/terraform/modules/memorystore_valkey/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the Memorystore Valkey module.
# Provisions a STANDARD-tier Memorystore instance for Redis-compatible cache.
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

resource "google_redis_instance" "instance" {
  project              = var.project_id
  name                 = var.instance_name
  tier                 = var.tier
  memory_size_gb       = var.memory_size_gb
  region               = var.region
  redis_version        = "VALKEY_7_2"
  display_name         = "Gemini Hackathon Valkey"
  connect_mode         = "PRIVATE_SERVICE_ACCESS"
  auth_enabled         = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"
  deletion_protection  = false
}
