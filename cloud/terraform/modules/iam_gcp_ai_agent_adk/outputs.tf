# ============================================================================
# cloud/terraform/modules/iam_gcp_ai_agent_adk/outputs.tf
# ============================================================================

output "email" {
  description = "Service account email (use in cloudrun_service bindings)"
  value       = google_service_account.adk.email
}

output "adk_iam_roles" {
  description = "The 4 Stackdriver AI Agent ADK IAM roles bound to this service account"
  value       = sort(local.adk_iam_roles)
}