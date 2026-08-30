# gemini_hackathon — Architecture (August 2026 refactor)

> The All Things Agentic 2026 hackathon submission. The British Isles
> Education Platform — Aistear → Bunscoil → MeanScoil → Scoil Sinsearach →
> Ollscoil — across **9 jurisdictions** (Ireland + England active;
> **UK NCCE** as the cross-jurisdiction Computing curriculum showcase
> shipped 2026-08-31; NI / Wales / Scotland / IoM / Jersey / Guernsey
> are Phase 2).

This ARCHITECTURE.md describes the current state after the August 2026
refactor (17 W0–W14 workstreams + 4 NEW 2026-08-30 changes + 3 NEW
2026-08-31 changes = **24 total openspec changes**). The diagram is
drawn from the running code (per the `adk2-tutorial/L5_capstone` lesson:
"the picture is read out of `Workflow.graph.edges`").

## 1. High-level layout

```
gemini_hackathon/
├── pyproject.toml + requirements.txt + mise.toml
├── gemini_hackathon/                       ← the Python package
│   ├── agents/                             ← W7 — 5 stage coordinators + 5 pillars
│   ├── assets/                             ← the image-gen router
│   ├── call_llm.py + backend.py            ← the LLM gateway
│   ├── certificate/                        ← W14 — the LC/JC certificate pipeline
│   ├── cli.py + __main__.py + compare.py
│   ├── knowledge_graph/                    ← W8 — hybrid search (LanceDB + FalkorDB)
│   ├── ledger/                             ← W9 — skill-progression ledger
│   ├── memory/                             ← W8 — MarkdownMemoryService
│   ├── models/ + model_registry.py
│   ├── observability.py
│   ├── ocr.py + ocr_ensemble.py
│   ├── progression/                       ← existing LC/JC certificate schema
│   ├── session/
│   ├── sources.py + theming.py
│   └── subnations.py                       ← W11 — 9 jurisdictions
├── gemini_hackathon_gradio/                ← W3 — the 5 editorial studios + an_learning_graph (2026-08-31)
│   ├── _common/                            ← shared library (theme, baml, pclm, hlml, ...)
│   ├── an_scrudu/                          ← LC past-paper heatmap studio
│   ├── anam_education/                     ← 7-feature integration studio
│   ├── oideachais_mission_control/         ← 5-stage control
│   ├── oideachais_pdf_review/              ← human review
│   ├── editorial_studio/                   ← W12 — the big canvas (Cloud Run + gr.Workflow)
│   └── an_learning_graph/                  ← 2026-08-31 — the 4-tab NCCE studio
├── gemini_hackathon_assets_fibo/           ← W10 — the FIBO image-gen pipeline
│   ├── models.py, schemas.py, cache.py, assets.py
│   ├── processors/texture_processor.py
│   └── education_prompts.py                ← 14 subjects × 5 stages prompt bank
├── gemini_hackathon_backend/               ← 2026-08-30 — the ADK 2 Cloud Run service
│   ├── agents/ + main.py + observability.py
│   ├── catalog/                            ← Lake namespace adapter (Phase 3 GCP-first)
│   ├── pyproject.toml + tests/
├── baml_extracts/                          ← BAML contracts (existing + 2026-08-31 learning_graph.baml)
├── baml_extracts_education/                ← W4+W5 — lifted from cianfhoghlaim
│   ├── stages/{aistear,primary,junior_cycle,senior_cycle}.baml
│   ├── celtic_curriculum.baml, player_assessment.baml
│   └── certification_criteria.baml         ← W14 (referenced)
├── cocoindex_flows/                        ← W5 + 2026-08-30 + 2026-08-31
│   ├── _shared/                             ← shared_lifespan + _vector_target + _vertex_embedder + _docling_grid_segmenter (2026-08-31)
│   ├── ireland/                             ← per-stage embedding apps
│   ├── pdf/                                 ← Phase 2b Docling converter (2026-08-30)
│   ├── uk_ncce/                             ← 2026-08-31 NCCE learning graph App + pedagogy_cache
│   ├── equivalency/                         ← Phase 4a equivalency graph
│   ├── education/                           ← W14 BAML extraction target
│   └── _factory/                            ← bi_jurisdiction + four_stage
├── dlt_pipelines/                           ← W5 + 2026-08-30 + 2026-08-31
│   ├── ireland/                              ← 6 NCCA subject pipelines
│   ├── uk_ncce_learning_graphs.py            ← 2026-08-31 (jurisdiction #9)
│   ├── _base/jurisdiction_pipeline_base.py
│   ├── official_doc_fetcher.py + corpus_downloader.py + pdf_downloader.py
│   └── _shared.py
├── data/
│   ├── ireland/ncca_policy/                ← W2 — 5 NCCA policy PDFs
│   ├── bi_ep/                              ← 2026-08-30 PDF→Markdown substrate
│   │   ├── syllabi_raw/                      ← raw PDFs (gitignored)
│   │   │   ├── ireland/                       ← NCCA + SEC + DES PDFs
│   │   │   └── uk_ncce/                       ← 2026-08-31 (5 NCCE PDFs)
│   │   ├── syllabi_md/                       ← Docling-converted Markdown
│   │   └── extracted_syllabi.sqlite          ← the BAML extraction target
│   ├── leabharlann/                         ← W6 — leabharlann corpus (manifests only)
│   ├── equivalencies/, jurisdictions/, marking_schemes/, policies/, sources/, syllabi/
├── themes/                                  ← awarding-body palettes (NCCA, AQA, OCR, ...)
├── web/                                    ← Firebase-native TanStack Start web
│   └── src/routes/learning-graphs/         ← 2026-08-31 NCCE landing page
├── hf_spaces/                               ← W13 + 2026-08-31 (6 headline demos)
├── orchestration/                           ← 2026-08-30 + 2026-08-31
│   ├── defs/                                ← 5-layer Dagster defs tree
│   │   ├── 1_ingestion/
│   │   ├── 2_materials/
│   │   ├── 3_model_lifecycle/               ← NCCE learning graph + equivalency + pedagogy assets
│   │   ├── 4_asset_generation/
│   │   └── 5_agent_ops/
│   ├── partitions.py
│   └── storage/                             ← BigQuery client + DuckLake client
├── openspec/changes/                       ← W16 + 2026-08-30 + 2026-08-31 — 26 openspec changes
├── docs/                                   ← W15 — the docs (TUATHA_CONSOLIDATION_MAP, KNOWN_ISSUES, LEARNING_GRAPH_SHOWCASE, ...)
├── notebooks/                              ← the 14 marimo + ipynb walkthroughs (00_theming … 13_pedagogy_overlay)
├── cloud/                                  ← GCP-native IaC
│   └── terraform/
│       ├── cloud_run_adk.tf + cloud_run.tf + cloud_run_jobs.tf + cloud_run_journey.tf
│       └── modules/                          ← 11 Terraform modules (per Phase 5 GCP-first IaC)
├── cloudbuild.yaml + mise.toml + README.md
└── firestore.{json,rules,indexes.json}     ← Firebase-native schema + NCCE collections
```

