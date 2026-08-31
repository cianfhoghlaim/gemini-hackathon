# 2026-08-30-retire-letta-wire-vertex-memory-bank-v1

> **Phase 0 of the multi-stage plan (see AGENTS.md). Retire Letta from the
> ADK backend + wire VertexAiMemoryBankService (production) +
> MarkdownMemoryService (dev/offline fallback).**

## Why

Letta is described as obscure OSS and the SDK shape churns between releases
(per `gemini_hackathon/agents/fleet/fleet_memory.py:442,417,52-67` — three
separate try/except blocks defending against Letta API drift). The ADK 2
ecosystem has two first-party memory services that implement the same
`BaseMemoryService` interface with managed GCP + file-backed options:

- `VertexAiMemoryBankService` — managed by Vertex AI Agent Engine, LLM-extracted facts
- `MarkdownMemoryService` — already implemented at `gemini_hackathon/memory/markdown.py:58`

The journey orchestrator already uses `VertexAiMemoryBankService` (per
`journey/journey_orchestrator/memory_service.py:36`); the rest of the
fleet still defaults to Letta. Aligning both removes the obsolescence risk
and brings the ADK backend under the same memory policy as the journey.

## What changes

- **Remove `letta>=0.50`** from `pyproject.toml` + remove the `letta.*` mypy override
- **Add `gemini_hackathon_backend/agents/memory.py`** with `build_memory_service()` env-gated:
  - When `DEPLOYED_AGENT_ENGINE_ID` is set → `VertexAiMemoryBankService(project, location, agent_engine_id)`
  - When `GH_MEMORY_DIR` is set (default `~/.gemini_hackathon/memory`) → `MarkdownMemoryService(root=GH_MEMORY_DIR)`
  - When neither is set → return `None` and fall through to the `InMemoryMemoryService` default (preserves existing dev/CI behaviour)
- **Wire `memory_service=build_memory_service()` into `gemini_hackathon_backend/main.py`** — replaces `use_in_memory_services=True`
- **Add `before_agent_callback`** in `gemini_hackathon_backend/agents/ncca_panel.py` that calls `await callback_context.add_session_to_memory()` so completed sessions are persisted to the Memory Bank / Markdown file automatically
- **Update `gemini_hackathon/agents/registry.py`** — rename `letta_agent_id` field → `memory_namespace` (semantics change but same shape)
- **Refactor `gemini_hackathon/agents/fleet/fleet_memory.py`** — delete the 3 Letta-specific try/except blocks; keep the in-memory + markdown implementations as `MarkdownMemoryService` adapters (re-export from `gemini_hackathon.memory.markdown`)
- **Update `cloud/terraform/cloud_run_adk.tf`** — inject `DEPLOYED_AGENT_ENGINE_ID` + `GH_MEMORY_DIR` env vars
- **Update `tests/conftest.py`** — replace `LETTA_API_KEY` / `LETTA_AGENT_ID` / `MEMORY_BACKEND` env vars with `DEPLOYED_AGENT_ENGINE_ID` + `GH_MEMORY_DIR` + `GH_MEMORY_USER`
- **Update `tests/test_fleet_primitives.py`** — rename `test_fleet_memory_letta_namespace` → `test_fleet_memory_namespace`

## Acceptance

- `grep -r "from letta" gemini_hackathon_backend/ gemini_hackathon/` returns 0 lines (excluding deprecated aliases in docs)
- `grep -r "letta_agent_id" gemini_hackathon/` returns 0 lines
- `grep -E "letta" pyproject.toml` returns 0 lines
- `pytest gemini_hackathon_backend/tests/` passes (11 passing + 1 new `test_build_memory_service_env_gating`)
- `pytest tests/test_fleet_primitives.py` passes (renamed test still asserts the namespace transformation)
- `pytest tests/test_call_llm.py` passes (no changes to model policy)
- `web tsc --noEmit` zero errors

## Dependencies

- **Blocked by:** nothing (this is the first phase).
- **Cross-repo:** the Fleet primitives (`Gateway`, `Identity`, `Armor`, `Observability`, `Memory`, `AG-UI`, `MCP`) are wholesale-copied from Cianfhoghlaim, **not** introduced as a new dependency.
- The `VertexAiMemoryBankService` and `MarkdownMemoryService` paths both implement the `BaseMemoryService` 2-method interface (`add_session_to_memory`, `search_memory`) — so no caller code changes are required to swap between them.

## Compatibility

- **No code changes required** for callers — both services share the `BaseMemoryService` interface
- The fallback chain is: `VertexAiMemoryBankService` (if `DEPLOYED_AGENT_ENGINE_ID`) → `MarkdownMemoryService` (if `GH_MEMORY_DIR`) → `InMemoryMemoryService` (default)
- The Cloud Run env vars are env-gated — when neither is set, the ADK backend behaves identically to today