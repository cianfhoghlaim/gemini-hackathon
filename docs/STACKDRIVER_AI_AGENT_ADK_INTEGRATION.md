# Stackdriver AI Agent ADK Integration

> **Phase 9 of `2026-08-30-gcp-first-iac-refactor-v1`.** The canonical
> reference for the GCP-native ADK observability contract. Mirrors the
> Google Cloud doc at
> [docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk](https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk)
> (last updated 2026-08-26).

## 1. The canonical 6 env vars

```bash
OTEL_SERVICE_NAME='gemini-hackathon-adk'
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED='true'
OTEL_SEMCONV_STABILITY_OPT_IN='gen_ai_latest_experimental'
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT='EVENT_ONLY'
ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS='false'
GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY='true'
```

Plus 2 standard OTel env vars:

```bash
OTEL_RESOURCE_ATTRIBUTES='service.namespace=gemini-hackathon,deployment.environment=hackathon'
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT='https://telemetry.googleapis.com/v1/traces'
```

**Critical**: `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` MUST be
`EVENT_ONLY` (not `true` which is invalid per the doc; not `NO_CONTENT`).

## 2. The canonical Python package list

```toml
opentelemetry-instrumentation-google-genai>=0.4b0
opentelemetry-instrumentation-vertexai>=2.0b0
opentelemetry-instrumentation-sqlite3>=0.41b0
opentelemetry-exporter-otlp-proto-grpc>=1.27
opentelemetry-exporter-gcp-logging>=1.9.0
openinference-instrumentation-google-adk>=0.1.0
```

## 3. The canonical 6 GCP APIs to enable

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  serviceusage.googleapis.com \
  telemetry.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudtrace.googleapis.com
```

## 4. The canonical 4 IAM roles for the Cloud Run service account

- `roles/telemetry.tracesWriter`
- `roles/logging.logWriter`
- `roles/monitoring.metricWriter`
- `roles/aiplatform.user`

## 5. The canonical Python wiring (per `try_init_adk_otel()`)

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider(
    resource=Resource.create(
        {
            "service.name": os.environ["OTEL_SERVICE_NAME"],
            "service.namespace": "gemini-hackathon",
            "service.version": os.environ.get("COMMIT_SHA", "dev"),
            "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "hackathon"),
        }
    ),
)
exporter = OTLPSpanExporter(
    endpoint="https://telemetry.googleapis.com/v1/traces",
    insecure=False,
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
```

## 6. The canonical Terraform wiring

The `cloud/terraform/modules/observability_apis/main.tf` module enables
the 6 APIs. The `cloud/terraform/modules/iam_gcp_ai_agent_adk/main.tf`
module creates the service account + the 4 IAM roles.

## 7. The canonical reference sample

Per the Stackdriver doc, the canonical end-to-end sample is:
`github.com/GoogleCloudPlatform/opentelemetry-samples/python/adk-sql-agent`

This sample shows:
- `adk web --otel_to_cloud` (Cloud Run Compose)
- The `opentelemetry.env` file with the 6 env vars
- The `gcloud services enable` command
- The 4 IAM role bindings
- The `Trace Explorer` UI navigation

## 8. The Application Monitoring dashboards

Per the Stackdriver doc, the **Vertex AI Application Monitoring**
dashboards auto-populate from these spans (under **Optimize >
Observability** in the GCP console). The 5 sub-views are:
- Overview
- Evaluation
- Models
- Tools
- Usage

## 9. Local dev path

For local dev (per user direction), the self-hosted Langfuse +
MLflow stack stays in `compose.yaml`. The dev observability surface
is the same as the prior 8-phase work in this session:
- Langfuse web: http://localhost:3000
- MLflow UI: http://localhost:5000

The Stackdriver 6-env-var contract doesn't apply to the local dev
path (the dev compose uses the docker-internal OTLP path, not the GCP
unified Telemetry API).
