# ADK 2 patterns reference (cross-cutting)

> **Cross-cutting reference for the ADK 2 patterns the Journey teaches.**
> Each pattern links to its canonical example in `docs/adk-examples/` and
> shows how the journey re-anchors it on the gemini-hackathon
> pipeline.

## Pattern 1 — `before_agent_callback` + `{key}` state templating

**Where the Journey uses it**: every level's agent (Levels 1, 2, 3, 5).

**Source**: `adk2-tutorial/L0_first_agent/` + `way-back-home/level_1/agent/agent.py`

**Implementation**: `gemini_hackathon/journey/journey_orchestrator/callback_before_agent.py`

```python
from gemini_hackathon.journey.journey_orchestrator.callback_before_agent import (
    hydrate_participant_state,
)

# Wired into an ADK 2 agent's `before_agent_callback` parameter:
agent = Agent(
    name="level_1_extraction",
    model="gemini-3.5-flash",
    instruction="... use {subnation} {subject} ...",
    before_agent_callback=hydrate_participant_state,
)
```

What it does:
1. Reads the participant's Firestore doc (`journeys/{event_code}/participants/{uid}`)
2. Falls back to env vars + sensible defaults in offline mode
3. Writes 6 keys into `ctx.state`: `learner_id` + `subnation` + `subject` + `event_code` + `journey_event_code` + `display_name`
4. Returns the dict (so callers/tests can inspect what was hydrated)

## Pattern 2 — `Workflow(edges=[(START, ...fn...agent)])`

**Where the Journey uses it**: Level 1's 4-node pipeline (fetch → baml → embed → upsert).

**Source**: `adk2-tutorial/L1_graph_basics/workflow.py`

**Implementation**: `gemini_hackathon/journey/level_1_syllabus_extraction/__init__.py`
(the `run_level_1()` orchestrator + the 3 function nodes + 1 implicit
BAML "agent node").

What it teaches:
- Function nodes are 0 LLM calls, deterministic, fast
- Agent nodes are 1 LLM call each (only when needed)
- `edges=[(START, fn1, fn2, ..., agent)]` is the canonical syntax
- Outputs are typed via Pydantic models (the `LCSyllabusDocument` here)

## Pattern 3 — `ParallelAgent` + `JoinNode`

**Where the Journey uses it**: Level 2 (4-path OCR) and Level 3 (3-criterion grader).

**Source**: `adk2-tutorial/L2a_parallel_join/workflow.py`

**Implementation**: 
- Level 2: `gemini_hackathon/journey/level_2_past_paper_ocr/__init__.py` (the 4 paths run via `asyncio.to_thread`, joined into a consensus vote)
- Level 3: `gemini_hackathon/journey/level_3_marking_scheme/__init__.py` (the 3 criterion graders + `join_criterion_grades` + `synthesise_strategy`)

What it teaches:
- Fan-out pattern: `[(START, fn1, JoinNode), (START, fn2, JoinNode), (START, fn3, JoinNode)]`
- Join: `JoinNode` waits for ALL branches, bundles outputs keyed by function name
- Post-join: one synthesis agent node writes the final output

## Pattern 4 — `RequestInput` (human-in-the-loop pause)

**Where the Journey uses it**: between Level 4 and Level 5 in the orchestrator.

**Source**: `loop-lab-table/hello_workflow.py` (the canonical ADK 2 HITL example)

**Implementation**: `gemini_hackathon/journey/journey_orchestrator/workflow.py` (`request_human_confirmation`)

```python
from google.adk.events.request_input import RequestInput

async def request_human_confirmation(ctx):
    return RequestInput(
        message="Mastery ledger updated across 4 backends. Continue to Level 5?"
    )
```

What it teaches:
- ADK 2's `RequestInput` event pauses the Runner until the participant
  confirms via the studio's "Continue" button
- The orchestrator's HITL checkpoint is where a workshop host can
  review the per-backend status board before asset generation
- `RequestInput` is a Pydantic model, not a dict (Phase C.3's `run_full_journey`
  normalises both via `hasattr(result, "model_dump")`)

## Pattern 5 — Vertex AI Memory Bank (cross-workshop learner continuity)

**Where the Journey uses it**: every level's `update_mastery()` call writes
to `memory_service.add_session_to_memory()` so long-term learner state
persists across Cloud Run cold starts + across multiple workshop runs.

**Source**: `support-memory-lab/r3_last_month/` + the
`VertexAiMemoryBankService` integration tests.

**Implementation**: `gemini_hackathon/journey/journey_orchestrator/memory_service.py`
+ `gemini_hackathon/ledger/mastery_ledger.py` (`update_mastery()` calls
`memory_service.add_session_to_memory(session)`).

What it teaches:
- The Memory Bank requires `DEPLOYED_AGENT_ENGINE_ID` (an Agent Engine
  instance); falls back to "memory not wired" if unset (a deliberate
  non-fatal degradation, not a hard error)
- The Memory Bank keys on `user_id` (which is `learner_id` here)
- Tool calls' `tool_context.search_memory(query)` is how downstream agents
  retrieve past events

## Pattern 6 — Dual-backed vector target (Firestore + Vertex AI Vector Search)

**Where the Journey uses it**: every level's vertex-embed step (Levels 1, 2, 5).

**Source**: `gemini_hackathon/cocoindex_flows/_shared/_vector_target.py` (Phase 2).

**Implementation**: `cocoindex_flows._shared._vector_target.get_vector_target(backend="firestore")`

What it teaches:
- One protocol (`VectorTarget.upsert_batch` / `find_nearest`), two backends
- Firestore `FindNearest` is the default (zero provisioning)
- Vertex AI Vector Search is opt-in via `VECTOR_BACKEND=vertex` (ScaNN ANN, sub-100ms p99)
- Both consume the same 1536-d `gemini-embedding-001` vectors (so a fair head-to-head benchmark is possible)

## Pattern 7 — Vertex AI Session Service (per-workshop state)

**Where the Journey uses it**: the orchestrator's session management.

**Source**: `way-back-home/level_2/backend/api/routes/chat.py` (`SESSION_MAP`).

**Implementation**: `gemini_hackathon/journey/journey_orchestrator/session_service.py`

What it teaches:
- 3-tier preference: `VertexAiSessionService` → `DatabaseSessionService` → `InMemorySessionService`
- The same SessionService instance is shared across the orchestrator's
  multiple level runs (so the workshop host can resume mid-journey)
- Persistent SQLite is the local-workshop default (no GCP setup needed)

## Pattern 8 — Function-node + agent-node in one edges list

**Where the Journey uses it**: every level.

**Source**: `adk2-tutorial/L1_graph_basics/workflow.py`

What it teaches:
- The whole point: function nodes are 0 LLM calls; agent nodes are 1 each.
  Use functions for I/O, math, parsing; use agents only for reasoning.
- The Journey's Level 1 is the canonical example: 1 BAML agent call
  (extract_baml) + 3 function nodes (fetch_syllabus_pdf, embed_chunks,
  upsert_vector). 1 LLM call total, 3 deterministic steps.
