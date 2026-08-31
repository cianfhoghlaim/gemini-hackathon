# ============================================================================
# cloud/terraform/modules/cloudsql_postgres/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "gemini-hackathon-pg"
}

variable "tier" {
  description = "Cloud SQL machine tier (e.g. db-f1-micro, db-g1-small)"
  type        = string
  default     = "db-f1-micro"
}

variable "deletion_protection" {
  description = "Whether to enable deletion protection (set false for dev)"
  type        = bool
  default     = false
}

variable "database_name" {
  description = "Name of the default database to create"
  type        = string
  default     = "gemini_hackathon"
}

variable "user_name" {
  description = "Name of the default Postgres user"
  type        = string
  default     = "gemini_hackathon"
}
