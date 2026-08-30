# ============================================================================
# cloud/terraform/modules/cloudrun_secret_mount/outputs.tf
# ============================================================================

output "secret_id" {
  description = "The Secret Manager secret ID (use in cloudrun_service.secret_env_vars)"
  value       = google_secret_manager_secret.secret.secret_id
}