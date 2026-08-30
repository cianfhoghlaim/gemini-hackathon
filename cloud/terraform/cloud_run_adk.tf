# Cloud Run service for the British Isles Journey ADK agent runtime.
#
# Phase D — T2 #14. Sibling to `cloud_run_journey.tf` (which hosts the
# Gradio studio). This service hosts `gemini_hackathon_backend.main:app`,
# which exposes the AG-UI SSE endpoint at `/` for CopilotKit + a `/healthz`
# probe for Cloud Run.
#
# Wires the same Vertex AI + Firestore + Cloud Storage + Cloud Run APIs
# already enabled by `cloud_run.tf:google_project_service.required`. The
# image is the existing `gemini-hackathon:latest` artifact-registry image
# built by the parent Dockerfile — the runtime distinguishes the two
# services by their env vars + entrypoint command.

variable "adk_service_name" {
  description = "Cloud Run service name for the ADK agent runtime"
  type        = string
  default     = "gemini-hackathon-adk"
}

variable "adk_min_instances" {
  description = "Min Cloud Run instances for ADK agent (0 = scale to zero)"
  type        = number
  default     = 0
}

variable "adk_max_instances" {
  description = "Max Cloud Run instances for ADK agent (cap so misconfiguration can't spin up dozens)"
  type        = number
  default     = 10
}

variable "adk_memory" {
  description = "Memory per Cloud Run instance for ADK agent"
  type        = string
  default     = "2Gi"
}

variable "adk_cpu" {
  description = "CPU per Cloud Run instance for ADK agent"
  type        = number
  default     = 2
}

variable "adk_timeout_seconds" {
  description = "Per-request timeout (the AG-UI SSE stream may be long for 5-key-competency surfaces)"
  type        = number
  default     = 300
}

variable "adk_concurrency" {
  description = "Max concurrent requests per instance (CopilotKit SSE is per-client)"
  type        = number
  default     = 80
}

variable "adk_image_tag" {
  description = "The Artifact Registry image tag the ADK service runs"
  type        = string
  default     = "latest"
}

# Where in the artifact registry the parent image lives (built by the
# parent Dockerfile's docker build).
locals {
  adk_image = "${google_artifact_registry_repository.gemini_hackathon.repository_url}:${var.adk_image_tag}"
}

resource "google_cloud_run_v2_service" "adk" {
  project  = var.project_id
  location = var.region
  name     = var.adk_service_name

  template {
    scaling {
      min_instance_count = var.adk_min_instances
      max_instance_count = var.adk_max_instances
    }

    containers {
      image = locals.adk_image

      # Use the parent's python + uvicorn entrypoint to launch the ADK
      # backend instead of the Gradio studio. The parent image has both
      # installed (uv pip install ag-ui-adk adds uvicorn + google-adk).
      command = ["uv", "run", "uvicorn", "gemini_hackathon_backend.main:app",
                 "--host", "0.0.0.0", "--port", "8080"]
      args    = []

      resources {
        limits = {
          cpu    = var.adk_cpu
          memory = var.adk_memory
        }
      }

      env {
        name  = "MODEL_PROFILE"
        value = "hackathon"
      }
      env {
        name  = "GEMINI_BACKEND"
        value = "vertex"
      }
      env {
        name  = "EMBED_BACKEND"
        value = "vertex"
      }
      env {
        name  = "VECTOR_BACKEND"
        value = "firestore"
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "JOURNEY_EVENT_CODE"
        value = "biep-demo"
      }
      env {
        name  = "JOURNEY_MAX_PARTICIPANTS"
        value = "200"
      }
      env {
        name  = "JOURNEY_FIRESTORE_DATABASE"
        value = "(default)"
      }

      # Observability — Langfuse (LLM cost + prompt mgmt) + MLflow
      # (experiment tracking) + Cloud Logging. All three are env-gated
      # and degrade to structlog-only when their env vars are absent.
      # The secret values come from Infisical via the per-portal
      # Locket sidecar; LANGFUSE_HOST defaults to the cloud instance.
      env {
        name = "LANGFUSE_PUBLIC_KEY"
        value_from {
          secret_key_ref {
            name = "gemini-hackathon-adk-langfuse"
            key  = "latest"
          }
        }
      }
      env {
        name = "LANGFUSE_SECRET_KEY"
        value_from {
          secret_key_ref {
            name = "gemini-hackathon-adk-langfuse"
            key  = "latest"
          }
        }
      }
      env {
        name  = "LANGFUSE_HOST"
        value = "https://cloud.langfuse.com"
      }
      env {
        name  = "MLFLOW_TRACKING_URI"
        value = "http://mlflow.cloud-ops.svc.cluster.local:5000"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      # Memory service — env-gated between VertexAiMemoryBankService
      # (production) and MarkdownMemoryService (dev/offline fallback).
      # Both implementations satisfy the ADK 2 BaseMemoryService contract;
      # the canonical factory is gemini_hackathon_backend.agents.memory.build_memory_service().
      # DEPLOYED_AGENT_ENGINE_ID is wired from a Secret Manager reference
      # (the Agent Engine resource is provisioned by cloud/terraform/agent_engine.tf
      # in Phase 8).
      env {
        name = "DEPLOYED_AGENT_ENGINE_ID"
        value_from {
          secret_key_ref {
            name = "gemini-hackathon-adk-agent-engine"
            key  = "latest"
          }
        }
      }
      env {
        name  = "GH_MEMORY_DIR"
        value = "/var/run/gh-memory"
      }
      env {
        name  = "GH_MEMORY_USER"
        value = "cloud-run"
      }

      # Phase 1 — ADK-native OpenTelemetry pipeline (Cloud Trace +
      # Cloud Logging under the GenAI semantic conventions) +
      # OpenInference Langfuse instrumentor. Both are env-gated; when
      # GCP_PROJECT_ID / LANGFUSE_PUBLIC_KEY are unset, the inits are
      # no-ops.
      env {
        name  = "OTEL_SERVICE_NAME"
        value = "gemini-hackathon-adk"
      }
      env {
        name  = "OTEL_RESOURCE_ATTRIBUTES"
        value = "service.namespace=gemini-hackathon,deployment.environment=hackathon"
      }
      env {
        name  = "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"
        value = "true"
      }
      env {
        name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        value = "NO_CONTENT"
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/healthz"
        }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/healthz"
        }
        period_seconds    = 30
        timeout_seconds   = 5
        failure_threshold = 3
      }
    }

    timeout = "${var.adk_timeout_seconds}s"
    service_account = "gemini-hackathon-adk@${var.project_id}.iam.gserviceaccount.com"
  }

  # AG-UI + CopilotKit browsers connect without auth — the per-participant
  # state is scoped by the AG-UI thread_id + the user's Firebase Auth ID
  # token (verified at the bridge boundary via `extract_headers`).
  ingress = "INGRESS_TRAFFIC_ALL"
}

output "adk_service_url" {
  value = google_cloud_run_v2_service.adk.status[0].url
}
