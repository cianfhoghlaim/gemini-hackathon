# ============================================================================
# cloud/terraform/modules/cloudrun_service/outputs.tf
# ============================================================================

output "service_url" {
  description = "The deployed Cloud Run service URL"
  value       = google_cloud_run_v2_service.service.status[0].url
}

output "service_name" {
  description = "The deployed Cloud Run service name"
  value       = google_cloud_run_v2_service.service.name
}