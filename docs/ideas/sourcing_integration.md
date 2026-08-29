# Sourcing pipeline audit trail — which existing pipeline / idea doc informed which file

> **Audit trail for the Phase 2 sourcing pipeline** (local-dev +
> GCP-first sourcing + ADK 2 SourcingCopilot). Same shape as
> `journey_integration.md` — each new file below is annotated with the
> canonical example it lifts from.

## In scope — absorbed

| Idea doc / existing pipeline | File | How absorbed |
|---|---|---|
| `gemini_hackathon/dlt_pipelines/official_doc_fetcher.py:KNOWN_OFFICIAL_URLS` | `gemini_hackathon/journey/sourcing/pipeline.py` (the `catalog_rows` resource) | The catalog is inlined in `pipeline.py` because the source module re-imports `dlt` at the top of its `__init__.py`, which fails offline. Same URLs, same per-row shape; the test `tests/test_sourcing_catalog_sync.py` will guard drift between the two once we add it. |
| `docs/ideas/BAML, DLT, and AI Workflow Integration.md` | `gemini_hackathon/journey/sourcing/pipeline.py` (DLT pipeline structure) | The 3-resource split (catalog_rows / artifact_upserts / sourcing_runs) + `merge` for the per-doc table + `replace` for the static catalog + `append` for the run history is exactly the pattern this doc argues for. |
| `docs/ideas/British Isles Education Map.md` | `gemini_hackathon/journey/sourcing/schemas.py` (the 8-subnation `ActiveSubnation` table) | The `subnation_slug` field on `ContentArtefactDoc` matches `gemini_hackathon/session/schema.py:ActiveSubnation` so the journey orchestrator (Stream C.3) can join them without an extra lookup. |
| `docs/adk-examples/adk2-tutorial/L0_first_agent/agent.py` | `gemini_hackathon/journey/sourcing_copilot/agent.py` | The `Agent` + `Runner.run_async()` + multi-turn REPL pattern is lifted verbatim. |
| `docs/adk-examples/adk2-tutorial/L1_graph_basics/workflow.py` | `gemini_hackathon/journey/sourcing_copilot/agent.py` (FunctionTool-as-sub-agent) | The 3 sub-agent roles are FunctionTool children of the root Agent — the canonical "function node + agent node in one edges list" pattern. |
| `docs/adk-examples/way-back-home/level_2/backend/api/routes/chat.py` (SessionService tier preference) | `gemini_hackathon/journey/sourcing/fs.py:get_firestore` | Same 3-tier preference (VertexAiSessionService → DatabaseSessionService → InMemoryFirestore), with the offline in-memory tier added as a 4th because `google-cloud-firestore` can't be imported when the pydantic conflict blocks `uv sync`. |
| `docs/adk-examples/loop-lab-table/hello_workflow.py` (RequestInput HITL) | Not directly used — `pipeline.py` is a CLI, not a workflow. The HITL pattern lives in `gemini_hackathon/journey/journey_orchestrator/workflow.py:request_human_confirmation` (Phase Stream C.3). |
| `docs/adk-examples/monstertix/MODULE 5` (LongRunningFunctionTool + RequestInput) | Same — the HITL pause between L4 and L5 in the journey is the canonical application. |
| `docs/adk-examples/support-memory-lab/r3_last_month/` | `gemini_hackathon/journey/sourcing_copilot/agent.py` (the `baml_extracted` flag mirrors the Memory Bank write) | The copilot's "what's normalised but not BAML-extracted?" question is the exact equivalent of "what's not in the Memory Bank yet?" in support-memory-lab. |
| `docs/ideas/Celtic Data Scraping and Integration Plan.md` (collect-then-process pipeline shape) | `gemini_hackathon/journey/sourcing/pipeline.py` (the 4-step pipeline) | The "collect everything first, then filter, then process" sequence the doc argues for is exactly the sourced → filtered → normalised → extract-baml sequence. |
| `docs/ideas/Knowledge-graph-infrastructure.md` (dual-engine graph + vector) | `gemini_hackathon/journey/sourcing/schemas.py:ContentArtefactDoc` (the per-doc provenance dict) | The doc argues for "embed provenance as a first-class field, not a side table"; we do that via `provenance: dict[str, Any]` on every artefact. |
| `docs/ideas/Backend Strategy For Educational Tutoring System.md` (the Irish maths curriculum's Strand → Topic → LO hierarchy) | The `stage_slug` field on `ContentArtefactDoc` matches `L0_SUBNATIONS` so the journey orchestrator's Level 0-5 levels can filter by stage. |

## Out of scope — explicitly NOT absorbed

| Idea doc | Why excluded |
|---|---|
| [x402 / EAS / UMÁ oracle / Brehon tokens](../ideas/Agentic%20Education%20Platform%20Development.md) | The sourcing pipeline is a *content preparation* layer, not an economic layer. The Journey's expansion pack home for the token stack still applies (per `docs/ideas/journey_integration.md`). |
| A2A swarm via Kafka | The copilot's 3 sub-agents are `FunctionTool`s under one `Agent`, not 3 separate Agents talking over A2A. Same trade-off as the journey orchestrator's Phase 3.2. |
| BAML BatchExtractGoldPattern (from `baml_src/`) | The pipeline calls one BAML function per artefact (`ExtractCurriculumSyllabus`); the BAML batch patterns are for cross-document extraction at Level 1, not per-doc ingestion. Out of scope here. |
| MegaTTS3 for bilingual EN/GA TTS | The sourcing pipeline produces text + structured provenance, not audio. TTS belongs in Level 5's asset generation (FIBO is image-only; TTS would be a future expansion pack asset type). |

## Decisions made during integration

1. **Firestore path = A** — every collection under `journeys/{event_code}/...`
   (per the user's choice). This means the copilot, the journey
   orchestrator, and the studio all see one document tree per workshop.

2. **Normalise step = 2** — 3 paths (pypdfium2 text-layer + Document AI +
   Gemini 3.5 Flash native PDF), pick the longest non-whitespace extraction
   as the winner. Local-dev falls back to pypdfium2 only.

3. **Catalog duplication** — `pipeline.py`'s `KNOWN_OFFICIAL_URLS` is
   duplicated from `gemini_hackathon/dlt_pipelines/official_doc_fetcher.py`
   because the source module re-imports `dlt` at the top of its `__init__.py`
   (which fails offline). A test (`tests/test_sourcing_catalog_sync.py`)
   will assert the two stay in sync — TBD in a follow-up.

4. **In-memory Firestore fallback** — when `google-cloud-firestore`
   isn't importable (the pydantic-conflict path), the pipeline uses
   `InMemoryFirestore` instead. This is the same fallback pattern
   `gemini_hackathon/journey/level_0_pick_subnation/app.py` uses.

## How to verify this audit trail

```bash
# 1. Every new file imports from the canonical examples it lists:
grep -rn "adk2-tutorial\|way-back-home\|loop-lab-table\|support-memory-lab\|monstertix\|celtic_data\|knowledge-graph-infrastructure" \
  gemini_hackathon/journey/sourcing gemini_hackathon/journey/sourcing_copilot

# 2. The catalog stays in sync (FUTURE — add tests/test_sourcing_catalog_sync.py):
.venv/bin/python -c "
from gemini_hackathon.journey.sourcing.pipeline import KNOWN_OFFICIAL_URLS as a
"  # would compare against gemini_hackathon.dlt_pipelines.official_doc_fetcher.KNOWN_OFFICIAL_URLS

# 3. No level imports anything from the out-of-scope list:
! grep -rn "x402\|EAS\|cumul\|pinginn\|screpall\|MegaTTS3" \
  gemini_hackathon/journey/sourcing gemini_hackathon/journey/sourcing_copilot && echo OK
```
