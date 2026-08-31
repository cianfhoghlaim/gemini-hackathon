# memory Specification

## Purpose
TBD - created by archiving change 2026-08-30-retire-letta-wire-vertex-memory-bank-v1. Update Purpose after archive.
## Requirements
### Requirement: Env-gated ADK 2 memory service selection

The system SHALL provide an env-gated `build_memory_service()` factory in
`gemini_hackathon_backend.agents.memory` that returns one of three ADK 2
`BaseMemoryService` implementations based on env vars, in this priority:

1. `VertexAiMemoryBankService` — returned when `DEPLOYED_AGENT_ENGINE_ID` is set AND `GOOGLE_CLOUD_PROJECT` (or `GCP_PROJECT_ID`) is set. Production path.
2. `MarkdownMemoryService` — returned when `GH_MEMORY_DIR` is set. Dev / offline / HF Spaces path.
3. `None` — returned when neither is set. The ADK 2 `Runner` then falls back to its `InMemoryMemoryService` default. CI + fresh dev clone default.

#### Scenario: production deploy sets `DEPLOYED_AGENT_ENGINE_ID`

- **WHEN** the operator sets `DEPLOYED_AGENT_ENGINE_ID=<agent-engine-resource-id>` and `GOOGLE_CLOUD_PROJECT=<project-id>` in the Cloud Run service env
- **THEN** `build_memory_service()` SHALL return a `VertexAiMemoryBankService(project=<project-id>, location=<GOOGLE_CLOUD_LOCATION || "us-central1">, agent_engine_id=<id>)` instance
- **AND** the FastAPI app SHALL pass it as `memory_service=` to `ADKAgent(...)`
- **AND** `Gemini Backend` log line `memory_service: using VertexAiMemoryBankService ...` SHALL appear in Cloud Logging

#### Scenario: dev / HF Spaces deploy sets `GH_MEMORY_DIR`

- **WHEN** the operator sets `GH_MEMORY_DIR=/some/path` without `DEPLOYED_AGENT_ENGINE_ID`
- **THEN** `build_memory_service()` SHALL return a `MarkdownMemoryService(root=<path>)` instance
- **AND** the FastAPI app SHALL pass it as `memory_service=` to `ADKAgent(...)`
- **AND** `memory_service: using MarkdownMemoryService (root=...)` SHALL appear in structlog

#### Scenario: CI / fresh dev clone sets neither env var

- **WHEN** both `DEPLOYED_AGENT_ENGINE_ID` and `GH_MEMORY_DIR` are unset
- **THEN** `build_memory_service()` SHALL return `None`
- **AND** the FastAPI app SHALL NOT pass a `memory_service=` to `ADKAgent(...)`
- **AND** the ADK 2 `Runner` SHALL default to `InMemoryMemoryService`
- **AND** the backend SHALL continue to boot + serve requests (no hard failure)

### Requirement: After-agent callback persists sessions to memory

The `NccaPanelAgent` LlmAgent SHALL register an `after_agent_callback`
(`_persist_session_to_memory`) that calls
`await callback_context.add_session_to_memory()` after every completed
turn. This applies whether the configured `BaseMemoryService` is
`VertexAiMemoryBankService`, `MarkdownMemoryService`, or the ADK default
`InMemoryMemoryService`.

#### Scenario: every completed turn is persisted

- **WHEN** a chat turn completes successfully on the NCCA panel agent
- **THEN** the runner SHALL invoke `_persist_session_to_memory`
- **AND** `add_session_to_memory()` SHALL be called on the configured memory service
- **AND** any exception from `add_session_to_memory()` SHALL be logged as a warning (`memory.add_session_failed`) and SHALL NOT block the response

### Requirement: Retire Letta dependency

The system SHALL remove `letta>=0.50` from `pyproject.toml` and SHALL NOT
import any symbol from `letta.*` in `gemini_hackathon_backend/` or
`gemini_hackathon/` (the only allowed references are in this OpenSpec
proposal explaining why the dependency was removed).

The `FleetMemory` class in `gemini_hackathon/agents/fleet/fleet_memory.py`
SHALL be refactored to:
- Remove the `LettaClient` / `create_letta_client` import block
- Rename the `_letta_*` fields → `_markdown_*` and `letta_agent_id` field name → `memory_namespace`
- Replace `_init_letta` with `_init_markdown` (uses `MarkdownMemoryService`)
- Replace `_remember_letta` with `_remember_markdown` (appends bullets to the user's markdown file via `gemini_hackathon.memory.markdown._memory_path`)
- Replace `_recall_letta` with `_recall_markdown` (parses the user's markdown file + does keyword scoring)

#### Scenario: no `from letta` import remains

- **WHEN** `grep -r "from letta" gemini_hackathon_backend/ gemini_hackathon/` is run
- **THEN** zero matches SHALL be returned

#### Scenario: `FleetMemory` constructor signature changes

- **WHEN** an existing caller instantiates `FleetMemory(letta_api_key=..., letta_agent_id=...)`
- **THEN** the call SHALL raise `TypeError: unexpected keyword argument`
- **AND** the caller MUST migrate to `FleetMemory(memory_namespace=..., backend=...)`

#### Scenario: `AgentSpec.letta_agent_id` field renamed

- **WHEN** `gemini_hackathon/agents/registry.py` is inspected
- **THEN** the field SHALL be named `memory_namespace` (not `letta_agent_id`)
- **AND** all 14 registry entries SHALL carry a `memory_namespace="gemini-hackathon-<subject>-agent"` value

### Requirement: Cloud Run MUST inject memory env vars

The Cloud Run service definition SHALL inject:
The Cloud Run service definition in `cloud/terraform/cloud_run_adk.tf`
SHALL inject:
- `DEPLOYED_AGENT_ENGINE_ID` — from Secret Manager (`gemini-hackathon-adk-agent-engine` secret)
- `GH_MEMORY_DIR` — `/var/run/gh-memory`
- `GH_MEMORY_USER` — `cloud-run`

#### Scenario: production Cloud Run has both vars

- **WHEN** the Cloud Run service is deployed with the secret reference resolved
- **THEN** `DEPLOYED_AGENT_ENGINE_ID` SHALL be set
- **AND** `build_memory_service()` SHALL take the Vertex path (production)

#### Scenario: dev Cloud Run sets only `GH_MEMORY_DIR`

- **WHEN** the operator overrides `DEPLOYED_AGENT_ENGINE_ID` to empty in the dev environment
- **THEN** `build_memory_service()` SHALL fall back to MarkdownMemoryService
- **AND** the backend SHALL still boot + serve requests