## 2. The 5-stage British Isles education palette

```
Aistear (0-6) → Bunscoil (4-12) → MeanScoil (12-15) → Scoil Sinsearach (15-19) → Ollscoil (Phase 2)
```

The Celtic 5-element palette (Talamh/Uisce/Tine/Aer/Anam) was REPLACED with
the 5-stage education palette in W3:

```
aistear          dawn-orange       #e8915c
bunscoil         sea-blue          #1e80c6
meanscoil        meadow-green      #28955e
scoil_sinsearach harvest-gold      #cc9966
ollscoil         scholarship-indigo #5a4fcf
```

Hades Shadow-First is preserved as the dark-mode foundation.

## 3. The 14-subject SUBJECT_WIRING_REGISTRY

W4 — the canonical routing table for the ADK 2 stage coordinators:

```
8 NCCA subjects + 6 NCCA-adjacent = 14 total

SUBJECT_WIRING_REGISTRY: dict[slug, SubjectAgentWiring]
  where SubjectAgentWiring has 8 fields:
    ncca_subject / module_slug / display_name / baml_prefix /
    langfuse_trace_name / cognee_dataset / memory_namespace / litellm_routing_key

The routing keywords (`ROUTING_KEYWORDS`) classify learner messages to
the right subject bucket (10/10 typical questions route correctly in
the smoke test).
```

