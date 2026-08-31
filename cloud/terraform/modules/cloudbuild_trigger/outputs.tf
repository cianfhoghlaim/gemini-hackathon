# ============================================================================
# cloud/terraform/modules/cloudbuild_trigger/outputs.tf
# ============================================================================

output "module_id" {
  description = "Module identifier (the module name)"
  value       = "cloudbuild_trigger"
}

output "trigger_id" {
  description = "The Cloud Build trigger ID"
  value       = google_cloudbuild_trigger.trigger.trigger_id
}

output "trigger_name" {
  description = "The Cloud Build trigger name"
  value       = google_cloudbuild_trigger.trigger.name
}
