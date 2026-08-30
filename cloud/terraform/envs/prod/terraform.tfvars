# ============================================================================
# cloud/terraform/envs/prod/terraform.tfvars — prod project defaults
# (image_tag is required at apply time; no default)
# ============================================================================

project_id = "gemini-hackathon-prod"
region     = "europe-west1"
# image_tag is intentionally required - production uses pinned tags.