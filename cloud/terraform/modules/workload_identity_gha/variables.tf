# ============================================================================
# cloud/terraform/modules/workload_identity_gha/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "pool_id" {
  description = "Workload identity pool ID"
  type        = string
  default     = "gh-pool"
}

variable "provider_id" {
  description = "Workload identity pool provider ID"
  type        = string
  default     = "gh-provider"
}

variable "repo" {
  description = "GitHub repository (owner/repo) allowed by the OIDC condition"
  type        = string
  default     = "cianmacandeisigh/gemini_hackathon"
}

variable "service_account_id" {
  description = "Service account ID (lowercase, no @)"
  type        = string
  default     = "gemini-hackathon-gha"
}

variable "display_name" {
  description = "Human-readable display name"
  type        = string
  default     = "Gemini Hackathon GHA service account"
}

variable "gha_project_roles" {
  description = "Project-level IAM roles to grant the GHA service account"
  type        = list(string)
  default = [
    "roles/run.admin",
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.editor",
    "roles/iam.serviceAccountTokenCreator",
  ]
}
