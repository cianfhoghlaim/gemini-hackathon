# ============================================================================
# cloud/terraform/modules/artifact_registry_repo/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "repository_id" {
  description = "Artifact Registry repository ID"
  type        = string
  default     = "gemini-hackathon"
}

variable "location" {
  description = "Artifact Registry repository location (region)"
  type        = string
  default     = "europe-west1"
}

variable "format" {
  description = "Repository format (DOCKER, MAVEN, NPM, PYTHON, etc.)"
  type        = string
  default     = "DOCKER"
}

variable "description" {
  description = "Human-readable description"
  type        = string
  default     = "gemini_hackathon container images"
}

variable "immutable_tags" {
  description = "Make tags immutable (recommended for production)"
  type        = bool
  default     = false
}
