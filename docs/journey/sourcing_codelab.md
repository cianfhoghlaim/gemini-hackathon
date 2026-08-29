# Sourcing pipeline — codelab

> **Phase 2 of the GCP-first refactor.** This codelab walks you through
> the local-dev → GCP-first sourcing pipeline: pull every catalog URL
> into one normalised Firestore layer (`journeys/{event_code}/
> content_artefacts/`), then use the SourcingCopilot (an ADK 2 agent) to
> decide what to exclude + what to deploy next.

The pipeline's job is to get all 34 catalog rows into one place,
normalised, and **filtered** (so the next stage — the Journey
orchestrator's Level 1+ — works against a clean corpus).

## The 4 steps (one CLI command each)

```bash
# 1. SOURCE — fetch every catalog URL, persist bytes, upsert content_artefacts.
mise run sourcing:sourced
# (or: python -m gemini_hackathon.journey.sourcing.pipeline --step=sourced)

# 2. NORMALISE — read cached bytes, extract text (3 paths: pypdfium2 text-layer
#    + Document AI + Gemini 3.5 Flash native PDF), write derived JSON to GCS.
mise run sourcing:normalised

# 3. FILTER — the workshop host's "this doc is out of scope" tool. Marks
#    content_artefacts[].excluded=True. The copilot's ExcludeDocumentAgent
#    walks you through the next-10-candidates flow.
python -m gemini_hackathon.journey.sourcing.pipeline --step=filtered \
    --exclude abc123...:corrupted \
    --exclude def456...:language_unsupported

# 4. STATUS — the 9-row read-only summary the copilot + the studio show.
mise run sourcing:status
```

Behind each step:
- The **sourced** step runs the 3-DLT-resource pipeline (catalog_rows +
  artifact_upserts + sourcing_runs), writes the catalog + the
  `content_artefacts` table, persists bytes via `cache.write_bytes` (local
  FS in dev, GCS in prod).
- The **normalised** step iterates `content_artefacts[excluded=False]`,
  reads cached bytes, runs the 3 normalise paths (pypdfium2 always;
  Document AI + Gemini when GCP_PROJECT_ID is set), picks the winner by
  text length, writes the derived JSON.
- The **filtered** step is a Firestore-only update — marks
  `excluded=True` with the reason from the closed vocabulary
  (`EXCLUDED_REASONS`).
- The **status** step is a Firestore aggregation over the
  `content_artefacts` collection.

## The SourcingCopilot (ADK 2 agent)

An ADK 2 `Agent` with 3 sub-agent roles (each a `FunctionTool`):

  1. **SourcingStatusAgent** — answers "what's sourced? / how many
     normalised? / any failures?" via the 9-row status table.
  2. **ExcludeDocumentAgent** — answers "should I exclude this?" via
     `mark_excluded(sha256, reason)`. Validates the reason against the
     closed vocabulary.
  3. **DeploymentAgent** — answers "what should I deploy next?" via
     `recommend_next_steps()` + `list_cloud_run_services()` +
     `list_scheduled_jobs()`.

Three ways to invoke:

```bash
# 1. One-shot status (the canonical 9-row table)
python -m gemini_hackathon.journey.sourcing_copilot.cli --status

# 2. List deployed Cloud Run services + Scheduler jobs
python -m gemini_hackathon.journey.sourcing_copilot.cli --list-services

# 3. Mark one doc excluded
python -m gemini_hackathon.journey.sourcing_copilot.cli \
    --exclude abc123...:corrupted

# 4. Interactive REPL (uses ADK 2 Runner.run_async — the same pattern as
#    adk2-tutorial/L0_first_agent/agent.py:ask())
python -m gemini_hackathon.journey.sourcing_copilot.cli
# > what's sourced?
# > exclude def456...:duplicate
# > exit
```

The copilot is also a tab in the unified Gradio studio
(`gemini_hackathon_gradio/journey_studio/` — the "SourcingCopilot —
interactive deploy guide" tab).

## Local-dev vs GCP-prod

The single env var that flips the boundary is `GOOGLE_PROJECT_ID`:

| Env | Local-dev | GCP-prod |
|---|---|---|
| unset | Firestore → in-memory dict; bytes → local FS; Document AI + Gemini disabled | — |
| set + emulator | Firestore emulator; bytes → local FS; Document AI + Gemini disabled | — |
| set + gcloud auth | real Firestore; bytes → local FS; Document AI + Gemini enabled if libs installed | real Firestore; bytes → GCS; Document AI + Gemini enabled |

Use `--emulator` to start the Firestore emulator:
```bash
gcloud emulators firestore start --host-port=localhost:8080 &
export FIRESTORE_EMULATOR_HOST=localhost:8080
python -m gemini_hackathon.journey.sourcing.pipeline --step=sourced --emulator
```

## The canonical Firestore tree

```
journeys/{event_code}/
  catalog/{source_key}/{subject_slug}/{language}            ← 34 rows, DLT replace
  content_artefacts/{sha256}                                 ← 1 row per fetched byte,
                                                               DLT merge on sha256
  sourcing_runs/{run_id}                                       ← append-only history
```

The studio's Level 0 onboarding already creates `journeys/{event_code}/
participants/{uid}` — the same event tree, different sub-collection.

## Why this design

DLT best practices the pipeline follows (per `docs/ideas/BAML, DLT,
and AI Workflow Integration.md`):
- `primary_key` on every resource so re-runs are idempotent.
- `write_disposition="replace"` for the static catalog; `merge` for the
  per-document artefacts (so partial runs don't duplicate rows).
- `incremental` *not* set — we want a full re-write per run because
  catalog URLs can change between invocations.
- One DLT pipeline per orchestrator-level run, not per step — the
  `sourcing_runs` resource gives per-step visibility.

The ADK 2 copilot follows the same patterns as
`adk2-tutorial/L0_first_agent/` + `L1_graph_basics/` — `Agent` +
`FunctionTool` + `Runner.run_async()`. The CLI's `_interactive_repl`
implements the ask-loop pattern verbatim.
