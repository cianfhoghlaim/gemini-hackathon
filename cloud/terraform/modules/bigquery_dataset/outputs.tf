# ============================================================================
# cloud/terraform/modules/bigquery_dataset/outputs.tf
# ============================================================================

output "module_id" {
  description = "Module identifier (the module name)"
  value       = "bigquery_dataset"
}

output "dataset_id" {
  description = "The BigQuery dataset ID"
  value       = google_bigquery_dataset.dataset.dataset_id
}

output "dataset_self_link" {
  description = "The BigQuery dataset self-link"
  value       = google_bigquery_dataset.dataset.self_link
}
