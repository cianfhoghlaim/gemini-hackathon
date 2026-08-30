---
title: "An Léaráid Foghlama — The Learning Graph Studio"
emoji: "🧩"
colorFrom: "green"
colorTo: "yellow"
sdk: gradio
sdk_version: 5.28.0
app_file: app.py
pinned: false
license: mit
short_description: "The 4-tab learning-graph studio — Render, Equivalencies (stub), Generate from PDF, Pedagogy overlay (stub). The NCCE Y8 Python showcase."
---

# An Léaráid Foghlama — The Learning Graph Studio

> **gemini_hackathon** — the British Isles Education Platform.
> The headline studio for the BIEP v3 learning-graph substrate (the 2026-08-31 Learning Graph era).

## What is this

A 4-tab Gradio studio that demonstrates how every official syllabus
becomes a structured row × column learning graph:

1. **Render** — pick a jurisdiction, subject, and year level; view the canonical LearningGraph as a Plotly SVG heatmap with prerequisite edges overlaid.
2. **Equivalencies** — STUB. Cell-level cross-jurisdiction equivalencies are shipped by Change B (`2026-08-31-learning-graph-equivalency-graph-v1`).
3. **Generate from PDF** — upload a syllabus PDF, run the per-subject BAML extractor (`ExtractCSLearningGraph`, `ExtractMathsLearningGraph`, …), preview the generated grid.
4. **Pedagogy overlay** — STUB. The 12 NCCE pedagogy principles overlay is shipped by Change C (`2026-08-31-pedagogy-overlay-renderer-v1`).

## The NCCE Y8 Python showcase

The canonical input is `learning_graph_intro_to_python_programming_y8.pdf`
(lifted verbatim from the upstream
`leabharlann/ollscoil_na_gaillimhe/education/pgce/syllabus/` source). The
extractor produces a 4-row × 7-column grid mapping Y8 Python programming
outcomes to lesson columns + a prerequisite arrow graph.

## Source

- **Repo:** https://github.com/cianfhoghlaim/gemini-hackathon
- **Architecture:** `docs/ARCHITECTURE.md`
- **Showcase guide:** `docs/LEARNING_GRAPH_SHOWCASE.md`
- **BAML contract:** `baml_extracts/learning_graph.baml`

## Deploy

This Space lazy-imports the canonical
`gemini_hackathon_gradio.an_learning_graph` package — when that package
is missing, the Space falls back to a 4-tab `gr.Markdown` placeholder so
the demo at least renders. The canonical deployment is Cloud Run (the HF
Space is the secondary mirror, per the Phase 8 GCP-first refactor).

```bash
hf upload cianfhoghlaim/gemini-hackathon-learning-graphs hf_spaces/gemini-hackathon_learning_graphs --repo-type space
```
