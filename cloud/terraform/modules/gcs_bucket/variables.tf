# ============================================================================
# cloud/terraform/modules/gcs_bucket/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "bucket_name" {
  description = "Globally-unique bucket name (defaults to ${project_id}-biep-raw)"
  type        = string
  default     = null
}

variable "location" {
  description = "GCS bucket location (region)"
  type        = string
  default     = "europe-west1"
}

variable "uniform_bucket_level_access" {
  description = "Enable uniform bucket-level access (recommended for GCP)"
  type        = bool
  default     = true
}

variable "force_destroy" {
  description = "Allow Terraform to delete a non-empty bucket (DANGER: dev only)"
  type        = bool
  default     = false
}

variable "lifecycle_age_days" {
  description = "Age (days) at which to delete objects (0 = disable lifecycle)"
  type        = number
  default     = 0
}
