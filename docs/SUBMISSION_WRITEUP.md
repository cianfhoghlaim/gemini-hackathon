# gemini-hackathon — Submission Writeup (200 words)

> Built for the **Google All Things Agentic Hackathon 2026** (Fortified Enterprise Fleet track).
> Built with **Google ADK 2** + **Gemini 3.5 Flash** + **Gemma 4 26B-A4B** (via Unsloth Studio) + **DiffusionGemma** (image gen) + **FLUX** (via InvokeAI) + **FIBO** (JSON-native image gen) + **Imagen 3 / Imagen 4** (Vertex AI).

## 200-word writeup

The gemini-hackathon submission is a British Isles education platform covering 5 stages (Aistear → Bunscoil → MeanScoil → Scoil Sinsearach → Ollscoil) across 8 subnations (Ireland + England live; NI / Wales / Scotland / IoM deferred). The **showcase** is the **LC/JC certificate pipeline**: 7 stages that take a learner_id + subject + stage, extract the NCCA learning outcomes from the 5 NCCA policy PDFs via BAML, RAG-search the policy corpus via a LanceDB + FalkorDB hybrid, generate the certificate background via FIBO + the 14-subject × 5-stage prompt bank, and compose the certificate via PIL (1200×850) with the official NCCA palette + the UNOFFICIAL banner + a 5-PDF provenance footer. Every claim cites a page. The **bonus** is the **280-cell asset-comparison leaderboard**: 8 NCCA LC subjects × 5 topics × 7 backends (FIBO + DiffusionGemma + FLUX.1-schnell + FLUX.2-dev + Gemini 2.5 Flash Image + Imagen 3 + Imagen 4) compared on SSIM, palette fidelity, cost, latency, and an LLM-judge subjective score. The **17 Jupyter notebooks** in `notebooks/converted/` (13 marimo conversions + 4 ADK-focused originals) walk through every pipeline + the Google ADK agent tree + the AGUI 13-event protocol + the CopilotKit runtime + the 7 Fleet primitives.

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
- **CocoIndex** + **LanceDB** + **FalkorDB** (MasteryLedger 4-backend)
- **DuckDB** + **MotherDuck** (data plane)
- **Convex** (UI surface, 13 tables)
- **TanStack Start** + **CopilotKit** + **AG-UI** (web)
- **Marimo** + **Jupyter** (notebooks — 17 .ipynb artefacts)
- **Google Cloud Run** (deployment)
- **Hugging Face Spaces** (5 studios)

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