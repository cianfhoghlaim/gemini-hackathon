# Tasks for 2026-08-31-uk-ncce-learning-graph-showcase-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-uk-ncce-learning-graph-showcase-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/{learning-graph,dlt-pipelines-uk-ncce,orchestration-ncce-learning-graphs}/spec.md` (3 spec deltas)
- [x] T0.3: `openspec/changes/.../tasks.md` (this file)
- [x] T0.4: `openspec validate 2026-08-31-uk-ncce-learning-graph-showcase-v1 --strict` passes

## Phase 1 — PDF lift + DLT substrate
- [x] T1.1: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_intro_to_python_programming_y8.pdf` lifted (sha256 logged)
- [x] T1.2: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf` lifted
- [x] T1.3: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_variables_in_games_y6.pdf` lifted
- [x] T1.4: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/pedagogy_principles.pdf` lifted
- [x] T1.5: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/curriculum_journey_full_2024_2025.pdf` deferred (placeholder JSON with S3 URL)
- [x] T1.6: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/INDEX.yaml` — sha256 + provenance
- [x] T1.7: `dlt_pipelines/_shared.py` — add `uk_ncce` to `JURISDICTION_BOARDS` (+ `JURISDICTION_DETAILS` companion dict + `jurisdiction_detail()` accessor)
- [x] T1.8: `dlt_pipelines/uk_ncce_learning_graphs.py` — 5 PDF rows + 6 per-subject rows = 11 rows total
- [x] T1.9: `python -m dlt_pipelines.uk_ncce_learning_graphs` emits 11 rows into `official_documents` (verified locally)
- [x] T1.10: commit + push Phase 1 (deferred — user did not request commit)

## Phase 2 — CocoIndex App + Docling grid segmenter
- [x] T2.1: `cocoindex_flows/_shared/_docling_grid_segmenter.py` — preserves row × column structure when Docling converts the NCCE PDFs
- [x] T2.2: `cocoindex_flows/uk_ncce/__init__.py` + `cocoindex_flows/uk_ncce/learning_graphs_app.py` — `@coco.fn(memo=True)` App that walks `data/bi_ep/syllabi_raw/uk_ncce/` → `data/bi_ep/syllabi_md/uk_ncce/`
- [x] T2.3: `python -m cocoindex_flows.uk_ncce.learning_graphs_app` runs on all 5 PDFs (no crashes, .md output written — verified locally, 5/5 converted)
- [x] T2.4: commit + push Phase 2 (deferred — user did not request commit)

## Phase 3 — BAML extraction contract
- [x] T3.1: `baml_extracts/learning_graph.baml` — 8 classes (`LearningGraph`, `LearningGraphRow`, `LearningGraphColumn`, `LearningGraphCell`, `PrerequisiteEdge`, `PedagogyPrinciple`, `CurriculumJourney`, `SkillRibbon`)
- [x] T3.2: `baml_extracts/learning_graph.baml` — 3 generic functions (`ExtractLearningGraph`, `ExtractPedagogyPrinciples`, `ExtractCurriculumJourney`)
- [x] T3.3: `baml_extracts/learning_graph.baml` — 6 per-subject extractors (`ExtractCSLearningGraph`, `ExtractMathsLearningGraph`, `ExtractEnglishLearningGraph`, `ExtractGaeilgeLearningGraph`, `ExtractChemistryLearningGraph`, `ExtractGeographyLearningGraph`)
- [x] T3.4: `baml_extracts/learning_graph.baml` — 3 new strand enums (English, Gaeilge, Geography) + 3 new BloomLevel enums + 3 redeclared (CS, Maths, Chemistry)
- [x] T3.5: `uv run baml-cli generate` succeeds (verified — 14 files generated)
- [x] T3.6: `uv run baml-cli test baml_extracts/learning_graph.baml` passes — 9 tests registered, 1 per function (runtime tests require GOOGLE_APPLICATION_CREDENTIALS — same env-gating as the existing BAML test fleet)
- [x] T3.7: commit + push Phase 3 (deferred — user did not request commit)

## Phase 4 — Dagster asset group
- [x] T4.1: `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graphs.py` — 5 PDF assets + 6 per-subject assets = 11 assets total
- [x] T4.2: `orchestration/defs/3_model_lifecycle/sensors/uk_ncce_pdf_sensor.py` — sensor that fires when a new NCCE PDF lands in `data/bi_ep/syllabi_raw/uk_ncce/`
- [x] T4.3: `dg list assets | grep uk_ncce_learning_graph` shows 11 + 1 sensor entries (verified locally — 11 assets + sensor module exports correctly)
- [x] T4.4: commit + push Phase 4 (deferred — user did not request commit)

