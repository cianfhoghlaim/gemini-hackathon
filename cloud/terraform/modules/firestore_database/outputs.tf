# ============================================================================
# cloud/terraform/modules/firestore_database/outputs.tf
# ============================================================================

output "module_id" {
  description = "Module identifier (the module name)"
  value       = "firestore_database"
}

output "database_id" {
  description = "The Firestore database ID"
  value       = google_firestore_database.database.name
}

output "database_name" {
  description = "The Firestore fully-qualified database name"
  value       = google_firestore_database.database.id
}

output "location_id" {
  description = "The Firestore location ID"
  value       = google_firestore_database.database.location_id
}