## 4. The 5 ADK 2 stage coordinators

W7 — `gemini_hackathon/agents/stages/<stage>/__init__.py` each builds
an ADK 2 `Workflow(name, description, edges=[...])`:

```
stages/
├── early_years/          Aistear 4-themes workflow
├── primary/              Bunscoil 12-area parallel-fetch + JoinNode (Pillar 1)
├── junior_cycle/         MeanScoil 10-subject dict-edge router (Pillar 1/2)
├── leaving_certificate/  Scoil Sinsearach 14-subject router + 14 specialists
└── cross_subject/        Pillar 3 dynamic fan-out for the 5 NCCA Key Competencies
```

The 5 reusable **ADK 2 pillars** in `gemini_hackathon/agents/workflows/`:

```
pillar1_grading.py          L2a parallel_join (parallel grading + JoinNode)
pillar2_collab_tutor.py     L3a collaborative (sub_agents + mode="single_turn")
pillar3_dynamic_research.py L4a flat_research (parallel_worker + synthesise)
pillar4_long_running.py      monstertix pattern (LongRunningFunctionTool + RequestInput)
pillar5_eval_flywheel.py     loop-lab-table pattern (adk eval + adk optimize GEPA)
```

## 5. The 5 NCCA policy PDFs as the source of truth

W2 — `data/ireland/ncca_policy/` contains 5 PDFs lifted verbatim from
`cianfhoghlaim/leaving_certificate/`:

```
SC-L1-L2-Programme-Statement.pdf
key-competencies-in-senior-cycle_en.pdf
the-potential-of-online-learning-environments_en.pdf
the-potential-of-technology-to-support-online-certification-and-reporting.pdf
scr-advisory-report_en.pdf
```

Every claim on every generated LC/JC certificate cites a page from one
of these PDFs (W14).

## 6. The LC/JC certificate pipeline (W14 — the showcase)

7 stages:

```
extract_criteria     → BAML extract from the 5 NCCA PDFs
decompose_outcomes    → split learner outcomes by mastery score
extract_paper+marking → DLT from data/ireland/lc_subject/
search_official       → RAG over the 5 NCCA policy corpus
generate_background   → Flux + W10 prompt bank (subject × stage)
compose_certificate   → PIL (1200×850): subject header + award pill +
                         learner name + top-5 outcomes + Key Competencies
                         strip + provenance footer + UNOFFICIAL banner
save_to_provenance     → W9 MasteryLedger (Firestore + Vertex AI Vector Search + Firestore graph)
```