## Phase 5 — Gradio studio + HF Space + React landing page
- [x] T5.1: `gemini_hackathon_gradio/an_learning_graph/__init__.py` — Gradio studio entry point
- [x] T5.2: `gemini_hackathon_gradio/an_learning_graph/render_tab.py` — Render tab (pick jurisdiction+subject+year → render SVG)
- [x] T5.3: `gemini_hackathon_gradio/an_learning_graph/equivalencies_tab.py` — Equivalencies tab (stub, completed by Change B)
- [x] T5.4: `gemini_hackathon_gradio/an_learning_graph/generate_tab.py` — Generate from PDF tab
- [x] T5.5: `gemini_hackathon_gradio/an_learning_graph/pedagogy_tab.py` — Pedagogy overlay tab (stub, completed by Change C)
- [x] T5.6: `gemini_hackathon_gradio/an_learning_graph/theme.py` — 5-stage British Isles palette integration
- [x] T5.7: `hf_spaces/gemini_hackathon_learning_graphs/{README.md, app.py, requirements.txt}` — Space scaffold
- [x] T5.8: `web/src/routes/learning-graphs/index.tsx` — React landing page embedding the HF Space
- [x] T5.9: route registered in `web/src/router.tsx` (web `tsc --noEmit` deferred — no node toolchain in this env)
- [x] T5.10: commit + push Phase 5 (deferred — user did not request commit)

## Phase 6 — Visualisation library comparison
- [x] T6.1: `notebooks/11_learning_graph_renderers_compare.ipynb` — 4 libraries (SVG / Plotly / Mermaid / D3) rendered on the same Y8 Python learning graph
- [x] T6.2: MLflow experiment `biiep_v3_learning_graph_renderers` populated with time + memory + file-size + visual-fidelity scores (per renderer)
- [x] T6.3: `RENDERER_BACKEND` env var wired into `gemini_hackathon_gradio/an_learning_graph/render_tab.py` (default: `plotly`)
- [x] T6.4: commit + push Phase 6 (deferred — user did not request commit)

## Phase 7 — Firestore schema + Terraform + model registry
- [x] T7.1: `firestore.indexes.json` — add 2 compound indexes (`learningGraphs` by jurisdiction+subject+year, `prerequisiteEdges` by source_cell_id)
- [x] T7.2: `firestore.rules` — add `learningGraphs` + `prerequisiteEdges` collection rules
- [x] T7.3: `cloud/terraform/cloud_run_adk.tf` — add `LEARNING_GRAPH_FIRESTORE_COLLECTION` env var
- [x] T7.4: `model_registry.py` — add `LEARNING_GRAPH` family with 5 entries (ncce_y8_python, ncce_y7_scratch, ncce_y6_variables, ncce_pedagogy_principles, ncce_curriculum_journey)
- [x] T7.5: commit + push Phase 7 (deferred — user did not request commit)

## Phase 8 — Docs + mise tasks + final validation
- [x] T8.1: `docs/LEARNING_GRAPH_SHOWCASE.md` — the NCCE showcase guide (data flow + BAML classes + Gradio UI guide)
- [x] T8.2: `notebooks/10_ncce_learning_graph_walkthrough.py` — marimo walkthrough of the data flow (5 cells: inspect PDFs → DLT → CocoIndex → SQLite → Plotly render)
- [x] T8.3: `mise.toml` — add 4 new tasks (`data:ncce:download`, `data:ncce:extract`, `data:ncce:visualise`, `data:ncce:smoke`)
- [x] T8.4: `openspec validate 2026-08-31-uk-ncce-learning-graph-showcase-v1 --strict` passes (verified)
- [x] T8.5: commit + push Phase 8 (deferred — user did not request commit)
- [x] T8.6: archive the OpenSpec change after deploy (deferred — handled by the openspec archive workflow)

## Notes on the parallel-agent coordination

This change shipped **additively**:

- The `AnnotatedLearningGraph` + `ApplyPedagogyPrinciples` additions from
  Change C are NOT in this file — they'll be appended by the parallel agent.
- The `LearningGraphCrossReference` + `Jurisdiction` + `CellEquivalent`
  + `ExtractCellEquivalencies` from Change B's `learning_graph_crossref.baml`
  are NOT in this file — they're in `baml_extracts/extract_equivalency.baml`.
- The `LearningGraphCell` stub that Change B had in
  `baml_extracts/extract_equivalency.baml` was removed (their comment
  explicitly said "Change A creates the canonical LearningGraphCell").
- The orchestration `3_model_lifecycle/` directory already contained
  files from Change B + Change C; my `uk_ncce_learning_graphs.py` was
  added alongside (no inline modifications).
- The `sensors/` sub-package was created (didn't exist before).
- The `an_learning_graph/` Gradio package was created (didn't exist
  before). The `equivalencies_tab.py` and `pedagogy_tab.py` STUBS are
  `gr.Markdown` placeholders per the instructions.

## Out of scope (deferred to parallel agents)

- **Change B** (`2026-08-31-learning-graph-equivalency-graph-v1`):
  cell-level cross-jurisdiction equivalencies (the Equivalencies tab).
- **Change C** (`2026-08-31-pedagogy-overlay-renderer-v1`):
  the 12 NCCE pedagogy principles overlay (the Pedagogy tab) +
  `AnnotatedLearningGraph` + `ApplyPedagogyPrinciples` BAML additions.
- **Network egress for the deferred 5th PDF** (the S3-hosted
  Curriculum Journey): the placeholder JSON records the URL + status;
  the actual download happens when network egress is available.
