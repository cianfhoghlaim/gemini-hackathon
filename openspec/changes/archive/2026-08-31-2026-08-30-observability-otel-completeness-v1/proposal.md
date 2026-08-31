# 2026-08-30-observability-otel-completeness-v1

> **Phase 1 of the multi-stage plan (see AGENTS.md). Wire ADK-native
> OpenTelemetry exporters + the OpenInference Langfuse instrumentor into
> the ADK backend so every LLM call, tool invocation, and agent run
> emits an OTel span under the OpenTelemetry GenAI semantic conventions.**

## Why

Phase 2 (already pushed in commit `85f11a5`) wired Langfuse + MLflow + Cloud
Logging into the ADK backend. Phase 1 closes the gap by adding the
ADK-native OTel pipeline (`google.adk.telemetry.google_cloud`) that
auto-streams every ADK span to Cloud Trace + Cloud Logging, and the
OpenInference Langfuse instrumentor that wraps every ADK call as a
nested Langfuse span under the parent AG-UI trace.

Without this, the Langfuse trace from Phase 2 only contains the parent
AG-UI request span — the actual LLM calls, tool invocations, and agent
runs inside it are invisible. With this, every LLM call shows up with its
own cost + token usage + latency + (when applicable) error stack.

## What changes

- **`gemini_hackathon_backend/pyproject.toml`** — add 3 deps:
  - `openinference-instrumentation-google-adk>=0.1.0`
  - `opentelemetry-exporter-gcp-trace>=1.9.0`
  - `opentelemetry-exporter-gcp-logging>=1.9.0`
- **`gemini_hackathon_backend/observability.py`** — add 2 new init functions:
  - `try_init_adk_otel()` — wires `google.adk.telemetry.google_cloud.get_gcp_exporters()` + `maybe_set_otel_providers()` for Cloud Trace + Cloud Logging under the OTLP GenAI semantic conventions
  - `try_init_openinference_langfuse()` — wraps every ADK call as a Langfuse span via `GoogleADKInstrumentor().instrument()`
  - `init_backend_observability()` calls both before the existing `try_init_langfuse()` + `try_init_mlflow()` calls
  - Add module-level singletons `_ADK_OTEL_HOOKS` + `_OPENINFERENCE_INSTRUMENTOR` and getters
- **`cloud/terraform/cloud_run_adk.tf`** — inject 4 new env vars:
  - `OTEL_SERVICE_NAME=gemini-hackathon-adk`
  - `OTEL_RESOURCE_ATTRIBUTES=service.namespace=gemini-hackathon,deployment.environment=hackathon`
  - `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT` (privacy: never log full prompts in Cloud Run; use GCS upload if needed)
  - `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`
- **`gemini_hackathon_backend/tests/`** — new test `test_observability_init_env_gating`:
  - When no GCP_PROJECT_ID + no LANGFUSE_PUBLIC_KEY: `_ADK_OTEL_HOOKS = None`, `_OPENINFERENCE_INSTRUMENTOR = None`
  - When GCP_PROJECT_ID set but google-adk not installed: graceful degradation
  - When LANGFUSE_PUBLIC_KEY set: `GoogleADKInstrumentor().instrument()` returns True

## Acceptance

- `grep -E "openinference|opentelemetry-exporter-gcp" gemini_hackathon_backend/pyproject.toml` returns 3 lines
- `pytest gemini_hackathon_backend/tests/test_observability_init.py` passes (1+ new tests)
- `pytest gemini_hackathon_backend/tests/` passes (19 + 1 = 20 passing)
- `mise run lint` green
- Manual: `terraform plan` on `cloud_run_adk.tf` shows the 4 new env vars
- `grep -r "openinference" gemini_hackathon_backend/` returns the new wiring code (no orphan imports)

## Dependencies

- **Blocked by:** Phase 0 (retire Letta, wire memory service) — already pushed in commit `ebef31e`.
- **Unblocks:** Phase 2 (CocoIndex PDF pipeline), Phase 8 (Cloud Run deploy + observability verification).
- **Cross-repo:** the OpenInference + ADK integration is documented at `adk.dev/integrations/langfuse/` and `langfuse.com/integrations/frameworks/google-adk` — both are first-party.

## Compatibility

- When `GCP_PROJECT_ID` is unset (CI / fresh dev clone): `try_init_adk_otel()` logs `observability.adk_otel_skipped` and returns `None`. No behaviour change from Phase 2.
- When `LANGFUSE_PUBLIC_KEY` is unset: `try_init_openinference_langfuse()` logs `observability.openinference_skipped` and returns `None`. No behaviour change.
- When both are set: the OTel pipeline runs first (auto-streams to Cloud Trace + Cloud Logging); OpenInference instruments every ADK call; Langfuse sees both the parent AG-UI trace + the nested per-call spans.
- `record_generation()` (Phase 2) is kept as a no-op when OpenInference is active (the instrumentor replaces it) but remains callable for the dev path (no Langfuse key).