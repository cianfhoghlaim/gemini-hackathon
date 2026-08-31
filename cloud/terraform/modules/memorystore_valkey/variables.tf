# ============================================================================
# cloud/terraform/modules/memorystore_valkey/variables.tf
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
  description = "Memorystore instance name"
  type        = string
  default     = "gemini-hackathon-valkey"
}

variable "tier" {
  description = "Memorystore tier (BASIC or STANDARD)"
  type        = string
  default     = "STANDARD"
}

variable "memory_size_gb" {
  description = "Memory size in GB"
  type        = number
  default     = 1
}
