# British Isles Journey — README

> **An immersive 6-level progressive educational experience that drives
> participants through the full official syllabus processing pipeline for
> all 8 British Isles subnations, built on Google ADK 2 and Google Cloud.**

The Journey is the gemini-hackathon submission's user-facing surface: it
turns the entire backend pipeline (BAML syllabus extraction → Vertex
embeddings → Document AI OCR → Firestore/Vector Search RAG → 4-path OCR
consensus → MasteryLedger 4-backend fan-out → FIBO JSON-native asset
generation) into a one-evening, workshoppable progression that a real
workshop host can deploy to their own GCP project.

It is the educational sibling of Google's [Way Back Home](../docs/adk-examples/way-back-home)
workshop — same proven structural ideas (per-level README + `#REPLACE`
markers + one Cloud Build per level + a central orchestrator), but
re-anchored on the official syllabus pipeline rather than a
rescue-on-an-alien-planet narrative.

## The 6 levels

| # | Title | What you do | ADK 2 pattern used |
|---|---|---|---|
| **0** | **Pick your subnation** | Choose your jurisdiction (1 of 8); auto-apply the matching palette; write your first Firestore doc | `before_agent_callback` + `{key}` state templating |
| **1** | **Syllabus extraction** | BAML extracts the LO from a syllabus chunk → Vertex embeds → Firestore `FindNearest` indexes | `Workflow(edges=[(START, fetch_pdf, baml_extract, embed, upsert_vector)])` |
| **2** | **Past paper OCR** | Upload a PDF; 4-path ensemble (Document AI + Gemini Vision + Gemma Vertex + pypdfium2 text-layer) extracts; consensus vote picks the winner | `ParallelAgent` + `JoinNode` |
| **3** | **Mark an answer** | Per-criterion graders (one BAML call per marking criterion) run in parallel; `JoinNode` aggregates; strategy agent writes the grade | `ParallelAgent` + `JoinNode` (Pillar 1) |
| **4** | **Update mastery** | `MasteryLedger.update_mastery()` writes to 4 backends in one shot (Firestore rows + mastery vectors + skill graph + GCS Markdown) | Per-backend fan-out + optional `RequestInput` HITL pause |
| **5** | **Generate an asset** | Ask a question grounded in the syllabus → BAML extracts a `VisualConcept` → FIBO generates a JSON-native curriculum-aligned asset | `Workflow(edges=[..., search_syllabus, baml_extract_visual, fibo_generate, save_to_gcs])` |

The Journey orchestrator chains all 6 in a single sequential `Workflow`
with `{key}` state templating passing outputs forward. The participant can
pause for human confirmation between Level 4 and Level 5 (`RequestInput`
pattern from `loop-lab-table/hello_workflow.py`).

## Quickstart

### For workshop participants

```bash
git clone https://github.com/cianfhoghlaim/gemini-hackathon.git
cd gemini-hackathon

# Bootstrap the journey (Cloud Shell)
./journey/scripts/setup.sh
# ...prompts for: event code, default subnation, admin email...

# Start with Level 0 — 5 minutes to "I'm onboarded"
cd journey/level_0_pick_subnation
python customize.py
```

### For workshop hosts (self-hostable)

```bash
./journey/scripts/setup-infrastructure.sh   # creates Firestore, enables APIs,
                                           # writes journeys/{event_code}
./journey/scripts/admin_create_event.py your-event-code "British Isles Journey Workshop"
./journey/scripts/deploy_journey.sh        # Cloud Build -> Cloud Run
```

The deployed service is available at `https://gemini-hackathon-journey-<hash>.run.app/`.
The progress dashboard (per-learner status across the 6 levels) is at
`https://<service>/e/<event-code>`.

### For the demo / hackathon submission

`mise run journey:serve` runs the studio locally (Gradio on `localhost:7860`).
The full pipeline runs end-to-end without GCP credentials by using the
in-memory fallbacks every backend ships with (`FirestoreVectorTarget`,
`FirestoreLedger`, `MasteryLedger.default()`).

