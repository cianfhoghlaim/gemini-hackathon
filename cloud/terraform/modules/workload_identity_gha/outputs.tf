# ============================================================================
# cloud/terraform/modules/workload_identity_gha/outputs.tf
# ============================================================================

output "module_id" {
  description = "Module identifier (the module name)"
  value       = "workload_identity_gha"
}

output "service_account_email" {
  description = "The GHA service account email"
  value       = google_service_account.gha.email
}

output "workload_identity_pool_id" {
  description = "The workload identity pool ID"
  value       = google_iam_workload_identity_pool.pool.workload_identity_pool_id
}

output "workload_identity_provider_id" {
  description = "The workload identity pool provider ID"
  value       = google_iam_workload_identity_pool_provider.provider.workload_identity_pool_provider_id
}

output "workload_identity_provider_name" {
  description = "The fully-qualified provider resource name"
  value       = google_iam_workload_identity_pool_provider.provider.name
}
