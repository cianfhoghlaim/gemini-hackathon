# ============================================================================
# cloud/terraform/modules/bigquery_dataset/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
  default     = "biep"
}

variable "location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "europe-west1"
}

variable "default_table_expiration_ms" {
  description = "Default table expiration (milliseconds). 0 = no expiry."
  type        = number
  default     = 0
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}
