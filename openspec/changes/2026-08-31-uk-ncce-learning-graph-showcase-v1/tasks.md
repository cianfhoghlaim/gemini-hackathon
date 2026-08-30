# Tasks for 2026-08-31-uk-ncce-learning-graph-showcase-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-uk-ncce-learning-graph-showcase-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/{learning-graph,dlt-pipelines-uk-ncce,orchestration-ncce-learning-graphs}/spec.md` (3 spec deltas)
- [x] T0.3: `openspec/changes/.../tasks.md` (this file)
- [x] T0.4: `openspec validate 2026-08-31-uk-ncce-learning-graph-showcase-v1 --strict` passes

## Phase 1 — PDF lift + DLT substrate
- [ ] T1.1: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_intro_to_python_programming_y8.pdf` lifted (sha256 logged)
- [ ] T1.2: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf` lifted
- [ ] T1.3: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_variables_in_games_y6.pdf` lifted
- [ ] T1.4: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/pedagogy_principles.pdf` lifted
- [ ] T1.5: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/curriculum_journey_full_2024_2025.pdf` downloaded from S3 (sha256 dedup)
- [ ] T1.6: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/INDEX.yaml` — sha256 + provenance
- [ ] T1.7: `dlt_pipelines/_shared.py` — add `uk_ncce` to `JURISDICTION_BOARDS`
- [ ] T1.8: `dlt_pipelines/uk_ncce_learning_graphs.py` — 5 PDF rows + 6 per-subject rows = 11 rows total
- [ ] T1.9: `python -m dlt_pipelines.uk_ncce_learning_graphs` emits 11 rows into `official_documents`
- [ ] T1.10: commit + push Phase 1

## Phase 2 — CocoIndex App + Docling grid segmenter
- [ ] T2.1: `cocoindex_flows/_shared/_docling_grid_segmenter.py` — preserves row × column structure when Docling converts the NCCE PDFs
- [ ] T2.2: `cocoindex_flows/uk_ncce/learning_graphs_app.py` — `@coco.fn(memo=True)` App that walks `data/bi_ep/syllabi_raw/uk_ncce/` → `data/bi_ep/syllabi_md/uk_ncce/`
- [ ] T2.3: `python -m cocoindex_flows.uk_ncce.learning_graphs_app` runs on all 5 PDFs (no crashes, .md output written)
- [ ] T2.4: commit + push Phase 2

## Phase 3 — BAML extraction contract
- [ ] T3.1: `baml_extracts/learning_graph.baml` — 8 classes (`LearningGraph`, `LearningGraphRow`, `LearningGraphColumn`, `LearningGraphCell`, `PrerequisiteEdge`, `PedagogyPrinciple`, `CurriculumJourney`, `SkillRibbon`)
- [ ] T3.2: `baml_extracts/learning_graph.baml` — 3 generic functions (`ExtractLearningGraph`, `ExtractPedagogyPrinciples`, `ExtractCurriculumJourney`)
- [ ] T3.3: `baml_extracts/learning_graph.baml` — 6 per-subject extractors (`ExtractCSLearningGraph`, `ExtractMathsLearningGraph`, `ExtractEnglishLearningGraph`, `ExtractGaeilgeLearningGraph`, `ExtractChemistryLearningGraph`, `ExtractGeographyLearningGraph`)
- [ ] T3.4: `baml_extracts/learning_graph.baml` — 3 new strand enums (English, Gaeilge, Geography) + 3 new BloomLevel enums (lifted from existing where possible)
- [ ] T3.5: `uv run baml-cli generate`
- [ ] T3.6: `uv run baml-cli test baml_extracts/learning_graph.baml` passes (1+ tests per function)
- [ ] T3.7: commit + push Phase 3

## Phase 4 — Dagster asset group
- [ ] T4.1: `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graphs.py` — 5 PDF assets + 6 per-subject assets = 11 assets total
- [ ] T4.2: `orchestration/defs/3_model_lifecycle/sensors/uk_ncce_pdf_sensor.py` — sensor that fires when a new NCCE PDF lands in `data/bi_ep/syllabi_raw/uk_ncce/`
- [ ] T4.3: `dg list assets | grep uk_ncce_learning_graph` shows 11 + 1 sensor entries
- [ ] T4.4: commit + push Phase 4

