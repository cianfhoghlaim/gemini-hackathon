# ============================================================================
# cloud/terraform/modules/gcs_bucket/outputs.tf
# ============================================================================

output "module_id" {
  description = "Module identifier (the module name)"
  value       = "gcs_bucket"
}

output "bucket_name" {
  description = "The GCS bucket name"
  value       = google_storage_bucket.bucket.name
}

output "bucket_url" {
  description = "The GCS bucket URL (gs://...)"
  value       = google_storage_bucket.bucket.url
}

output "bucket_self_link" {
  description = "The GCS bucket self-link"
  value       = google_storage_bucket.bucket.self_link
}
