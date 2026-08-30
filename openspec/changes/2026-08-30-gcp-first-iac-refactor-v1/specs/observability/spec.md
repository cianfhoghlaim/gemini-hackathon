# Spec Delta: observability (Phase 0 — Stackdriver AI Agent ADK integration)

This delta is applied by the OpenSpec change
[`2026-08-30-gcp-first-iac-refactor-v1`](../proposal.md). It describes the
**ADDED** Requirements to the canonical `observability` capability
that this change adds.

The canonical reference is the Google Cloud doc
[Instrument ADK applications with OpenTelemetry](https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk)
(last updated 2026-08-26).

## ADDED Requirements

### Requirement: The ADK OTel pipeline SHALL use the canonical Stackdriver 6-env-var set
The system SHALL meet the requirement: The ADK OTel pipeline SHALL use the canonical Stackdriver 6-env-var set.
The `try_init_adk_otel()` function in
`gemini_hackathon_backend/observability.py` SHALL setdefault the
following 6 env vars (in this exact order) on every Cloud Run boot:

```
OTEL_SERVICE_NAME='gemini-hackathon-adk'
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED='true'
OTEL_SEMCONV_STABILITY_OPT_IN='gen_ai_latest_experimental'
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT='EVENT_ONLY'
ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS='false'
GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY='true'
```

The exporter SHALL use `opentelemetry-exporter-otlp-proto-grpc` pointed at
`https://telemetry.googleapis.com/v1/traces` (the unified Telemetry
OTLP API), NOT the legacy `get_gcp_exporters` path.

#### Scenario: `GCP_PROJECT_ID` unset -> the env vars are setdefault'd even before any GCP API call

- **WHEN** `try_init_adk_otel()` is called and `GCP_PROJECT_ID` is unset
- **THEN** the function SHALL log `observability.adk_otel_skipped reason='GCP_PROJECT_ID unset'`
- **AND** the function SHALL still setdefault the 6 env vars (so the operator can verify the contract)
- **AND** the function SHALL return `None`

#### Scenario: `GCP_PROJECT_ID` set -> the OTLP exporter is initialised

- **WHEN** `try_init_adk_otel()` is called and `GCP_PROJECT_ID` is set
- **THEN** the function SHALL setdefault the 6 env vars
- **AND** SHALL set up an `OTLPSpanExporter(endpoint="https://telemetry.googleapis.com/v1/traces")`
- **AND** SHALL register a `BatchSpanProcessor` with the exporter
- **AND** SHALL return the hooks object (non-None)

#### Scenario: `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` MUST be `EVENT_ONLY`

- **WHEN** the value is set to anything other than `EVENT_ONLY` (notably `true` or `NO_CONTENT`)
- **THEN** the setdefault SHALL override to `EVENT_ONLY`
- **BECAUSE** the Stackdriver doc explicitly states: "Don't set the value of this variable to `true`. When you use the most recent semantic conventions, setting the value of this variable to `true` results in an invalid configuration."

### Requirement: The 4 Stackdriver IAM roles SHALL be bound to the ADK Cloud Run service account
The system SHALL meet the requirement: The 4 Stackdriver IAM roles SHALL be bound to the ADK Cloud Run service account.
The system SHALL provide a Terraform module
`cloud/terraform/modules/iam_gcp_ai_agent_adk` that creates a service
account with the following 4 role bindings:

- `roles/telemetry.tracesWriter`
- `roles/logging.logWriter`
- `roles/monitoring.metricWriter`
- `roles/aiplatform.user`

#### Scenario: `gcloud projects get-iam-policy` shows the 4 role bindings

- **WHEN** the operator runs `gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:gemini-hackathon-adk"`
- **THEN** the output SHALL include all 4 role bindings

### Requirement: The 6 GCP APIs SHALL be enabled on the dev project
The system SHALL meet the requirement: The 6 GCP APIs SHALL be enabled on the dev project.
The system SHALL provide a Terraform module
`cloud/terraform/modules/observability_apis` that creates 6
`google_project_service` resources:

- `aiplatform.googleapis.com` (Vertex AI)
- `serviceusage.googleapis.com` (Service Usage)
- `telemetry.googleapis.com` (unified Telemetry API — the canonical 2026 endpoint)
- `logging.googleapis.com` (Cloud Logging)
- `monitoring.googleapis.com` (Cloud Monitoring)
- `cloudtrace.googleapis.com` (Cloud Trace — legacy, kept for backward compat with the existing `try_init_adk_otel()` env-gated path)

#### Scenario: `gcloud services list --enabled` shows the 6 APIs

- **WHEN** the operator runs `gcloud services list --enabled --project=$PROJECT_ID | grep -E "aiplatform|serviceusage|telemetry|logging|monitoring|cloudtrace"`
- **THEN** the output SHALL include all 6 APIs

### Requirement: Langfuse self-hosted dev path SHALL remain in `compose.yaml`
The system SHALL meet the requirement: Langfuse self-hosted dev path SHALL remain in `compose.yaml`.
The system SHALL NOT remove the self-hosted Langfuse stack
(Postgres + ClickHouse + Redis + web + worker) from the local dev
surface. The 6-service stack SHALL stay in `compose.yaml` as the
canonical **local dev** observability surface.

The system MAY optionally dual-export traces to **Langfuse Cloud
Hobby tier** (free, 50K units/mo) in the prod Cloud Run service when
`LANGFUSE_BASE_URL` is set.

#### Scenario: The local `docker compose up` boots the full Langfuse + MLflow stack

- **WHEN** the operator runs `docker compose up`
- **THEN** the 6 Langfuse services + the 1 MLflow service SHALL boot
- **AND** the Langfuse web UI SHALL be reachable at `http://localhost:3000`
- **AND** the MLflow UI SHALL be reachable at `http://localhost:5000`

#### Scenario: The prod Cloud Run service dual-exports to Langfuse Cloud

- **WHEN** the prod Cloud Run service has `LANGFUSE_BASE_URL=https://cloud.langfuse.com` and the corresponding `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` from Secret Manager
- **THEN** every ADK span SHALL be exported to BOTH `https://telemetry.googleapis.com/v1/traces` (Cloud Trace) AND `https://cloud.langfuse.com/api/public/otel/v1/traces` (Langfuse Cloud)
