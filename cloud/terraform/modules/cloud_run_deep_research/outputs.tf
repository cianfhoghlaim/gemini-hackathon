# ============================================================================
# cloud/terraform/modules/cloud_run_deep_research/outputs.tf
# ============================================================================

output "service_url" {
  description = "The deployed Cloud Run service URL"
  value       = module.service.service_url
}

output "service_name" {
  description = "The deployed Cloud Run service name"
  value       = module.service.service_name
}
