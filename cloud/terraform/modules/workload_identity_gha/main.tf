# ============================================================================
# cloud/terraform/modules/workload_identity_gha/main.tf
#
# Phase 0 (GCP-first IaC refactor) — the GitHub Actions Workload Identity
# Federation module. Creates the workload identity pool + OIDC provider
# + service account + IAM bindings that GitHub Actions uses to authenticate
# to GCP without storing service-account JSON keys.
# ============================================================================

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

resource "google_iam_workload_identity_pool" "pool" {
  project                   = var.project_id
  workload_identity_pool_id = var.pool_id
  display_name              = "GitHub Actions pool"
  description               = "Workload identity pool for GitHub Actions OIDC"
}

resource "google_iam_workload_identity_pool_provider" "provider" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.pool.workload_identity_pool_id
  workload_identity_pool_provider_id = var.provider_id
  display_name                       = "GitHub OIDC provider"
  description                        = "OIDC provider for ${var.repo}"

  attribute_condition = "assertion.repository == '${var.repo}'"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "gha" {
  project      = var.project_id
  account_id   = var.service_account_id
  display_name = var.display_name
  description  = "Service account for GitHub Actions via Workload Identity Federation"
}

resource "google_service_account_iam_binding" "workload_identity_user" {
  service_account_id = google_service_account.gha.name
  role               = "roles/iam.workloadIdentityUser"
  members = [
    "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.pool.name}/attribute.repository/${var.repo}",
  ]
}

resource "google_project_iam_member" "gha_roles" {
  for_each = toset(var.gha_project_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.gha.email}"
}
