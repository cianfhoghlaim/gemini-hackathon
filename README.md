# gemini_hackathon — The British Isles Education Platform

> **Google All Things Agentic 2026 Hackathon submission.** Built with
> **Gemini 3.5** (Vertex AI) + **Gemma 4 26B-A4B** (Unsloth Studio) +
> the **Google ADK 2** agent framework. Deployed on **Google Cloud
> Run** with the editorial canvas on **Hugging Face Spaces**.
> The British Isles education system: **Aistear → Bunscoil → MeanScoil
> → Scoil Sinsearach → Ollscoil** across **9 jurisdictions** (Ireland +
> England active; NCCE cross-jurisdiction for the showcase; NI / Wales
> / Scotland / IoM / Jersey / Guernsey as Phase 2).

[![MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![Gradio 5.28+](https://img.shields.io/badge/gradio-5.28%2B-orange)](requirements.txt)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)](.github/workflows/ci.yml)
[![OpenSpec](https://img.shields.io/badge/openspec-26_changes-green)](openspec/changes/INDEX.md)

---

## 1. The NCCE learning graph showcase — NEW (2026-08-31)

The headline feature of the 2026-08-31 batch. The **UK NCCE** (National
Centre for Computing Education) publishes its computing curriculum as
**structured row × column learning graphs** — the canonical example of
how every official syllabus should be modelled. The 5 lifted PDFs:

| File | Source | Shape |
|---|---|---|
| `learning_graph_intro_to_python_programming_y8.pdf` | `leabharlann/.../pgce/syllabus/` | 4 rows × 7 columns + prerequisite arrows (Y8 Python) |
| `learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf` | `leabharlann/.../pgce/syllabus/` | 6 columns + 3 cross-cutting skill ribbons (Y7 Scratch) |
| `learning_graph_variables_in_games_y6.pdf` | `leabharlann/.../pgce/syllabus/lessons/` | Y6 unit (Variables in Games) |
| `pedagogy_principles.pdf` | `leabharlann/.../pgce/syllabus/` | 12 cross-cutting pedagogy principles |
| `curriculum_journey_full_2024_2025.pdf` | [NCCE S3](https://ncce-curriculum-production.s3.eu-west-1.amazonaws.com/qvz4tnrz4y7rrxayqz2qfji94nko) | Full Y7→Y11 NCCE Computing journey |

### 1.1 The data flow (5 stages)

```
NCCE PDF → DLT resource → CocoIndex App → BAML extraction → Dagster asset → Firestore + Gradio SVG
```

1. **DLT** (`dlt_pipelines/uk_ncce_learning_graphs.py`) — emits 11 rows into `official_documents`
2. **CocoIndex** (`cocoindex_flows/uk_ncce/learning_graphs_app.py`) — Docling converter that preserves the row × column grid via the new `_shared/_docling_grid_segmenter.py`
3. **BAML** (`baml_extracts/learning_graph.baml`) — 8 classes + 9 functions; 6 per-subject extractors for Computer Science, Mathematics, English, Gaeilge, Chemistry, Geography
4. **Dagster** (`orchestration/defs/3_model_lifecycle/uk_ncce_learning_graphs.py`) — 11 assets; sensor on `data/bi_ep/syllabi_raw/uk_ncce/`
5. **Gradio + HF Space + React** (`gemini_hackathon_gradio/an_learning_graph/`, `hf_spaces/gemini_hackathon_learning_graphs/`, `web/src/routes/learning-graphs/`) — 4-tab studio: Render / Equivalencies / Generate from PDF / Pedagogy overlay

### 1.2 Cross-jurisdiction equivalencies

Every cell in every jurisdiction's learning graph has a pointer to its
equivalent cells in the 7 other BI jurisdictions. Powered by
`ExtractCellEquivalencies` (Change B). Visualised as a Sankey diagram.

### 1.3 Pedagogy overlay

Every cell is coloured by which of the 12 NCCE pedagogy principles it
uses (PRIMM, pair programming, semantic waves, etc.). Principles are
**dynamically extracted** from `pedagogy_principles.pdf` and **cached**
to disk + Cognee (Change C).

[SCREENSHOT placeholder — the SVG grid of the Y8 Python learning graph with pedagogy overlay]

---

## 2. The August 2026 refactor — three eras

### 2.1 The 17-workstream W0–W14 refactor (2026-08-27)

| W | What |
|---|---|
| W0 | minimal unblock (document dupe web/components, add KNOWN_ISSUES.md) |
| W1 | dependency pin: `google-adk 2.7.1+`, `gradio 5.28+`, `huggingface_hub 0.30+`, `lancedb`, `falkordb`, `graphiti-core`, `cognee`, `fastmcp` |
| W2 | **5 NCCA policy PDFs** as committed data — the certificate source of truth |
| W3 | `gemini_hackathon_gradio/` — the 5 editorial studios + shared library |
| W4 | lift `sruth/tuath` non-mythology + `/dev/tuatha` subject wiring + deferred-tuatha openspec change |
| W5 | Ireland K-12 BAML + DLT + CocoIndex (Primary + Secondary) |
| W6 | leabharlann general sources + UoG archives (manifests only) |
| W7 | **5 ADK 2 stage coordinators** + 5 reusable workflow pillars |
| W8 | memory layer (`MarkdownMemoryService`) + `knowledge_graph/hybrid_search.py` |
| W9 | skill-progression ledger (Firestore + Vertex AI Vector Search + Firestore graph) |
| W10 | FIBO image generation — **14 NCCA subjects × 5 stages** prompt bank |
| W11 | 9 subnations (Ireland + England + NCCE active; NI/Wales/Scotland/IoM/Jersey/Guernsey Phase 2) |
| W12 | the big Gradio editorial studio on Cloud Run (monolithic + `gr.Workflow` canvas) |
| W13 | 5 HF Spaces at `cianfhoghlaim/gemini_hackathon_<stage>` |
| W14 | **the LC/JC certificate pipeline** — the SHOWCASE |

### 2.2 The 4 NEW 2026-08-30 changes (GCP-first era)

- **`gcp-first-iac-refactor-v1`** — Phase 0: drops Komodo/Pangolin/Locket/Infisical for Cloud Run + Secret Manager + WIF + 11 Terraform modules
- **`observability-otel-completeness-v1`** — Phase 1: ADK OTel OTLP path + OpenInference Langfuse instrumentor + 6 Stackdriver env vars
- **`cocoindex-pdf-pipeline-v1`** — Phase 2: pdf_to_markdown App (Docling converter) + Dagster asset + MLflow benchmark
- **`retire-letta-wire-vertex-memory-bank-v1`** — Phase 0 (memory): replaces Letta with `VertexAiMemoryBankService` + `MarkdownMemoryService` + `InMemoryMemoryService`

### 2.3 The 3 NEW 2026-08-31 changes (Learning Graph era)

- **`uk-ncce-learning-graph-showcase-v1`** — the headline change (see §1)
- **`learning-graph-equivalency-graph-v1`** — extends `ExtractEquivalencies` from linear topics to cell-level (48 jurisdiction × subject cross-walks)
- **`pedagogy-overlay-renderer-v1`** — dynamic extraction + disk + Cognee cache for the 12 NCCE pedagogy principles; renders the annotated SVG

The Celtic 5-element palette (Talamh / Uisce / Tine / Aer / Anam) was
REPLACED with the 5-stage British Isles education palette (Aistear /
Bunscoil / MeanScoil / Scoil Sinsearach / Ollscoil). The Hades
Shadow-First dark theme is preserved.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture, or
[docs/TUATHA_CONSOLIDATION_MAP.md](docs/TUATHA_CONSOLIDATION_MAP.md)
for what was absorbed from `sruth/tuath` and `/dev/tuatha`.

---

## 3. The LC/JC certificate pipeline (the SHOWCASE — W14)

Every claim on every generated certificate cites a page from one of
the 5 NCCA policy PDFs:

```
SC-L1-L2-Programme-Statement.pdf,
key-competencies-in-senior-cycle_en.pdf,
the-potential-of-online-learning-environments_en.pdf,
the-potential-of-technology-to-support-online-certification-and-reporting.pdf,
scr-advisory-report_en.pdf
```

The pipeline (7 stages): extract_criteria → decompose_outcomes →
extract_paper+marking → search_official → generate_background →
compose_certificate → save_to_provenance.

Output: PNG (~80 KB) + PDF (~700 B) with the awarding-body palette
background + competency strip + provenance footer + UNOFFICIAL banner.

---

## 4. Repository layout

```
gemini_hackathon/
├── pyproject.toml + requirements.txt + Makefile
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
├── gemini_hackathon_gradio/                ← W3 — the 5 editorial studios + 2026-08-31 an_learning_graph
├── gemini_hackathon_assets_fibo/            ← W10 — the FIBO image-gen pipeline
├── gemini_hackathon_backend/                ← 2026-08-30 — the ADK 2 Cloud Run service
│   ├── agents/ + memory.py + observability.py + main.py
│   ├── catalog/                            ← the Lake namespace adapter
│   └── tests/
├── baml_extracts/                          ← BAML contracts (existing + 2026-08-31 learning_graph.baml)
├── baml_extracts_education/                ← W4+W5 — lifted from cianfhoghlaim
├── cocoindex_flows/                        ← W5 + 2026-08-30 + 2026-08-31
│   ├── _shared/                             ← shared_lifespan + _vector_target + _docling_grid_segmenter
│   ├── ireland/                             ← per-stage embedding apps
│   ├── pdf/                                 ← Phase 2b Docling converter
│   ├── uk_ncce/                             ← 2026-08-31 NCCE learning graph App
│   ├── equivalency/                         ← Phase 4a equivalency graph
│   ├── education/                           ← W14 BAML extraction target
│   └── _factory/                            ← bi_jurisdiction + four_stage
├── dlt_pipelines/                           ← W5 + 2026-08-30 + 2026-08-31
│   ├── ireland/                              ← 6 NCCA subject pipelines
│   ├── uk_ncce_learning_graphs.py            ← 2026-08-31 (jurisdiction #9)
│   ├── official_doc_fetcher.py
│   ├── pdf_downloader.py
│   ├── corpus_downloader.py
│   └── _shared.py + _base/ + _subject_base.py
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
├── web/                                    ← Firebase-native TanStack Start web (post Firebase migration)
│   └── src/routes/learning-graphs/         ← 2026-08-31 NCCE landing page (embeds HF Space)
├── hf_spaces/                               ← W13 + 2026-08-31 (6 headline demos)
│   ├── _generate.py
│   ├── gemini_hackathon_{aistear,bunscoil,junior_cycle,leaving_certificate,editorial_studio}/
│   └── gemini_hackathon_learning_graphs/   ← 2026-08-31
├── orchestration/                           ← 2026-08-30 + 2026-08-31
│   ├── defs/                                ← 5-layer Dagster defs tree
│   │   ├── 1_ingestion/
│   │   ├── 2_materials/
│   │   ├── 3_model_lifecycle/               ← NCCE learning graph assets (2026-08-31)
│   │   ├── 4_asset_generation/
│   │   └── 5_agent_ops/
│   └── storage/                             ← BigQuery client + DuckLake client
├── openspec/changes/                       ← W16 — 26 openspec changes (23 + 3 NEW 2026-08-31)
├── docs/                                   ← W15 — the docs (TUATHA_CONSOLIDATION_MAP, KNOWN_ISSUES, LEARNING_GRAPH_SHOWCASE, ...)
├── notebooks/                              ← the 14 marimo + ipynb walkthroughs (00_theming … 13_pedagogy_overlay)
├── cloud/                                  ← GCP-native IaC
│   └── terraform/
│       ├── cloud_run_adk.tf + cloud_run.tf + cloud_run_jobs.tf + cloud_run_journey.tf
│       └── modules/                          ← 11 Terraform modules (per Phase 5 GCP-first IaC)
├── cloudbuild.yaml + Makefile + README.md
└── firestore.{json,rules,indexes.json}     ← Firebase-native schema + NCCE collections
```

---

## 5. The data plane

### 5.1 VLM + OCR ensemble

The 4-path OCR/VLM ensemble (BAML + Docling + EasyOCR + Tesseract) with
RAGAS voting + MLflow observability. Scanned-PDF detector
(`is_scanned_pdf()`) routes to the recommended backend via
`select_ocr_backend()`. The 22 VLM + 6 classical OCR entries live in
`MODEL_REGISTRY:ocr_vision` (qwen3-vl-8b + qwen3-vl-4b added in
`2026-08-25-tuatha-vision-models-v1`).

### 5.2 CocoIndex flows

- `_shared/{_lifespan, _vector_target, _vertex_embedder, _docling_grid_segmenter}` — canonical lifespan + dual-backed vector target (Firestore default / Vertex AI Vector Search) + VertexEmbedder + grid-preserving Docling segmenter (2026-08-31)
- `ireland/` — per-stage embedding apps for the 6 NCCA LC subjects
- `pdf/pdf_to_markdown_app.py` — Phase 2b Docling converter
- `uk_ncce/learning_graphs_app.py` — 2026-08-31 NCCE learning graph App
- `_factory/{bi_jurisdiction, four_stage}` — the 114-App 4-stage BI factory
- `equivalency/equivalency_graph_app.py` — Phase 4a cross-jurisdiction graph
- `education/lc6_extraction_app.py` — W14 BAML extractor target

### 5.3 DLT pipelines

- 6 NCCA LC subjects + cross-jurisdiction + jurisdiction sensors
- `pdf_downloader.py` (Phase 2) + `corpus_downloader.py` + `official_doc_fetcher.py`
- `uk_ncce_learning_graphs.py` (2026-08-31 — jurisdiction #9)
- DLT 1.30 features: `refresh` + `dlt[hub]` + `pipeline.dataset()`
- DuckDB → BigLake Iceberg (prod) via `orchestration/storage/bigquery_client.py:BIGQUERY_DATASET = "biep"`

### 5.4 Dagster assets (5-layer architecture)

`orchestration/defs/{1_ingestion, 2_materials, 3_model_lifecycle, 4_asset_generation, 5_agent_ops}`. The 2026-08-31 NCCE learning graph assets (11) + equivalency assets (48) + pedagogy overlay assets (6) + 1 sensor live under `3_model_lifecycle/`. Wired via `dg` CLI (Dagster 1.13+).

### 5.5 BAML extraction

- `baml_extracts/learning_graph.baml` (2026-08-31) — 8 classes + 9 functions for the structured learning graphs
- `baml_extracts/extract_equivalency.baml` — topic-level + cell-level equivalencies (extended in 2026-08-31 Change B)
- `baml_extracts_education/{celtic_curriculum, subjects/*}.baml` — per-subject BAML contracts with strand + BloomLevel metadata

---

## 6. The lakehouse stack (GCP-first substrate)

### 6.1 Local dev (docker-compose)

`pgvector/pgvector:pg17` + `lake-keeper-rust` + `lance-namespace` + `cognee` + `falkordb` + `memgraph` + `clickhouse` + `garage` (S3) + `olake` (CDC). Langfuse v3 :3001 + MLflow v2.20 :5050 (the dual-purpose local observability stack).

### 6.2 Prod (Cloud Run + BigLake)

- Cloud SQL Enterprise HA (Postgres)
- Memorystore Standard M3 (Valkey)
- BigQuery dataset `biep` (via `orchestration/storage/bigquery_client.py`)
- Lance namespace `iceberg` backend → BigLake Iceberg REST (Lakekeeper)
- GCS bucket for the PDF→Markdown raw + md pairs

### 6.3 Terraform modules (11 modules under `cloud/terraform/modules/`)

`cloudrun_service`, `cloudrun_secret_mount`, `cloudsql_postgres`, `memorystore_valkey`, `gcs_bucket`, `bigquery_dataset`, `firestore_database`, `artifact_registry_repo`, `workload_identity_gha`, `cloudbuild_trigger`, `iam_gcp_ai_agent_adk`.

---

## 7. The memory + observability layer (post-Phase 0/1)

### 7.1 Memory

- `VertexAiMemoryBankService` (prod, when `DEPLOYED_AGENT_ENGINE_ID` is set)
- `MarkdownMemoryService` (dev/offline, when `GH_MEMORY_DIR` is set)
- `InMemoryMemoryService` (default fallback)
- `before_agent_callback` → `add_session_to_memory`
- `letta_agent_id` field renamed to `memory_namespace` (semantics change, same shape)

### 7.2 Observability

- ADK OTel OTLP path → Cloud Trace + Cloud Logging + Cloud Monitoring
- 6 Stackdriver env vars (per the [Stackdriver AI Agent ADK doc](https://docs.cloud.google.com/stackdriver/docs/instrumentation/ai-agent-adk))
- OpenInference Langfuse instrumentor (wraps every ADK call as a nested Langfuse span)
- Langfuse v3 :3001 + MLflow v2.20 :5050 (local dev)

---

## 8. The 5-stage British Isles education palette + Hades Shadow-First

```
aistear          dawn-orange       #e8915c
bunscoil         sea-blue          #1e80c6
meanscoil        meadow-green      #28955e
scoil_sinsearach harvest-gold      #cc9966
ollscoil         scholarship-indigo #5a4fcf
```

Hades Shadow-First is preserved as the dark-mode foundation.

---

## 9. The 14-subject SUBJECT_WIRING_REGISTRY + 5 ADK 2 stage coordinators

8 NCCA + 6 NCCA-adjacent subjects. The 2026-08-31 NCCE showcase adds a
9th routing key (`learning_graph`) for the structured cross-walk view.

The 5 ADK 2 stage coordinators (`gemini_hackathon/agents/stages/`) and
the 5 reusable workflow pillars (`gemini_hackathon/agents/workflows/`)
remain the runtime substrate.

---

## 10. The 9 subnations + awarding-body palettes

| # | Subnation | Awarding Body | Status |
|--:|-----------|---------------|--------|
| 1 | Ireland | NCCA + SEC + DES | active |
| 2 | England | DfE + AQA + OCR + Pearson | active |
| 3 | UK NCCE | NCCE (cross-jurisdiction Computing curriculum) | **showcase (2026-08-31)** |
| 4 | Northern Ireland | CCEA | phase_2 (deferred) |
| 5 | Wales | WJEC / CBAC | phase_2 (deferred) |
| 6 | Scotland | SQA | phase_2 (deferred) |
| 7 | Isle of Man | IoM Government Ed | phase_2 (default_meanscoil) |
| 8 | Jersey | States of Jersey Education | expansion pack (deferred) |
| 9 | Guernsey | States of Guernsey Education | expansion pack (deferred) |

All 9 subnations have a corresponding awarding-body palette in `themes/<key>_palette.json`.

---

## 11. Quick start (offline, no GCP keys required)

The canonical Google project management pattern: a single self-documenting
`Makefile` + `scripts/dev.sh` (one-shot bootstrap) + `scripts/verify.sh`
(the 8-tick verify gate). Run `make help` for all 27 targets.

```bash
# 1. Bootstrap (uv install + sync + .env + baml + verify)
make setup            # = ./scripts/dev.sh

# 2. Generate BAML clients + run BAML tests
make baml

# 3. Boot the Python backend on :8000 (FastAPI + ADK 2)
make backend

# 4. Bring up the full lakehouse + observability stack (docker compose)
make dev              # 6 services on :8080 + :3001 + :5050 + :5432 + :8181 + :9100

# 5. Run the data plane (5 DLT pipelines → 8 CocoIndex Apps → 6 BAML extractions)
make dlt-smoke-all    # writes ~31 OFFICIAL_DOC_COLUMNS rows to gemini_hackathon.duckdb
make cocoindex-update # converts 13 PDFs to Markdown + 11 learning graphs

# 6. Render the NCCE Y8 Python learning graph as SVG
make ncce-visualise   # = uv run python -m gemini_hackathon_gradio.an_learning_graph

# 7. Materialize the NCCE learning graph Dagster assets
dg launch --assets uk_ncce_learning_graph_y8_python,uk_ncce_learning_graph_y7_scratch,uk_ncce_learning_graph_y6_variables,uk_ncce_pedagogy_principles,uk_ncce_curriculum_journey

# 8. Verify everything
make verify           # = ./scripts/verify.sh (the 8-tick gate)
```

See [docs/LOCAL_DEV.md](docs/LOCAL_DEV.md) for the full step-by-step
recipe (5 steps + the data cheatsheet + the "what to do when something
breaks" section).

---

## 12. Cloud Run deploy (with GCP keys)

```bash
# Build + push the container
gcloud builds submit --config=cloudbuild.yaml

# Deploy the ADK 2 backend
gcloud run services deploy gemini-hackathon-adk \
  --source . --region europe-west1 \
  --service-account gemini-hackathon-adk@PROJECT.iam \
  --set-env-vars=ADK_LOAD_SECRETS=1,DEPLOYED_AGENT_ENGINE_ID=...,GH_MEMORY_DIR=...,LEARNING_GRAPH_FIRESTORE_COLLECTION=annotatedLearningGraphs

# Apply the prod Terraform
cd cloud/terraform/envs/prod && terraform apply
```

---

## 12.1 Google Cloud Secret Manager (GSM) — Phase 0 (2026-08-30)

The dev demo uses **Google Cloud Secret Manager** (project
`agentic-hackathon-august-26`) instead of the Infisical + Locket contract
used by the parent `cianfhoghlaim` monorepo. The legacy cianfhoghlaim
Infisical flow is unchanged; GSM is a gemini_hackathon-only contract.

### Files added in this change

| Path | Purpose |
|---|---|
| `secrets.yaml` | The committed catalogue: 15 `env_var → gsm_secret_id` mappings |
| `gemini_hackathon/secrets_loader.py` | Python module — ADC + GSM SDK fetch with `.env` fallback |
| `scripts/seed_gsm.py` | One-shot uploader — reads `.env`, creates/populates each GSM secret |
| `scripts/audit_gsm.py` | Parity check — `secrets.yaml ↔ GSM API ↔ .env` |
| `docs/GSM_README.md` | Operator guide |

### Resolution contract

| `ADK_LOAD_SECRETS` | `ADK_LOCAL_SECRETS` | Behaviour |
|:--:|:--:|:--|
| `0` / unset | n/a | Dormant — backward-compatible (default) |
| `1` | `0` / unset | **GSM mode** — ADC + Secret Manager SDK |
| `1` | `1` | **Local mode** — reads `.env` via python-dotenv |

### One-time GSM bootstrap

```bash
gcloud config set project agentic-hackathon-august-26
gcloud services enable secretmanager.googleapis.com aiplatform.googleapis.com
gcloud auth application-default login
uv run python scripts/seed_gsm.py     # pushes .env → GSM
uv run python scripts/audit_gsm.py    # verifies catalogue ↔ GSM ↔ .env
```

For laptop dev without GSM creds, use:
```bash
ADK_LOAD_SECRETS=1 ADK_LOCAL_SECRETS=1 uv run python -m gemini_hackathon.backend
```

See `docs/GSM_README.md` for the full operator guide.

---

## 12.2 The 5-stack live demo substrate (2026-08-30)

The dev demo runs against a 5-stack substrate on `bunchloch` (the M4 MacBook):

| Stack | Port | Role in the demo | Source |
|---|---|---|---|
| **litellm** | 4000 | The 46-model OpenAI-compatible gateway (Kimi-K2.6 + GLM-5.1 + minimax-m3 + 22 local/unsloth/* GGUF routes + OpenCode Go fallback) | `bonneagar/stacks/litellm/` (cianfhoghlaim monorepo) |
| **langfuse** | 3001 | LLM observability — traces every `litellm` call into ClickHouse; the unified dashboard for cost + latency + prompt management | `bonneagar/stacks/langfuse/` |
| **mlflow** | 5000 | Experiment tracking — the BAML extraction runs, the cross-jurisdiction equivalency sweeps, the Gemini-vs-Gemma4 harness | `bonneagar/stacks/mlflow/` |
| **llama-swap** | 8080 | GGUF model swapper — 12 vision + text GGUFs (qwen3-vl-8b, gemma-4-26B-A4B, internvl3-8b, paddleocr-vl-1.6) for the Tier-2 Gemma 4 route | `bonneagar/stacks/llama-swap/` |
| **unsloth** | 8888 | Unsloth Studio host process — the OpenAI-compatible API at `/v1/chat/completions` + Anthropic-compatible `/v1/messages`; long-running daemon on `127.0.0.1:8888` | `bonneagar/stacks/unsloth/` |

### Health verification

```bash
curl -s http://localhost:4000/health/liveliness                 # litellm
curl -s http://127.0.0.1:3001/api/public/health                  # langfuse
curl -s http://localhost:5000/api/2.0/mlflow/                    # mlflow
curl -s http://localhost:8080/v1/models | jq '.data | length'    # llama-swap → 12
curl -s http://localhost:8888/api/auth/status                    # unsloth
```

### PDF indexing pipeline routing

The NCCE + NCCA + SEC PDF ingestion stack uses these 5 services in this order:

```
PDF on disk
  ↓
[Dagster asset] uk_ncce_learning_graphs / ncca_syllabus_pdf
  ↓
[CocoIndex App]  (Docling grid segmenter + BAAI/bge-m3 embedder)
  ↓                                                                    ↘
[BAML extract]   ExtractLearningGraphRow / ExtractCurriculumSyllabus   [OpenTelemetry OTLP]
  ↓                                                                          ↓
[DuckLake table] cianfhoghlaim.uk_ncce.learning_graph_row              [logfire-otel collector]
                                                                              ↓
[Gradio / Firestore]                                                          ↓
                                                                       [Langfuse traces]
                                                                       [MLflow runs]
                                                                       [Gemma 4 (llama-swap)]
                                                                       [Gemini 3.5 (litellm)]
```

---

## 13. Quality gates

```bash
make lint                          # ruff check + ruff format --check (Python + Markdown + YAML)
make typecheck                     # mypy gemini_hackathon/ (strict)
make test                          # pytest tests/ -v
make verify                        # the 8-tick verify gate (every CI gate in one script)
openspec validate <change-id> --strict
make dlt-smoke-all                  # 9 jurisdictions (Ireland + England + NCCE + 6 Phase 2)
dg list assets --module orchestration.defs   # ~80 assets (11 NCCE + 48 equivalency + 6 pedagogy + ...)
uv run baml-cli test baml_extracts/learning_graph.baml  # the 10 BAML functions
```

The CI workflow (`.github/workflows/ci.yml`) runs `make lint` + `make typecheck` + `make test` + `baml-cli test` on every push across the Python 3.11 + 3.12 matrix.

---

## 14. References

- [ARCHITECTURE.md](ARCHITECTURE.md) — the architecture deep-dive
- [AGENTS.md](AGENTS.md) — the root agent routing file
- [openspec/changes/INDEX.md](openspec/changes/INDEX.md) — the 26 openspec changes
- [docs/TUATHA_CONSOLIDATION_MAP.md](docs/TUATHA_CONSOLIDATION_MAP.md) — what was absorbed from `sruth/tuath` + `/dev/tuatha`
- [docs/LEARNING_GRAPH_SHOWCASE.md](docs/LEARNING_GRAPH_SHOWCASE.md) — the NCCE showcase guide
- [docs/GSM_README.md](docs/GSM_README.md) — the Google Cloud Secret Manager operator guide (Phase 0)
- [`.agents/skills/openspec/SKILL.md`](.agents/skills/openspec/SKILL.md) — the OpenSpec skill
- **Upstream cianfhoghlaim**:
  - [`2026-08-30-cieanfhoghlaim-biep-on-gcp-v1`](file:///Users/cianmacandeisigh/dev/cianfhoghlaim/openspec/changes/2026-08-30-cieanfhoghlaim-biep-on-gcp-v1/) — the BIEP-on-GCP umbrella
  - [`2026-08-26-empower-gemini-hackathon-v1`](file:///Users/cianmacandeisigh/dev/cianfhoghlaim/openspec/changes/2026-08-26-empower-gemini-hackathon-v1/) — the TIER 1 + TIER 3 mount
  - [`2026-08-25-tuatha-vision-models-v1`](file:///Users/cianmacandeisigh/dev/cianfhoghlaim/openspec/changes/2026-08-25-tuatha-vision-models-v1/) — the VLM registration
- **NCCE source**:
  - [teachcomputing.org/curriculum](https://teachcomputing.org/curriculum)
  - [Curriclum.Journey_Full_2024_2025.pdf](https://ncce-curriculum-production.s3.eu-west-1.amazonaws.com/qvz4tnrz4y7rrxayqz2qfji94nko)

---

[MIT](LICENSE) © 2026 cianfhoghlaim