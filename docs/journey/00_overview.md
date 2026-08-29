# British Isles Journey — overview

> **A 6-level immersive progressive educational experience built on the
> official syllabus processing pipeline for all 8 British Isles
> subnations.**

This is the single entry-point doc for the British Isles Journey
codelab series. The Journey is the gemini-hackathon submission's
user-facing surface: it turns the entire backend pipeline (BAML
syllabus extraction → Vertex embeddings → Document AI OCR → Firestore
Vector Search RAG → 4-path OCR consensus → MasteryLedger 4-backend
fan-out → FIBO JSON-native asset generation) into a one-evening,
workshoppable progression that a real workshop host can deploy to
their own GCP project.

It is the educational sibling of Google's [Way Back Home](../adk-examples/way-back-home/)
workshop — same proven structural ideas (per-level README + `#REPLACE`
markers + one Cloud Build per level + a central orchestrator), but
re-anchored on the official syllabus pipeline rather than a
rescue-on-an-alien-planet narrative.

## The 6 levels

| # | Title | Anchored on | Engine | Verifiable artefact |
|---|---|---|---|---|
| **0** | **Pick your subnation** | `gemini_hackathon.theming` + `gemini_hackathon.session` | Firestore session store | `journeys/{event}/participants/{uid}` profile + palette |
| **1** | **Syllabus extraction** | `baml_extracts/education/subjects/<sub>.baml` + `cocoindex_flows/_factory/four_stage` | Vertex AI `gemini-embedding-001` + Firestore `FindNearest` | Embedded chunks in `biep_<stage>_<subject>_<lang>_chunks` |
| **2** | **Past paper OCR** | `gemini_hackathon.ocr_ensemble.EnsembledExtractor` (4-path consensus) | Document AI + Gemini Vision + Gemma Vertex + pypdfium2 text-layer | `EnsembleResult` + NCCA page citations |
| **3** | **Mark an answer** | `baml_extracts/education/stages/leaving_cycle.baml` (marking) + `pillar1_grading.Pillar1GradingWorkflow` | ADK 2 `Workflow(JoinNode)` + Gemini 3.5 Flash | Per-criterion grade JSON + total |
| **4** | **Update mastery** | `gemini_hackathon.ledger.MasteryLedger` | Firestore 4-backend fan-out (achievements + mastery vectors + skill graph + GCS Markdown) | `MasteryUpdate` written across 3 Google-native backends |
| **5** | **Asset generation** | `baml_extracts/education/stages/leaving_cycle.baml` (BAML re-call) + `gemini_hackathon_assets_fibo` | Vertex embeddings + BAML `ExtractCurriculumSyllabus` + FIBO image gen | PNG saved to `gs://<project>-biep-assets/journey/<file>.png` |

## Codelab sequence

1. [00_overview](00_overview.md) — this doc
2. [01_level_0_pick_subnation](01_level_0_pick_subnation.md) — onboarding
3. [02_level_1_syllabus_extraction](02_level_1_syllabus_extraction.md) — Level 1
4. [03_level_2_past_paper_ocr](03_level_2_past_paper_ocr.md) — Level 2
5. [04_level_3_marking_scheme](04_level_3_marking_scheme.md) — Level 3
6. [05_level_4_mastery_update](05_level_4_mastery_update.md) — Level 4
7. [06_level_5_asset_generation](06_level_5_asset_generation.md) — Level 5
8. [07_adk_patterns_reference](07_adk_patterns_reference.md) — cross-cutting reference

## ADK 2 patterns used (the codelab series teaches these in passing)

| Level | ADK 2 pattern | Source for the pattern |
|---|---|---|
| 0 | `before_agent_callback` + `{key}` state templating | `adk2-tutorial/L0_first_agent` + `way-back-home/level_1` |
| 1 | `Workflow(edges=[(START, fetch, agent)])` | `adk2-tutorial/L1_graph_basics` |
| 2 | `ParallelAgent` + `JoinNode` | `adk2-tutorial/L2a_parallel_join` |
| 3 | `ParallelAgent` + `JoinNode` (reused pattern) | `adk2-tutorial/L1_graph_basics` |
| 4 | `RequestInput` (HITL pause between L4 and L5) | `loop-lab-table/hello_workflow` |
| 5 | (function nodes only — no LLM call) | — |
| All | Vertex AI `Memory Bank` (cross-workshop learner continuity) | `support-memory-lab/r3_last_month` |
| Orchestrator | Sequential `Workflow(edges=[...])` + `VertexAiSessionService` | `way-back-home/level_2/backend/api/routes/chat.py` + `support-memory-lab` |

## Quickstart for workshop hosts

```bash
git clone https://github.com/cianfhoghlaim/gemini-hackathon.git
cd gemini-hackathon
./journey/scripts/setup.sh    # venv + ADC + .env + Firestore seed + smoke
./journey/scripts/verify.sh   # 8-tick smoke gate
./journey/scripts/deploy_journey.sh  # Cloud Build + deploy
```

Then open the deployed service URL — the Gradio studio has one tab per
level, plus a "Run the whole journey" tab for the end-to-end one-click
demo.

## Cost estimate (per participant, end-to-end through all 6 levels)

| Backend | Approximate cost |
|---|---|
| Vertex AI embeddings (`gemini-embedding-001`) | ~$0.02 |
| Gemini 3.5 Flash (Levels 1, 3, 5) | ~$0.08 |
| Document AI (Level 2 path 1) | ~$0.04 |
| Firestore writes | <$0.01 |
| **Total per participant** | **~$0.15** |
| Cloud Run idle (scales to zero) | ~$0/month |
| Cloud Storage (asset bucket) | <$0.01/participant |

## Audit trail

`docs/ideas/journey_integration.md` records which `docs/ideas/` deep-research
doc informed which level + the explicit "out of scope" list — so a future
workshop host can pick up where this one leaves off.