## Phase 5 — Gradio studio + HF Space + React landing page
- [ ] T5.1: `gemini_hackathon_gradio/an_learning_graph/__init__.py` — Gradio studio entry point
- [ ] T5.2: `gemini_hackathon_gradio/an_learning_graph/render_tab.py` — Render tab (pick jurisdiction+subject+year → render SVG)
- [ ] T5.3: `gemini_hackathon_gradio/an_learning_graph/equivalencies_tab.py` — Equivalencies tab (stub, completed by Change B)
- [ ] T5.4: `gemini_hackathon_gradio/an_learning_graph/generate_tab.py` — Generate from PDF tab
- [ ] T5.5: `gemini_hackathon_gradio/an_learning_graph/pedagogy_tab.py` — Pedagogy overlay tab (stub, completed by Change C)
- [ ] T5.6: `gemini_hackathon_gradio/an_learning_graph/theme.py` — 5-stage British Isles palette integration
- [ ] T5.7: `hf_spaces/gemini_hackathon_learning_graphs/{README.md, app.py, requirements.txt}` — Space scaffold
- [ ] T5.8: `web/src/routes/learning-graphs/index.tsx` — React landing page embedding the HF Space
- [ ] T5.9: `web tsc --noEmit` zero errors
- [ ] T5.10: commit + push Phase 5

## Phase 6 — Visualisation library comparison
- [ ] T6.1: `notebooks/11_learning_graph_renderers_compare.ipynb` — 4 libraries (SVG / Plotly / Mermaid / D3) rendered on the same Y8 Python learning graph
- [ ] T6.2: MLflow experiment `biiep_v3_learning_graph_renderers` populated with time + memory + file-size + visual-fidelity scores
- [ ] T6.3: `RENDERER_BACKEND` env var wired into `gemini_hackathon_gradio/an_learning_graph/render_tab.py` (default: `plotly`)
- [ ] T6.4: commit + push Phase 6

## Phase 7 — Firestore schema + Terraform + model registry
- [ ] T7.1: `firestore.indexes.json` — add 2 compound indexes (`learningGraphs` by jurisdiction+subject+year, `prerequisiteEdges` by source_cell_id)
- [ ] T7.2: `firestore.rules` — add `learningGraphs` + `prerequisiteEdges` collection rules
- [ ] T7.3: `cloud/terraform/cloud_run_adk.tf` — add `LEARNING_GRAPH_FIRESTORE_COLLECTION` env var
- [ ] T7.4: `model_registry.py` — add `LEARNING_GRAPH` family
- [ ] T7.5: commit + push Phase 7

## Phase 8 — Docs + mise tasks + final validation
- [ ] T8.1: `README.md` — new top-level "The NCCE learning graph showcase" section
- [ ] T8.2: `ARCHITECTURE.md` — bump 23 → 24 changes, new §15 NCCE showcase
- [ ] T8.3: `openspec/changes/INDEX.md` — bump 23 → 24
- [ ] T8.4: `mise.toml` — add 4 new tasks (`data:ncce:download`, `data:ncce:extract`, `data:ncce:visualise`, `data:ncce:smoke`)
- [ ] T8.5: `docs/LEARNING_GRAPH_SHOWCASE.md` — data flow + BAML classes + Gradio UI guide
- [ ] T8.6: `notebooks/10_ncce_learning_graph_walkthrough.ipynb` — marimo walkthrough
- [ ] T8.7: `mise run lint && mise run py:typecheck && mise run turbo typecheck` green
- [ ] T8.8: `pytest gemini_hackathon_backend/tests/` passes (no regressions)
- [ ] T8.9: `openspec validate 2026-08-31-uk-ncce-learning-graph-showcase-v1 --strict` passes
- [ ] T8.10: commit + push Phase 8
- [ ] T8.11: archive the OpenSpec change after deploy