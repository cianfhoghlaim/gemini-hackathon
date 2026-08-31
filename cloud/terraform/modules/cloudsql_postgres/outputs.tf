# ============================================================================
# cloud/terraform/modules/cloudsql_postgres/outputs.tf
# ============================================================================

output "module_id" {
  description = "Module identifier (the module name)"
  value       = "cloudsql_postgres"
}

output "connection_name" {
  description = "The Cloud SQL connection name (project:region:instance)"
  value       = google_sql_database_instance.instance.connection_name
}

output "instance_self_link" {
  description = "The self-link for the Cloud SQL instance"
  value       = google_sql_database_instance.instance.self_link
}

output "instance_name" {
  description = "The Cloud SQL instance name"
  value       = google_sql_database_instance.instance.name
}

output "database_name" {
  description = "The created database name"
  value       = google_sql_database.database.name
}

output "user_name" {
  description = "The created user name"
  value       = google_sql_user.user.name
}

output "db_password_secret_ref" {
  description = "Reference (NOT value) to the randomly-generated DB password — store in Secret Manager"
  value       = random_password.db_password.result
  sensitive   = true
}
