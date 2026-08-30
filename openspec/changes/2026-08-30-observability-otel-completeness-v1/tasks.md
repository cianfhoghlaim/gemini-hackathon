# Tasks for 2026-08-30-observability-otel-completeness-v1

- [x] T1: OpenSpec change folder created + proposal.md drafted
- [x] T2: gemini_hackathon_backend/pyproject.toml — add 3 deps (openinference-instrumentation-google-adk, opentelemetry-exporter-gcp-trace, opentelemetry-exporter-gcp-logging)
- [x] T3: gemini_hackathon_backend/observability.py — add `try_init_adk_otel()` + `try_init_openinference_langfuse()`
- [x] T4: gemini_hackathon_backend/observability.py — `init_backend_observability()` calls both first; skip cloud_logging when adk_otel is active
- [x] T5: gemini_hackathon_backend/observability.py — module-level singletons + getters
- [x] T6: gemini_hackathon_backend/tests/test_observability_init.py — 8 new tests
- [x] T7: cloud/terraform/cloud_run_adk.tf — inject OTEL_SERVICE_NAME, OTEL_RESOURCE_ATTRIBUTES, GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY, OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT
- [x] T8: openspec/changes/.../specs/observability/spec.md — spec delta
- [ ] T9: `openspec validate 2026-08-30-observability-otel-completeness-v1 --strict` passes
- [ ] T10: `pytest gemini_hackathon_backend/tests/` — 19 + 8 = 27 passing
- [ ] T11: `pytest` — no new failures (7 pre-existing failures per KNOWN_ISSUES.md stay at 7)
- [ ] T12: web `tsc --noEmit` — zero errors
- [ ] T13: git commit + git push origin main
- [ ] T14: `openspec archive 2026-08-30-observability-otel-completeness-v1 --yes` (after deploy)