## Architecture overview

```
                    Journey orchestrator (ADK 2 sequential Workflow)
                                   │
            ┌──────────┬───────────┼───────────┬──────────┬──────────┐
            ▼          ▼           ▼           ▼          ▼          ▼
         Level 0    Level 1     Level 2     Level 3    Level 4    Level 5
         pick      syllabus    4-path OCR  mark ans  update     gen asset
                   extract     consensus             mastery
            │          │           │           │          │          │
            └──────────┴───────────┴───────────┴──────────┴──────────┘
                                   │
                                   ▼
                          Cloud Run service:
                          gemini-hackathon-journey
                          (FastAPI + Gradio studio)
                                   │
                                   ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ Firestore  │  │ Vertex AI  │  │ Document AI│  │ GCS         │
   │ (sessions, │  │ (embeddings│  │ + Gemini   │  │ (syllabus  │
   │  ledger,   │  │  + Gemini  │  │  Vision +  │  │  PDFs,      │
   │  skills,   │  │  chat)     │  │  Gemma +   │  │  generated  │
   │  mastery)  │  │            │  │  pypdfium2)│  │  assets)    │
   └────────────┘  └────────────┘  └────────────┘  └────────────┘
                                   │
                                   ▼
                          Cloud Run Jobs (Phase 7):
                          ingest-corpus, embed-index, ocr-consensus
                          triggered nightly by Cloud Scheduler
```

## Cost estimate

Per-participant, end-to-end (all 6 levels):
- Vertex AI embeddings (`gemini-embedding-001`): ~$0.02
- Gemini 3.5 Flash (Level 1 + 3 + 5): ~$0.08
- Document AI (Level 2 path 1): ~$0.04
- Firestore writes: <$0.01

**Total: ~$0.15/participant** for the full Journey.

Cloud Run idle: ~$0/month (scales to zero).

## Documentation

| Doc | Audience |
|---|---|
| [`docs/journey/00_overview.md`](docs/journey/00_overview.md) | Workshop hosts + participants (entry point) |
| [`docs/journey/01_level_0_pick_subnation.md`](docs/journey/01_level_0_pick_subnation.md) … `06_level_5_certificate.md` | Participants (one codelab per level) |
| [`docs/journey/07_adk_patterns_reference.md`](docs/journey/07_adk_patterns_reference.md) | Cross-cutting reference for the ADK 2 patterns each level uses |
| [`docs/ideas/journey_integration.md`](../docs/ideas/journey_integration.md) | Audit trail: which `docs/ideas/` deep-research doc informed which level + the explicit "out of scope" list |

## Status

- [x] Stream A — scaffolding + Level 0 + journey orchestrator skeleton
- [x] Stream B — Levels 1, 2, 3 (syllabus, OCR, marking)
- [x] Stream C — Levels 4, 5 (mastery update, asset generation)
- [x] Stream D — unified Gradio studio + Cloud Run deploy
- [x] Stream E — codelabs, integration audit, tests

## Built on

- [Google ADK 2](https://adk.dev) — agent framework (Workflow, ParallelAgent, JoinNode, before_agent_callback, RequestInput, Memory Bank)
- [Vertex AI](https://cloud.google.com/vertex-ai) — `gemini-embedding-001`, Gemini 3.5 Flash, Gemma 4 on Model Garden
- [Document AI](https://cloud.google.com/document-ai) — Layout Parser
- [Firestore](https://firebase.google.com/docs/firestore) — `FindNearest` (vector search) + native FindNearest + skill graph nodes/edges + achievement ledger
- [Cloud Run](https://cloud.google.com/run) + [Cloud Build](https://cloud.google.com/build) + [Cloud Workflows](https://cloud.google.com/workflows) + [Cloud Scheduler](https://cloud.google.com/scheduler)
- [Bria FIBO](https://www.bria.ai) — JSON-native image generation for Level 5
