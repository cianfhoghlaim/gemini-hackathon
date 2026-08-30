# ============================================================================
# cloud/terraform/modules/iam_gcp_ai_agent_adk/variables.tf
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "service_account_id" {
  description = "Service account ID (lowercase, no @)"
  type        = string
  default     = "gemini-hackathon-adk"
}

variable "display_name" {
  description = "Human-readable display name"
  type        = string
  default     = "Gemini Hackathon ADK service account"
}