# observability Specification

## Purpose
TBD - created by archiving change 2026-08-30-observability-otel-completeness-v1. Update Purpose after archive.
## Requirements
### Requirement: ADK-native OTel pipeline wired by default

The ADK backend MUST initialise the ADK-native OpenTelemetry pipeline
(Cloud Trace + Cloud Logging via OTLP) when `GCP_PROJECT_ID` (or
`GOOGLE_CLOUD_PROJECT`) is set. The pipeline SHALL emit every ADK LLM
call, tool invocation, and agent run as an OTel span following the
OpenTelemetry GenAI semantic conventions.

The initialiser SHALL:
1. Set `OTEL_SERVICE_NAME=gemini-hackathon-adk` (default; overridable)
2. Set `OTEL_RESOURCE_ATTRIBUTES=service.namespace=gemini-hackathon,deployment.environment=hackathon`
3. Set `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT` (privacy)
4. Call `google.adk.telemetry.google_cloud.get_gcp_exporters(enable_cloud_tracing=True, enable_cloud_metrics=False, enable_cloud_logging=True)`
5. Call `maybe_set_otel_providers(otel_hooks_to_setup=[otel_hooks], otel_resource=get_gcp_resource(project_id))`

#### Scenario: production Cloud Run has GCP_PROJECT_ID set

- **WHEN** the Cloud Run service is deployed with `GCP_PROJECT_ID=<project-id>`
- **THEN** `try_init_adk_otel()` SHALL attempt to wire the OTel pipeline
- **AND** `observability.adk_otel_initialised` SHALL be logged
- **AND** every ADK LLM call SHALL emit a Cloud Trace span + Cloud Logging entry

#### Scenario: dev / CI / fresh clone has GCP_PROJECT_ID unset

- **WHEN** `GCP_PROJECT_ID` and `GOOGLE_CLOUD_PROJECT` are both unset
- **THEN** `try_init_adk_otel()` SHALL log `observability.adk_otel_skipped reason='GCP_PROJECT_ID unset'`
- **AND** the function SHALL return `None`
- **AND** `state["adk_otel"]` SHALL be `False`
- **AND** the backend SHALL continue to boot + serve requests

#### Scenario: google.adk not importable

- **WHEN** `GCP_PROJECT_ID` is set but the `google.adk` package is missing
- **THEN** `try_init_adk_otel()` SHALL catch the `ImportError`
- **AND** SHALL log `observability.adk_otel_skipped reason=<type>: <message>`
- **AND** the function SHALL return `None`
- **AND** the env vars SHALL still be setdefault'd (the setdefault runs
  before the try block)

### Requirement: OpenInference Langfuse instrumentor wired by default

The ADK backend MUST initialise the OpenInference Langfuse instrumentor
when `LANGFUSE_PUBLIC_KEY` is set. The instrumentor SHALL wrap every
ADK LLM call, tool invocation, and agent run as a nested Langfuse span
under the parent AG-UI trace (set by `AguiTraceMiddleware`).

#### Scenario: Langfuse credentials present

- **WHEN** `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are both set
- **THEN** `try_init_openinference_langfuse()` SHALL call `GoogleADKInstrumentor().instrument()` once
- **AND** `observability.openinference_initialised` SHALL be logged
- **AND** every ADK call SHALL appear in Langfuse as a nested span under the parent trace

#### Scenario: Langfuse credentials absent

- **WHEN** `LANGFUSE_PUBLIC_KEY` is unset
- **THEN** `try_init_openinference_langfuse()` SHALL log `observability.openinference_skipped reason='LANGFUSE_PUBLIC_KEY unset'`
- **AND** the function SHALL return `None`
- **AND** `state["openinference"]` SHALL be `False`

### Requirement: Cloud Run MUST inject OpenTelemetry env vars

The Cloud Run service definition SHALL inject 4 env vars that the ADK
OTel pipeline consumes:

- `OTEL_SERVICE_NAME=gemini-hackathon-adk`
- `OTEL_RESOURCE_ATTRIBUTES=service.namespace=gemini-hackathon,deployment.environment=hackathon`
- `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT` (privacy)

#### Scenario: Cloud Run startup probes the new env vars

- **WHEN** `terraform plan` is run on `cloud_run_adk.tf`
- **THEN** the 4 env vars SHALL appear in the planned container spec

### Requirement: init order prevents double-logging

The `init_backend_observability()` function SHALL call the inits in this
order to prevent Cloud Logging from receiving duplicated entries:

1. `try_init_adk_otel()` — first
2. `try_init_openinference_langfuse()` — second
3. `try_init_langfuse()` — third
4. `try_init_mlflow()` — fourth
5. `try_init_cloud_logging()` — fifth, but **only when `_ADK_OTEL_HOOKS` is None**

When the OTel pipeline is active, the raw Cloud Logging handler is
skipped because the OTel SDK already streams every span to Cloud Logging.

#### Scenario: OTel active, Cloud Logging raw handler skipped

- **WHEN** `GCP_PROJECT_ID` is set AND `try_init_adk_otel()` returns a truthy hooks object
- **THEN** `try_init_cloud_logging()` SHALL NOT be called
- **AND** `_CLOUD_LOGGING_CLIENT` SHALL remain `None`
- **AND** `state["cloud_logging"]` SHALL be `False`

#### Scenario: OTel inactive, Cloud Logging raw handler active

- **WHEN** `GCP_PROJECT_ID` is unset (so `try_init_adk_otel()` returns `None`)
- **THEN** `try_init_cloud_logging()` SHALL be called
- **AND** `_CLOUD_LOGGING_CLIENT` SHALL be set to the raw handler
- **AND** `state["cloud_logging"]` SHALL reflect the actual init result

### Requirement: Module-level singletons + getters

The observability module SHALL expose module-level singletons
(`_ADK_OTEL_HOOKS`, `_OPENINFERENCE_INSTRUMENTOR`) populated by
`init_backend_observability()` and getters (`get_adk_otel_hooks()`,
`get_openinference_instrumentor()`) for callers that need them.

#### Scenario: getters return the singletons

- **WHEN** `init_backend_observability()` has run
- **THEN** `get_adk_otel_hooks()` SHALL return `_ADK_OTEL_HOOKS`
- **AND** `get_openinference_instrumentor()` SHALL return `_OPENINFERENCE_INSTRUMENTOR`

