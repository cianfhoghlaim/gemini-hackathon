# ============================================================================
# cloud/terraform/modules/cloudbuild_trigger/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the Cloud Build trigger"
  type        = string
  default     = "europe-west1"
}

variable "repo_name" {
  description = "Cloud Source Repos name (must be connected to Cloud Build)"
  type        = string
}

variable "trigger_name" {
  description = "Cloud Build trigger name"
  type        = string
  default     = "gemini-hackathon-adk-trigger"
}

variable "branch_name" {
  description = "Branch name to trigger on"
  type        = string
  default     = "main"
}

variable "cloudbuild_yaml" {
  description = "Path to the cloudbuild.yaml file (relative to repo root)"
  type        = string
  default     = "cloudbuild.yaml"
}

variable "included_files" {
  description = "Glob of files to include (triggers only fire when matched)"
  type        = list(string)
  default     = ["cloudbuild.yaml", "Dockerfile", "backend/**", "gemini_hackathon/**"]
}

variable "substitutions" {
  description = "Build substitutions"
  type        = map(string)
  default = {
    _REGION = "europe-west1"
    _REPO   = "gemini-hackathon"
  }
}
