# ============================================================================
# cloud/terraform/envs/prod/backend.tf — GCS backend for prod state
# ============================================================================

terraform {
  backend "gcs" {
    bucket = "gemini-hackathon-tfstate-prod"
    prefix = "envs/prod"
  }
}