# ============================================================================
# cloud/terraform/envs/dev/backend.tf — GCS backend for dev state
# ============================================================================

terraform {
  backend "gcs" {
    bucket = "gemini-hackathon-tfstate-dev"
    prefix = "envs/dev"
  }
}