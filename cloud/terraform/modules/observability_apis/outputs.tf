# ============================================================================
# cloud/terraform/modules/observability_apis/outputs.tf
# ============================================================================

output "enabled_apis" {
  description = "The 6 observability APIs enabled on the project"
  value       = sort(local.observability_apis)
}