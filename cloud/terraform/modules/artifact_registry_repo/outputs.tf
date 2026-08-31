# ============================================================================
# cloud/terraform/modules/artifact_registry_repo/outputs.tf
# ============================================================================

output "module_id" {
  description = "Module identifier (the module name)"
  value       = "artifact_registry_repo"
}

output "repository_id" {
  description = "The Artifact Registry repository ID"
  value       = google_artifact_registry_repository.repo.repository_id
}

output "repository_name" {
  description = "The Artifact Registry fully-qualified repository name"
  value       = google_artifact_registry_repository.repo.name
}

output "repository_url" {
  description = "The Artifact Registry Docker repository URL"
  value       = "${var.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}
