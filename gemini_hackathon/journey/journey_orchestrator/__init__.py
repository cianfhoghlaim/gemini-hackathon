"""gemini_hackathon.journey.journey_orchestrator — the ADK 2 Workflow that chains all 6 levels.

This is the canonical pattern lifted from `adk2-tutorial/L1_graph_basics/`
(function node + agent node in one Workflow) + `way-back-home/level_1/`'s
`before_agent_callback` for participant state hydration.

Two responsibilities:

  - **`callback_before_agent.py`** (this package): the canonical
    `before_agent_callback` that runs BEFORE every level's agent and
    populates `ctx.state` with the per-participant Firestore values:
    `{learner_id}`, `{subnation}`, `{subject}`, `{event_code}`.

  - **`workflow.py`**: the ADK 2 sequential `Workflow(edges=[...])` that
    chains Levels 1-5, with one `RequestInput` between Level 4 and Level 5
    for human-in-the-loop confirmation (per `loop-lab-table/hello_workflow.py`).

  - **`session_service.py`** + **`memory_service.py`**: Vertex AI
    `VertexAiSessionService` + (optional) `VertexAiMemoryBankService`
    wiring — long-term per-learner memory across workshop runs (per
    `support-memory-lab/r3_last_month`).

The orchestrator itself is the entry point for the Cloud Run `journey_studio`
service — one container hosts the FastAPI + Gradio studio + ADK 2 runner.
"""
