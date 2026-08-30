# Tasks for 2026-08-30-retire-letta-wire-vertex-memory-bank-v1

- [x] T1: OpenSpec change folder created + proposal.md drafted
- [x] T2: pyproject.toml — remove `letta>=0.50` + the `letta.*` mypy override
- [x] T3: gemini_hackathon_backend/agents/memory.py — `build_memory_service()` env-gated
- [x] T4: gemini_hackathon_backend/main.py — wire `memory_service=build_memory_service()`, drop `use_in_memory_services=True`
- [x] T5: gemini_hackathon_backend/agents/ncca_panel.py — `before_agent_callback` calls `add_session_to_memory()`
- [x] T6: gemini_hackathon_backend/tests/ — new `test_build_memory_service_env_gating` + existing tests still pass
- [x] T7: gemini_hackathon/agents/registry.py — rename `letta_agent_id` → `memory_namespace`
- [x] T8: gemini_hackathon/agents/fleet/fleet_memory.py — delete the 3 Letta-specific try/except blocks; keep markdown adapter
- [x] T9: cloud/terraform/cloud_run_adk.tf — inject `DEPLOYED_AGENT_ENGINE_ID` + `GH_MEMORY_DIR` env vars
- [x] T10: tests/conftest.py — replace `LETTA_API_KEY` / `LETTA_AGENT_ID` / `MEMORY_BACKEND` with new env vars
- [x] T11: tests/test_fleet_primitives.py — rename `test_fleet_memory_letta_namespace` → `test_fleet_memory_namespace`
- [x] T12: openspec/changes/.../specs/memory/spec.md — spec delta (ADDED Requirements: env-gated memory service selection; canonical ADK 2 BaseMemoryService contract)
- [x] T13: `openspec validate 2026-08-30-retire-letta-wire-vertex-memory-bank-v1 --strict` passes
- [x] T14: `mise run lint && mise run py:typecheck && mise run turbo typecheck`
- [x] T15: `pytest` — no new failures (7 pre-existing failures per KNOWN_ISSUES.md stay at 7)
- [x] T16: `web tsc --noEmit` — zero errors
- [x] T17: `git add` + `git commit -m "Phase 0: retire Letta, wire VertexAiMemoryBankService + MarkdownMemoryService"` + `git push origin main`
- [x] T18: `openspec archive 2026-08-30-retire-letta-wire-vertex-memory-bank-v1 --yes` (after deploy)