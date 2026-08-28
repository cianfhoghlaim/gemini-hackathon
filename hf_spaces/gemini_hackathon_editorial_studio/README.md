---
title: "Editorial Studio — British Isles Education Workflow Canvas"
emoji: "🧑‍🎓"
colorFrom: "indigo"
colorTo: "purple"
sdk: gradio
sdk_version: 5.28.0
app_file: app.py
pinned: false
license: mit
short_description: "The full editorial studio — the LC/JC certificate pipeline as a drag-and-drop workflow canvas. The showcase of the gemini-hack"
---

# Editorial Studio — British Isles Education Workflow Canvas

> **gemini_hackathon** — the British Isles Education Platform.
> Submission for the **Google All Things Agentic Hackathon 2026** (Fortified Enterprise Fleet track).
> Built with **Google ADK 2** + **Gemini 3.5 Flash** + **Gemma 4 26B-A4B** (via Unsloth Studio) + **DiffusionGemma** (image gen) + **FLUX** (via InvokeAI) + **FIBO** (JSON-native image gen).

## Headline demo

The full editorial studio — the **LC/JC certificate pipeline as a drag-and-drop workflow canvas**. The showcase of the gemini-hackathon submission.

Given a learner_id + subject + stage, the 7-stage pipeline runs:
1. BAML extract from the 5 NCCA policy PDFs (data/ireland/ncaa_policy/)
2. Decompose outcomes (per-NCCA-LO)
3. Pull the exam paper + marking scheme (via DLT)
4. RAG over the NCCA policy corpus (via HybridSearchEngine: LanceDB + FalkorDB)
5. Generate the certificate background (FIBO + the 14-subject × 5-stage prompt bank)
6. Compose the certificate (PIL 1200×850: NCCA palette + UNOFFICIAL banner + provenance footer)
7. Save to provenance (MasteryLedger → Convex + LanceDB + Markdown memory)

## The 17-notebook collection

The full pipeline + Google ADK / AGUI / CopilotKit walkthrough lives in [`notebooks/converted/`](https://github.com/cianfhoghlaim/gemini-hackathon/tree/main/notebooks/converted).

## Live demo

- **Hosted URL** (Cloud Run): <https://gemini-hackathon-<hash>.a.run.app>
- **Source repo**: <https://github.com/cianfhoghlaim/gemini-hackathon>
- **Architecture**: [`docs/ARCHITECTURE.md`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/docs/ARCHITECTURE.md)

See the parent repo: [`gemini_hackathon_gradio/editorial_studio/`](https://github.com/cianfhoghlaim/gemini-hackathon)