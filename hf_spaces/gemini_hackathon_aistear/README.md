---
title: "Aistear — Early Years (0-6)"
emoji: "👶"
colorFrom: "orange"
colorTo: "amber"
sdk: gradio
sdk_version: 5.28.0
app_file: app.py
pinned: false
license: mit
short_description: "Aistear framework for ages 0-6 — play-based learning, 4 themes (wellbeing / identity / communicating / exploring)."
---

# Aistear — Early Years (0-6)

> **gemini_hackathon** — the British Isles Education Platform.
> Submission for the **Google All Things Agentic Hackathon 2026** (Fortified Enterprise Fleet track).
> Built with **Google ADK 2** + **Gemini 3.5 Flash** + **Gemma 4 26B-A4B** (via Unsloth Studio) + **DiffusionGemma** (image gen) + **FLUX** (via InvokeAI) + **FIBO** (JSON-native image gen).

## Headline demo

The 5-stage British Isles education palette (Aistear → Bunscoil → MeanScoil → Scoil Sinsearach → Ollscoil) across 8 subnations (Ireland + England live; NI / Wales / Scotland / IoM deferred).

## The 17-notebook collection

The full pipeline + Google ADK / AGUI / CopilotKit walkthrough lives in [`notebooks/converted/`](https://github.com/cianfhoghlaim/gemini-hackathon/tree/main/notebooks/converted):

- [`google_adk_agent_tree.ipynb`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/converted/google_adk_agent_tree.ipynb) — the ADK agent tree
- [`agui_event_protocol.ipynb`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/converted/agui_event_protocol.ipynb) — the 13 AGUI event types
- [`copilotkit_runtime_config.ipynb`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/converted/copilotkit_runtime_config.ipynb) — the CopilotKit runtime
- [`fleet_primitives.ipynb`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/converted/fleet_primitives.ipynb) — the 7 Fleet primitives
- Plus 13 marimo → .ipynb conversions of the per-subject + per-platform notebooks (the 6-step BIEP pipeline for each of the 8 NCCA LC subjects)

## Live demo

- **Hosted URL** (Cloud Run): <https://gemini-hackathon-<hash>.a.run.app>
- **Source repo**: <https://github.com/cianfhoghlaim/gemini-hackathon>
- **Architecture**: [`docs/ARCHITECTURE.md`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/docs/ARCHITECTURE.md)

See the parent repo: [`gemini_hackathon_gradio/editorial_studio/`](https://github.com/cianfhoghlaim/gemini-hackathon)