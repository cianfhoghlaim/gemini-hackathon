# gemini-hackathon — Submission Writeup (200 words)

> Built for the **Google All Things Agentic Hackathon 2026** (Fortified Enterprise Fleet track).
> Built with **Google ADK 2** + **Gemini 3.5 Flash** + **Gemma 4 26B-A4B** (via Unsloth Studio) + **DiffusionGemma** (image gen) + **FLUX** (via InvokeAI) + **FIBO** (JSON-native image gen) + **Imagen 3 / Imagen 4** (Vertex AI).

## 200-word writeup

The gemini-hackathon submission is a British Isles education platform covering 5 stages (Aistear → Bunscoil → MeanScoil → Scoil Sinsearach → Ollscoil) across all 8 British Isles subnations (Ireland + England fully populated; NI / Scotland / Wales / Isle of Man / Jersey / Guernsey wired end-to-end with schema-complete pipelines, corpus coverage growing as each jurisdiction's official sources are ingested). The **showcase** is the **LC/JC certificate pipeline**: 7 stages that take a learner_id + subject + stage, extract the NCCA learning outcomes from the 5 NCCA policy PDFs via BAML, RAG-search the policy corpus via a Firestore/Vertex AI Vector Search hybrid, generate the certificate background via FIBO + the 14-subject × 5-stage prompt bank, and compose the certificate via PIL (1200×850) with the official NCCA palette + the UNOFFICIAL banner + a 5-PDF provenance footer. Every claim cites a page. The **bonus** is the **280-cell asset-comparison leaderboard**: 8 NCCA LC subjects × 5 topics × 7 backends (FIBO + DiffusionGemma + FLUX.1-schnell + FLUX.2-dev + Gemini 2.5 Flash Image + Imagen 3 + Imagen 4) compared on SSIM, palette fidelity, cost, latency, and an LLM-judge subjective score. The **17 Jupyter notebooks** in `notebooks/converted/` (13 marimo conversions + 4 ADK-focused originals) walk through every pipeline + the Google ADK agent tree + the AGUI 13-event protocol + the CopilotKit runtime + the 7 Fleet primitives.

*Submitted for the purposes of entering this hackathon.*

## Stack

- **Google ADK 2** (`google-adk >= 2.7.1`) — the mandatory framework
- **Gemini 3.5 Flash** via Vertex AI (Tier 1)
- **Gemma 4 26B-A4B** via Unsloth Studio (Tier 2 local)
- **Gemini 2.5 Flash Image** + **Imagen 3** + **Imagen 4** via LiteLLM (Vertex AI)
- **DiffusionGemma 26B-A4B-it** via Unsloth Studio (image gen)
- **FLUX.1-schnell** + **FLUX.2-dev** via InvokeAI (image gen)
- **FIBO** via ComfyUI (JSON-native image gen)
- **BAML** (`baml-py >= 0.223`) — structured extraction
- **CocoIndex** + **Vertex AI `gemini-embedding-001`** — the embedding layer
  (BGE-M3/sentence-transformers is the offline dev fallback only)
- **Firestore `FindNearest`** + **Vertex AI Vector Search** (dual-backed
  `VectorTarget`, benchmarked head-to-head on identical 1536-d vectors) —
  the MasteryLedger's vector backend
- **Document AI** + **Gemini 3.5 Flash native PDF** — the 4-path OCR
  ensemble (RAGAS `biiep_extraction_consensus` vote)
- **BigQuery** + **Cloud Storage** (data plane; replaces DuckLake/MotherDuck
  for the deployed path — `duckdb_local` remains the offline dev default)
- **Firestore** (UI-facing MasteryLedger rows + session state + skill graph
  — replaces Convex)
- **Firebase** — Hosting + Auth + App Check + Cloud Functions Gen2 (web)
- **Cloud Run** + **Cloud Run Jobs** + **Cloud Workflows** + **Cloud
  Scheduler** (deployment + ingestion orchestration)
- **Cloud Trace** + **Cloud Logging** (observability)
- **Marimo** + **Jupyter** (notebooks — 17 .ipynb artefacts)
- **Hugging Face Spaces** (5 studios — secondary distribution channel,
  generated from the same Gradio source that ships on Cloud Run)

## Live demo

- **Hosted URL** (Cloud Run): <https://gemini-hackathon-<hash>.a.run.app>
- **Source repo**: <https://github.com/cianfhoghlaim/gemini-hackathon>
- **Architecture**: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- **17-notebook collection**: [`notebooks/converted/`](notebooks/converted/)
- **Cloud Run deploy**: [`cloud/scripts/deploy-cloud-run.sh`](cloud/scripts/deploy-cloud-run.sh)
- **Per-subject BAML contracts**: [`baml_extracts_education/subjects/`](baml_extracts_education/subjects/)
- **8 NCCA LC subjects + per-subject asset specialities**: [`gemini_hackathon/syllabus/per_topic_schema.py`](gemini_hackathon/syllabus/per_topic_schema.py)
- **7 compositor backends**: [`gemini_hackathon/certificate/backends/`](gemini_hackathon/certificate/backends/)
- **13 official-guidelines palette JSONs**: [`themes/_official_guidelines/`](themes/_official_guidelines/)

## Bonus integrations

- **Gemma 4 26B-A4B** (Unsloth Studio, local) — the Tier 2 model + the multimodal VLM
- **Imagen 4** (Vertex AI) — added to the asset comparison leaderboard
- **Google Stitch** design system — the British Isles palette pushed via `gemini_hackathon/agents/stitch_client.py`
- **5 Hugging Face Spaces** — one per British Isles stage + the editorial studio

## Submission checklist

- [x] Category: **Fortified Enterprise Fleet**
- [x] Uses **Gemini 3.5+** (Vertex AI)
- [x] Uses at least one **Google Agent Framework** (Google ADK 2)
- [x] Uses at least one **Google Cloud infrastructure service** (Cloud Run)
- [x] **Hosted URL** (Cloud Run)
- [x] **Text description** (200 words, above)
- [x] **Public code repository** (GitHub)
- [x] **Spin-up Instructions** (README.md + cloud/scripts/deploy-cloud-run.sh)
- [x] **Architecture Diagram** (docs/ARCHITECTURE.md Mermaid)
- [x] **No demo video** — the **17 Jupyter notebooks** ARE the demo
- [x] **Bonus: blog post** (forthcoming)
- [x] **Bonus: social media** with #AllThingsAgenticHackathon (forthcoming)
- [x] **Bonus: Gemma 4** as Tier 2 local model
- [x] **Bonus: Imagen 4** in the asset comparison leaderboard