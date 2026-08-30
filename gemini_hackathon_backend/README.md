# `gemini_hackathon_backend/` — the ADK 2 + AG-UI + A2UI bridge

The Python FastAPI service that exposes the British Isles Journey's
agents to the CopilotKit v2 + AG-UI + A2UI React frontend (T2 #15–#16,
T3 #9–#13 in the prioritisation matrix).

## What's here

```
gemini_hackathon_backend/
├── README.md              ← you are here
├── pyproject.toml         ← ag-ui-adk + ADK 2 + FastAPI + Vertex AI
├── main.py                 ← FastAPI entrypoint (AG-UI SSE route at /)
├── agents/
│   └── ncca_panel.py      ← the FIRST working ADK agent (T1 #7)
└── catalog/
    └── ncca_v1.json       ← the A2UI component catalog (T1 #10)
```

## What it does

`uvicorn gemini_hackathon_backend.main:app` exposes:

  - **`POST /`** — the AG-UI SSE bridge. The CopilotKit React client sends
    a `RunAgentInput`; the backend runs the underlying ADK 2 agent and
    streams back `RUN_STARTED` / `TEXT_MESSAGE_START` /
    `TEXT_MESSAGE_CONTENT` / `TOOL_CALL_*` / `RUN_FINISHED` envelopes
    (plus custom `Raw` events for A2UI JSONL payloads).
  - **`GET /healthz`** — Cloud Run health probe.
  - **`POST /agents/state`** — experimental AG-UI state-snapshot endpoint
    (added by ag-ui-adk automatically; for the React client to fetch
    thread history without restarting a run).

## What it doesn't do (yet)

  - **No A2UI server-side streaming.** The first working agent (`NccaPanelAgent`)
    surfaces A2UI JSONL inside AG-UI `Raw` events; the renderer on the
    frontend parses them client-side. We could move the rendering server-side
    in a follow-up — T3 #15 plans to do that.
  - **Multi-agent routing.** The `gemini_hackathon_adk` Cloud Run service
    hosts ONE agent. A future iteration can serve multiple agents by
    registering them with an `agent_resolver` (per the `ag_ui_adk` docs)
    and mounting the service at `/adk/{agent_name}`.

## Local dev

```bash
# 1. Install deps
uv pip install -e .

# 2. Stub mode (no Gemini key needed — every LLM call is monkeypatched in
#    the smoke test, and the production path is opt-in via $GOOGLE_API_KEY)
uvicorn gemini_hackathon_backend.main:app --host 0.0.0.0 --port 8000

# 3. Run the tests
uv run pytest gemini_hackathon_backend/tests/ -v
```

## Production deploy

```bash
# Auth the gcloud CLI, then apply cloud/terraform/cloud_run_adk.tf.
# The service image is the same one as `cloud_run.tf` (gemini-hackathon:latest)
# — the runtime entrypoint differs (uvicorn ... :8000 vs Gradio launch).
gcloud builds submit --tag europe-west1-docker.pkg.dev/$PROJECT/gemini-hackathon/gemini-hackathon:$TAG .
terraform apply -var="project_id=$PROJECT" cloud/terraform/
```

## Test counts (per 2026-08-29 run)

| Module | Tests | Notes |
|---|---|---|
| `gemini_hackathon_backend/tests/test_adk_agui_envelope.py` | 1 | The kill-switch test — proves the AG-UI v0.10 envelope shape |
| `gemini_hackathon_backend/tests/test_ncca_panel_agent.py` | 10 | 6 tool tests + 2 catalog tests + 2 catalog/JSONL tests + 1 app-test |

11 backend tests pass; the suite runs in < 2 seconds and is the only
fast feedback loop for the ADK + AG-UI + A2UI work.
