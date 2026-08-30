# ============================================================================
# cloud/terraform/modules/cloudrun_secret_mount/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "secret_id" {
  description = "Secret Manager secret ID"
  type        = string
}

variable "replication" {
  description = "Replication policy: 'automatic' or 'manual'"
  type        = string
  default     = "automatic"
}

variable "service_account_email" {
  description = "Service account email that needs access"
  type        = string
}