# ============================================================================
# cloud/terraform/modules/firestore_database/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "database_id" {
  description = "Firestore database ID"
  type        = string
  default     = "(default)"
}

variable "location_id" {
  description = "Firestore location ID (region or multi-region)"
  type        = string
  default     = "eur3"
}

variable "type" {
  description = "Firestore database type (FIRESTORE_NATIVE or DATASTORE_MODE)"
  type        = string
  default     = "FIRESTORE_NATIVE"
}
