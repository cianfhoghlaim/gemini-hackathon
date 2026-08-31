# ============================================================================
# cloud/terraform/modules/memorystore_valkey/outputs.tf
# ============================================================================

output "module_id" {
  description = "Module identifier (the module name)"
  value       = "memorystore_valkey"
}

output "host" {
  description = "The Memorystore host (IP)"
  value       = google_redis_instance.instance.host
}

output "port" {
  description = "The Memorystore port"
  value       = google_redis_instance.instance.port
}

output "instance_id" {
  description = "The Memorystore instance ID"
  value       = google_redis_instance.instance.id
}

output "instance_name" {
  description = "The Memorystore instance name"
  value       = google_redis_instance.instance.name
}
