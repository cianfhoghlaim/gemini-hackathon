# All Things Agentic Hackathon 2026 — gemini-hackathon submission

> **Built for the purposes of entering this hackathon.**
> #AllThingsAgenticHackathon

I just shipped my submission to the **Google All Things Agentic Hackathon 2026** — a British Isles education platform that builds an LC/JC certificate from the 5 NCCA policy PDFs.

## What it does

The headline: the **LC/JC certificate pipeline** takes a learner_id + subject + stage and produces a 1200×850 NCCA-cited certificate via a 7-stage pipeline (BAML extract → decompose outcomes → pull exam paper + marking scheme → RAG over the NCCA policy corpus via LanceDB + FalkorDB → FIBO background → PIL compose → save to MasteryLedger).

The bonus: a **280-cell asset-comparison leaderboard** that compares 7 image-gen backends (FIBO + DiffusionGemma + FLUX.1-schnell + FLUX.2-dev + Gemini 2.5 Flash Image + Imagen 3 + Imagen 4) on 8 NCCA LC subjects × 5 topics each.

## The stack

- **Google ADK 2** (the mandatory framework)
- **Gemini 3.5 Flash** via Vertex AI (Tier 1)
- **Gemma 4 26B-A4B** via Unsloth Studio (Tier 2 local)
- **DiffusionGemma** (Google's first image-gen Gemma)
- **Imagen 3** + **Imagen 4** (Vertex AI)
- **FLUX.1-schnell** + **FLUX.2-dev** (InvokeAI)
- **FIBO** (JSON-native ComfyUI)
- **BAML** (structured extraction)
- **CocoIndex** + **LanceDB** + **FalkorDB** (MasteryLedger 4-backend)
- **DuckDB** + **MotherDuck**
- **Convex** (13 tables)
- **TanStack Start** + **CopilotKit** + **AG-UI**
- **Marimo** + **Jupyter** (17 .ipynb notebooks)
- **Google Cloud Run**
- **5 Hugging Face Spaces**

## The 17 Jupyter notebooks

The notebooks ARE the demo. Each walks through a specific pipeline + the Google ADK / AGUI / CopilotKit internals:

- `google_adk_agent_tree.ipynb` — the LlmAgent + 5 tools + App + Runner
- `agui_event_protocol.ipynb` — the 13 AGUI event types + render_agui_events
- `copilotkit_runtime_config.ipynb` — the CopilotKit + AGUI + TanStack Start wiring
- `fleet_primitives.ipynb` — the 7 Fleet primitives
- 13 more: per-subject (8 LC subjects) + per-platform (3 platform demos)

## Live

- **Repo**: https://github.com/cianfhoghlaim/gemini-hackathon
- **Cloud Run**: <live URL goes here>
- **5 HF Spaces**: https://huggingface.co/cianfhoghlaim

#AllThingsAgenticHackathon #GoogleADK #Gemini #Gemma4 #DiffusionGemma #FLUX #FIBO #Imagen4 #BAML #CocoIndex #LanceDB #FalkorDB #DuckDB #Convex #TanStack #CopilotKit #AGUI #CloudRun #HuggingFace