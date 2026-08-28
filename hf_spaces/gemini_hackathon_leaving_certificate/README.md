---
title: "Scoil Sinsearach — Leaving Certificate (15-19)"
emoji: "🎓"
colorFrom: "orange"
colorTo: "yellow"
sdk: gradio
sdk_version: 5.28.0
app_file: app.py
pinned: false
license: mit
short_description: "Scoil Sinsearach (Senior Cycle / Leaving Certificate) — the headline stage. 14 NCCA LC subjects, the LC certificate pipeline."
---

# Scoil Sinsearach — Leaving Certificate (15-19)

> **gemini_hackathon** — the British Isles Education Platform.
> Submission for the **Google All Things Agentic Hackathon 2026** (Fortified Enterprise Fleet track).
> Built with **Google ADK 2** + **Gemini 3.5 Flash** + **Gemma 4 26B-A4B** (via Unsloth Studio) + **DiffusionGemma** (image gen) + **FLUX** (via InvokeAI) + **FIBO** (JSON-native image gen).

## Headline demo

The 5-stage British Isles education palette (Aistear → Bunscoil → MeanScoil → Scoil Sinsearach → Ollscoil) across 8 subnations (Ireland + England live; NI / Wales / Scotland / IoM deferred). Every page is themable per-session.

**The showcase**: the LC/JC certificate pipeline (W14) — given a learner_id + subject + stage, the 7-stage pipeline (BAML extract → decompose → paper+marking → RAG over the 5 NCCA policy PDFs → FIBO background → PIL compose → MasteryLedger persist) produces an NCCA-cited certificate with the UNOFFICIAL banner.

## The 17-notebook collection

Each pipeline + each Google ADK / AGUI / CopilotKit surface has a corresponding Jupyter notebook in [`notebooks/converted/`](https://github.com/cianfhoghlaim/gemini-hackathon/tree/main/notebooks/converted).

| Notebook | Pipeline layer |
|---|---|
| [`google_adk_agent_tree.ipynb`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/converted/google_adk_agent_tree.ipynb) | The LlmAgent + 5 tools + App + Runner + Fleet |
| [`agui_event_protocol.ipynb`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/converted/agui_event_protocol.ipynb) | The 13 AGUI event types + render_agui_events |
| [`copilotkit_runtime_config.ipynb`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/converted/copilotkit_runtime_config.ipynb) | The CopilotKit + AGUI + TanStack Start wiring |
| [`fleet_primitives.ipynb`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/notebooks/converted/fleet_primitives.ipynb) | The 7 Fleet primitives wrapping run_agent_turn |
| `lc_mathematics.ipynb` | LC Maths — 6-step BIEP pipeline |
| `lc_english.ipynb` | LC English — 6-step BIEP pipeline |
| `lc_gaeilge.ipynb` | LC Gaeilge — 6-step BIEP pipeline (bilingual) |
| `lc_chemistry.ipynb` | LC Chemistry — 6-step BIEP pipeline |
| `lc_physics.ipynb` | LC Physics — 6-step BIEP pipeline |
| `lc_biology.ipynb` | LC Biology — 6-step BIEP pipeline |
| `lc_geography.ipynb` | LC Geography — 6-step BIEP pipeline |
| `lc_computer_science.ipynb` | LC Computer Science — 6-step BIEP pipeline |
| `leaving_cert_subject_panel.ipynb` | 7-tab grouped LC panel |
| `biep_subject_full_pipeline.ipynb` | Parameterised 6-subject pipeline |
| `marimo_patterns_tour.ipynb` | The 6-pillar marimo v14 demo (P1-P6) |
| `unsloth_vision_compare.ipynb` | The 10-way OCR/VLM benchmark |
| `control_panel.ipynb` | The 5-tab deployment control panel |

## Live demo

- **Hosted URL** (Cloud Run): <https://gemini-hackathon-<hash>.a.run.app>
- **Source repo**: <https://github.com/cianfhoghlaim/gemini-hackathon>
- **Architecture**: [`docs/ARCHITECTURE.md`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/docs/ARCHITECTURE.md)
- **Submission writeup**: [`docs/SUBMISSION_WRITEUP.md`](https://github.com/cianfhoghlaim/gemini-hackathon/blob/main/docs/SUBMISSION_WRITEUP.md)

See the parent repo: [`gemini_hackathon_gradio/editorial_studio/`](https://github.com/cianfhoghlaim/gemini-hackathon)