Output: `CertificateRecord` with PNG (~80 KB) + PDF (~700 B) + provenance
+ skill-progression summary. **Every claim cites a NCCA PDF page.** The
UNOFFICIAL banner is always present (per the user's spec).

## 7. The skill-progression ledger (W9 — Google-native as of the GCP-first refactor)

4 backends unified by `MasteryLedger` facade — Convex was never deployed
(the original backend's own docstring called it a dev-only stub) and is
replaced outright, not migrated:

```
Firestore         UI-facing achievement rows (per-learner + per-outcome)
                   — replaces ConvexLedger
VectorTarget       320-dim -> 1536-d per-learner mastery vectors (5 Key
                   Competencies x 8 subjects x 4 levels x 2 languages),
                   dual-backed: Firestore FindNearest (default) or
                   Vertex AI Vector Search (VECTOR_BACKEND env var) —
                   replaces LanceDB
Firestore graph    skill-prerequisite graph (skill -> unlocks ->
                   assessed_by_artefact) as a `skillEdges` collection —
                   replaces FalkorDB
MarkdownMemory     per-user long-term memory (W8 — from monstertix),
                   persisted to Cloud Storage in production
```

`MasteryLedger.update_mastery(MasteryUpdate)` writes atomically to all 4.
`MasteryLedger.get_learner_state(learner_id)` reads all 4.

See `gemini_hackathon/ledger/backends/firestore_ledger.py` and
`gemini_hackathon/ledger/backends/firestore_graph.py`.

## 8. The 5 editorial studios (W3) + the 6 HF Spaces (W13 + 2026-08-31)

```
gemini_hackathon_gradio/
├── _common/                                shared library
│   ├── theme.py (5-stage British Isles palette + Hades)
│   ├── baml_client.py (3-tier LiteLLM → Unsloth → HF)
│   ├── baml_pydantic_bridge.py
│   ├── pclm_emitter.py + hlml_emitter.py
│   ├── anam_bonneagar.py (Anam Faisnéise footer)
│   ├── hf_hub_push.py + demo_recorder.py
├── an_scrudu/             LC past-paper heatmap
├── anam_education/        7-feature integration
├── oideachais_mission_control/  5-stage control
├── oideachais_pdf_review/      human review
├── editorial_studio/      W12 — the big canvas (Cloud Run + gr.Workflow)
└── an_learning_graph/     2026-08-31 — the 4-tab NCCE studio (Render / Equivalencies / Generate / Pedagogy overlay)

hf_spaces/                 ← published to cianfhoghlaim/gemini_hackathon_<stage>
                            + cianfhoghlaim/gemini_hackathon_learning_graphs (2026-08-31)
```

Each Space has README.md (HF frontmatter) + app.py (lazy-imports the
studio) + requirements.txt. Generated by `hf_spaces/_generate.py`.

## 9. The 9 subnations (W11 + 2026-08-31)

```
9 subnations:
  1. Ireland (NCCA + SEC + DES)                — active
  2. England (DfE + AQA + OCR + Pearson)        — active
  3. UK NCCE (cross-jurisdiction Computing)    — SHOWCASE (2026-08-31)
  4. Northern Ireland (CCEA)                   — phase_2 (deferred)
  5. Wales (WJEC / CBAC)                       — phase_2 (deferred)
  6. Scotland (SQA)                            — phase_2 (deferred)
  7. Isle of Man (IoM Government Ed)           — phase_2 (default_meanscoil)
  8. Jersey   (States of Jersey Education)     — expansion pack (deferred)
  9. Guernsey (States of Guernsey Education)   — expansion pack (deferred)
```

All 9 subnations have a corresponding awarding-body palette in
`themes/<key>_palette.json` (verified by smoke test).

## 10. The deferred-tuatha consolidation (W4 + W16)

```
W4 openspec change (already shipped):
  2026-08-27-defer-tuatha-consolidation-v1
  → documents the dropped features from sruth/tuath + /dev/tuatha
  → 5-step post-hackathon consolidation plan

Future openspec change at the cianfhoghlaim monorepo level:
  → absorbs gemini_hackathon/ back into cianfhoghlaim/tuatha/
  → closes the deferred-consolidation spec
```

See `docs/TUATHA_CONSOLIDATION_MAP.md` for the full details.

## 11. The 26 openspec changes

```
# The original 2 (pre-refactor)
2026-08-24-gemini-hackathon-public-v1
2026-08-25-per-subnation-user-context

# The 16 W0-W14 refactor changes + the W4 deferred-tuatha
2026-08-27-minimal-unblock-v1                       (W0)
2026-08-27-dependency-pin-to-verified-versions-v1    (W1)
2026-08-27-ncca-policy-corpus-as-certificate-source-v1  (W2)
2026-08-27-gemini-hackathon-gradio-package-v1         (W3)
2026-08-27-lift-sruth-tuath-non-mythology-v1          (W4a)
2026-08-27-lift-dev-tuatha-subject-wiring-v1         (W4b)
2026-08-27-defer-tuatha-consolidation-v1             (W4c)
2026-08-27-lift-ireland-k12-baml-dlt-cocoindex-v1     (W5)
2026-08-27-lift-leabharlann-personal-archive-v1       (W6)
2026-08-27-adk-2-stage-coordinators-v1               (W7)
2026-08-27-memory-knowledge-graph-v1                 (W8)
2026-08-27-skill-progression-ledger-v1              (W9)
2026-08-27-fibo-image-generation-v1                  (W10)
2026-08-27-ireland-england-subnations-v1            (W11)
2026-08-27-gradio-editorial-studio-on-cloud-run-v1   (W12)
2026-08-27-hf-spaces-headline-demos-v1               (W13)
2026-08-27-official-lc-jc-certificate-pipeline-v1     (W14 — SHOWCASE)
2026-08-27-deferred-ni-wales-scotland-iom-v1         (Phase 2 openspec)
2026-08-27-deferred-jersey-guernsey-v1              (expansion pack)

# The 4 NEW 2026-08-30 changes (GCP-first era)
2026-08-30-retire-letta-wire-vertex-memory-bank-v1   (Phase 0 — memory)
2026-08-30-observability-otel-completeness-v1        (Phase 1 — OTLP)
2026-08-30-cocoindex-pdf-pipeline-v1                 (Phase 2 — PDF→Markdown)
2026-08-30-gcp-first-iac-refactor-v1                 (Phase 0 IaC — Cloud Run + Secret Manager + WIF)

# The 3 NEW 2026-08-31 changes (Learning Graph era)
2026-08-31-uk-ncce-learning-graph-showcase-v1        (Phase A — the SHOWCASE)
2026-08-31-learning-graph-equivalency-graph-v1       (Phase B — cross-walk)
2026-08-31-pedagogy-overlay-renderer-v1              (Phase C — pedagogy overlay)
```

## 12. Local dev topology

```
# Local dev (docker-compose)
gemini-hackathon     (the app container; Dockerfile.cloudrun builds)
llama-swap          (OCR/VLM gateway; uses the canonical cianfhoghlaim config)
duckdb               (named-volume mount for the .duckdb file)
langfuse             (v3 :3001)
mlflow               (v2.20 :5050)
pgvector/pgvector:pg17 + lake-keeper-rust + lance-namespace + cognee + falkordb + memgraph + clickhouse + garage + olake

# Dev Cloud Run (gcloud run compose up)
gemini-hackathon-adk  (Cloud Run service)
Secrets via Google Secret Manager + WIF

# Prod Cloud Run (terraform apply from cloud/terraform/envs/prod/)
36 Cloud Run services (32 stateless + 4 GPU)
Cloud SQL Enterprise HA (Postgres)
Memorystore Standard M3 (Valkey)
BigQuery dataset `biep`
GCS bucket for raw + md pairs
Lance namespace `iceberg` backend → BigLake Iceberg REST (Lakekeeper)

Unsloth Studio and the LLM backends run **outside Docker** on the host:
Unsloth Studio at 127.0.0.1:8888, Gemini via Vertex ADC, etc.
```

## 13. Observability

`gemini_hackathon.observability` ports the cianfhoghlaim/observability/*
modules. Emits:

- `llm.invocation` (canonical — `llm.tier` / `llm.model` / `llm.backend` /
  `llm.latency_ms` / `llm.tokens_in` / `llm.tokens_out` /
  `llm.fallback_reason`)
- `agent.trace_opened` + `agent.trace_closed` (per-agent spans)
- `asset.generated` (per-asset provenance)

**The OTLP path** (post 2026-08-30 Phase 1) replaces `get_gcp_exporters`
with `opentelemetry-exporter-otlp-proto-grpc` pointed at
`https://telemetry.googleapis.com/v1/traces`. The 6 Stackdriver env
vars (per the [Stackdriver AI Agent ADK doc](https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk)):

```
OTEL_SERVICE_NAME='gemini-hackathon-adk'
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED='true'
OTEL_SEMCONV_STABILITY_OPT_IN='gen_ai_latest_experimental'
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT='EVENT_ONLY'
ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS='false'
GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY='true'
```

The **OpenInference Langfuse instrumentor** wraps every ADK call as a
nested Langfuse span under the parent AG-UI trace. Langfuse :3001 +
MLflow :5050 are both live and wire in when the env vars are set.

## 14. The 3-tier model policy

```
Tier 1 (production):  gemini-3.5-flash  via Vertex AI / AI Studio
Tier 2 (dev / local):  unsloth/gemma-4-26B-A4B-it-GGUF  via Unsloth Studio
Tier 3 (offline):     HuggingFace Inference Providers
                       (Qwen 7B → Llama 8B → Gemma 9b fallback chain)

Hard-rejected: `@cf/*` (Cloudflare Workers AI), `qwen3-coder-*`.
```

Every call routes through `gemini_hackathon.call_llm.call_llm(messages)`.

## 15. The NCCE learning graph showcase (NEW — 2026-08-31)

The headline change of the 2026-08-31 batch. Lifts the 5 NCCE PDFs into
the BIEP substrate as the canonical example of how every official
syllabus becomes a structured row × column learning graph.

### 15.1 The 5 lifted PDFs

| File | Shape |
|---|---|
| `learning_graph_intro_to_python_programming_y8.pdf` | 4 rows × 7 columns + prerequisite arrows (Y8 Python) |
| `learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf` | 6 columns + 3 cross-cutting skill ribbons (Y7 Scratch) |
| `learning_graph_variables_in_games_y6.pdf` | Y6 unit (Variables in Games) |
| `pedagogy_principles.pdf` | 12 cross-cutting pedagogy principles |
| `curriculum_journey_full_2024_2025.pdf` | Full Y7→Y11 NCCE Computing journey |

### 15.2 The data flow

```
NCCE PDF → DLT (jurisdiction #9) → CocoIndex (grid-preserving) → BAML (8 classes + 9 functions)
       → Dagster (11 assets + 1 sensor) → Firestore + Gradio SVG + HF Space + React landing page
```

### 15.3 The 6 priority subjects

The 6 per-subject BAML extractors in `baml_extracts/learning_graph.baml`:

- Computer Science (Y6 / Y7 / Y8 NCCE learning graphs cover this end-to-end)
- Mathematics (NCEA + AQA + OCR + Edexcel comparability is strong)
- English (cross-walks AQA + CCEA)
- Gaeilge / Irish (bilingual EN ↔ GA — the unique 2-language path)
- Chemistry (NCCA + AQA + OCR 21st Century)
- Geography (NCCA + AQA + OCR)

### 15.4 Cross-jurisdiction equivalencies (Change B)

Every cell in every jurisdiction's learning graph has a pointer to its
equivalent cells in the 7 other BI jurisdictions. Powered by
`ExtractCellEquivalencies` (linear topics → cell-level). Visualised as
a Sankey diagram.

### 15.5 Pedagogy overlay (Change C)

Every cell is coloured by which of the 12 NCCE pedagogy principles it
uses. Principles are **dynamically extracted** from `pedagogy_principles.pdf`
and **cached** to disk + Cognee (`gh_cognee_pedagogy_dataset`).

### 15.6 Visualisation library comparison

The 4 implementations are compared in
`notebooks/11_learning_graph_renderers_compare.ipynb` (SVG / Plotly /
Mermaid / D3) and benchmarked on time + memory + file-size +
visual-fidelity (RAGAS over 10 sample graphs) to MLflow experiment
`biiep_v3_learning_graph_renderers`. The Gradio studio picks the winner
via `RENDERER_BACKEND` env var (default: `plotly`).