# notebooks/converted/ — the 17 Jupyter notebooks (Phase 7)

> **Status**: 13 converted marimo notebooks + 4 new ADK-focused notebooks.
> All .ipynb files execute end-to-end via `jupyter nbconvert --execute` (with the
> `notebooks/_shared/converted/marimo_stub.py` runtime replacement).

## The 17 notebooks (Layer 1 → Layer 5 walkthrough)

Each notebook has a 5-layer structure:

1. **Title + provenance** — what it shows, source marimo path, conversion method
2. **Google ADK wiring** — the LlmAgent tree + 5 tools + App wrapper + Runner
3. **AGUI 13-event protocol** — the events emitted during a chat turn
4. **CopilotKit consumption** — the runtime + route map + useRenderTool patterns
5. **The pipeline content** — the original marimo notebook (6-step BIEP pipeline)

## Index

### 4 NEW ADK-focused notebooks (Phase 7.4)

| Notebook | What it demos | Pipeline layer |
|---|---|---|
| [`google_adk_agent_tree.ipynb`](./google_adk_agent_tree.ipynb) | The complete ADK agent tree (root + 5 tools + App + Runner) | Layer 2 |
| [`agui_event_protocol.ipynb`](./agui_event_protocol.ipynb) | The 13 AGUI event types + the SSE stream | Layer 3 |
| [`copilotkit_runtime_config.ipynb`](./copilotkit_runtime_config.ipynb) | The CopilotKit + AGUI + TanStack Start integration | Layer 4 |
| [`fleet_primitives.ipynb`](./fleet_primitives.ipynb) | The 7 Fleet primitives wrapping run_agent_turn() | Layer 2 |

### 13 converted marimo notebooks (Phase 7.2)

| Notebook | Subject / Pipeline | Source marimo |
|---|---|---|
| [`lc_mathematics.ipynb`](./lc_mathematics.ipynb) | LC Maths — 6-step BIEP pipeline | `cianfhoghlaim/notebooks/lc/mathematics.py` |
| [`lc_english.ipynb`](./lc_english.ipynb) | LC English — 6-step BIEP pipeline | `cianfhoghlaim/notebooks/lc/english.py` |
| [`lc_gaeilge.ipynb`](./lc_gaeilge.ipynb) | LC Gaeilge — 6-step BIEP pipeline (bilingual) | `cianfhoghlaim/notebooks/lc/gaeilge.py` |
| [`lc_chemistry.ipynb`](./lc_chemistry.ipynb) | LC Chemistry — 6-step BIEP pipeline | `cianfhoghlaim/notebooks/lc/chemistry.py` |
| [`lc_physics.ipynb`](./lc_physics.ipynb) | LC Physics — 6-step BIEP pipeline | `cianfhoghlaim/notebooks/lc/physics.py` |
| [`lc_biology.ipynb`](./lc_biology.ipynb) | LC Biology — 6-step BIEP pipeline | `cianfhoghlaim/notebooks/lc/biology.py` |
| [`lc_geography.ipynb`](./lc_geography.ipynb) | LC Geography — 6-step BIEP pipeline | `cianfhoghlaim/notebooks/lc/geography.py` |
| [`lc_computer_science.ipynb`](./lc_computer_science.ipynb) | LC Computer Science — 6-step BIEP pipeline | `cianfhoghlaim/notebooks/lc/computer_science.py` |
| [`leaving_cert_subject_panel.ipynb`](./leaving_cert_subject_panel.ipynb) | 7-tab grouped LC panel (Maths/Chem/Geo/Gaeilge/English/CS + EN-vs-GA + Ask BAML) | `cianfhoghlaim/notebooks/40_leaving_cert_subject_panel.py` |
| [`biep_subject_full_pipeline.ipynb`](./biep_subject_full_pipeline.ipynb) | Parameterised 6-subject pipeline (multiselect) | `cianfhoghlaim/notebooks/10_biep_pipeline_lakehouse_07_subject_full_pipeline.py` |
| [`marimo_patterns_tour.ipynb`](./marimo_patterns_tour.ipynb) | The 6-pillar marimo v14 demo (P1-P6) | `cianfhoghlaim/notebooks/00_marimo_patterns_tour.py` |
| [`unsloth_vision_compare.ipynb`](./unsloth_vision_compare.ipynb) | The 10-way OCR/VLM benchmark (the "Gemini vs the world" demo) | `cianfhoghlaim/notebooks/30_unsloth_vision_compare.py` |
| [`control_panel.ipynb`](./control_panel.ipynb) | The 5-tab deployment control panel | `cianfhoghlaim/notebooks/00_control_panel.py` |

## How to run

```bash
# Validate all 17 .ipynb files execute cleanly
cd /Users/cianmacandeisigh/dev/gemini_hackathon
uv run --with jupyter jupyter nbconvert --to notebook --execute --inplace notebooks/converted/*.ipynb

# Or open in JupyterLab
uv run --with jupyter jupyter lab notebooks/converted/
```

The `notebooks/_shared/converted/marimo_stub.py` replaces the marimo runtime
so the .ipynb files execute end-to-end in any Jupyter kernel. The
interactive `mo.ui.*` widgets become static code cells (they print None).

## How they were converted

```bash
# 13 conversions (Phase 7.2)
cd /Users/cianmacandeisigh/dev/cianfhoghlaim
uv run --with marimo marimo export ipynb notebooks/lc/mathematics.py \
  -o /Users/cianmacandeisigh/dev/gemini_hackathon/notebooks/converted/lc_mathematics.ipynb
# ... (12 more, see scripts/sync/notebooks.sh)
```

The 4 ADK-focused notebooks were authored from scratch in Phase 7.4.