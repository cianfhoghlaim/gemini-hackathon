# ============================================================================
# cloud/terraform/modules/cloudrun_service/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "image" {
  description = "Artifact Registry image URL"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "service_account" {
  description = "Service account email"
  type        = string
}

variable "cpu" {
  description = "CPU limit per instance"
  type        = string
  default     = "2"
}

variable "memory" {
  description = "Memory limit per instance"
  type        = string
  default     = "4Gi"
}

variable "min_instances" {
  description = "Minimum instance count (0 for scale-to-zero)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum instance count"
  type        = number
  default     = 10
}

variable "env_vars" {
  description = "Plain env vars"
  type        = map(string)
  default     = {}
}

variable "secret_env_vars" {
  description = "Secret Manager-backed env vars"
  type        = map(string)
  default     = {}
}

variable "secret_volumes" {
  description = "Secret Manager volume mounts"
  type = list(object({
    name       = string
    secret_id  = string
    version    = string
    mount_path = string
  }))
  default = []
}

variable "timeout_seconds" {
  description = "Request timeout (seconds)"
  type        = number
  default     = 900
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8080
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = {}
}