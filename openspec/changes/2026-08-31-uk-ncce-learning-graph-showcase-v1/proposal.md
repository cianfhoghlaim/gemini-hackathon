# 2026-08-31-uk-ncce-learning-graph-showcase-v1

> **The headline change of the 2026-08-31 batch.** Lifts the 5 NCCE PDFs
> (3 learning graphs + pedagogy + the full Y7→Y11 Curriculum Journey)
> into the gemini_hackathon BIEP substrate as the canonical example of
> how every official syllabus becomes a structured row × column learning
> graph. Ships the BAML extraction contract, the CocoIndex App, the
> Dagster asset group, the Gradio studio + HF Space, and the README
> section that frames the whole platform around this showcase.

## Why

The `leabharlann/ollscoil_na_gaillimhe/education/pgce/syllabus/`
folder in the upstream cianfhoghlaim monorepo holds **4 canonical NCCE
artefacts**:

1. `learning_graph_intro_to_python_programming_y8.pdf` — a 4-row × 7-column grid mapping Y8 Python programming outcomes to lesson columns + a prerequisite arrow graph
2. `learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf` — a 6-column Y7 Scratch unit grid with 3 cross-cutting skill ribbons
3. `learning_graph_variables_in_games_y6.pdf` — a Y6 unit grid
4. `pedagogy_principles.pdf` — 12 named pedagogy principles (Lead with concepts, Work together, Get hands-on, …)

Plus the S3-hosted
[Curriclum.Journey_Full_2024_2025.pdf](https://ncce-curriculum-production.s3.eu-west-1.amazonaws.com/qvz4tnrz4y7rrxayqz2qfji94nko) — the full NCCE Computing journey from Y7 to Y11.

These 5 PDFs are the **canonical pattern** for how an official syllabus
becomes a structured learning graph. Today, every jurisdiction's syllabus
arrives as a flat PDF; the BIEP needs to turn each one into:

- a `LearningGraph` (row × column grid)
- a `PrerequisiteEdge[]` (the arrows)
- a `PedagogyPrinciple[]` (cross-cutting teaching guidance)
- a `CurriculumJourney` (the multi-year path)

Without this change, the BIEP has the **NCCA Senior Cycle certificate
pipeline** (W14) for one specific use case, but no general-purpose
"structured syllabus" pipeline. With this change, the BIEP can ingest
**any** official syllabus — AQA, OCR, Edexcel, WJEC, SQA, CCEA, IoM —
and produce the same kind of structured artefact.

This is the **6th workstream** of the GCP-first era (after the 4
2026-08-30 changes + the 17 2026-08-27 workstreams).

## What changes

### Phase 0 — PDF lift (this commit)

- **Verbatim copy** the 4 NCCE PDFs from
  `leabharlann/ollscoil_na_gaillimhe/education/pgce/syllabus/` to
  `data/bi_ep/syllabi_raw/uk_ncce/curriculum/` (matching the
  `data/ireland/ncca_policy/` pattern with `INDEX.yaml` + sha256
  checksums).
- **Download** the 5th PDF from the S3 URL to
  `data/bi_ep/syllabi_raw/uk_ncce/curriculum/curriculum_journey_full_2024_2025.pdf`
  (idempotent sha256 dedup; `source_kind` = `'downloaded'`).
- **Add `uk_ncce` to `JURISDICTION_BOARDS`** in `dlt_pipelines/_shared.py`.

### Phase 1 — DLT + CocoIndex substrate

- **New `dlt_pipelines/uk_ncce_learning_graphs.py`** — 5 PDF rows + 6 per-subject rows = 11 rows total.
- **New `cocoindex_flows/_shared/_docling_grid_segmenter.py`** — preserves the row × column structure when Docling converts the NCCE PDFs to Markdown.
- **New `cocoindex_flows/uk_ncce/learning_graphs_app.py`** — Docling converter that walks `data/bi_ep/syllabi_raw/uk_ncce/` → `data/bi_ep/syllabi_md/uk_ncce/` with grid-aware page segmentation.

### Phase 2 — BAML extraction contract

- **New `baml_extracts/learning_graph.baml`** — 8 classes + 9 functions:
  - `LearningGraph`, `LearningGraphRow`, `LearningGraphColumn`, `LearningGraphCell`, `PrerequisiteEdge`, `PedagogyPrinciple`, `CurriculumJourney`, `SkillRibbon`
  - `ExtractLearningGraph` (generic), `ExtractPedagogyPrinciples`, `ExtractCurriculumJourney`
  - 6 per-subject extractors for the priority subjects: `ExtractCSLearningGraph`, `ExtractMathsLearningGraph`, `ExtractEnglishLearningGraph`, `ExtractGaeilgeLearningGraph`, `ExtractChemistryLearningGraph`, `ExtractGeographyLearningGraph`

### Phase 3 — Dagster asset group

- **New `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graphs.py`** — 11 assets (5 PDFs + 6 per-subject extracted graphs).
- **New `orchestration/defs/3_model_lifecycle/sensors/uk_ncce_pdf_sensor.py`** — sensor that fires when a new NCCE PDF lands.

### Phase 4 — Gradio studio + HF Space + React landing page

- **New `gemini_hackathon_gradio/an_learning_graph/`** — 4-tab Gradio studio: Render / Equivalencies (stub) / Generate from PDF / Pedagogy overlay (stub).
- **New `hf_spaces/gemini_hackathon_learning_graphs/`** — lazy-imports the studio.
- **New `web/src/routes/learning-graphs/`** — thin React landing page embedding the HF Space via `<iframe>`.

### Phase 5 — Visualisation library comparison

- **New `notebooks/11_learning_graph_renderers_compare.ipynb`** — renders the same Y8 Python learning graph with SVG / Plotly / Mermaid / D3 and logs time + memory + file-size + visual-fidelity (RAGAS over 10 sample graphs) to **MLflow experiment `biiep_v3_learning_graph_renderers`**.

### Phase 6 — Firestore schema + Terraform

- **`firestore.indexes.json`** — add 2 compound indexes (`learningGraphs` by jurisdiction+subject+year, `prerequisiteEdges` by source_cell_id).
- **`firestore.rules`** — add `learningGraphs` + `prerequisiteEdges` collection rules (read-public, write-admin).
- **`cloud/terraform/cloud_run_adk.tf`** — add `LEARNING_GRAPH_FIRESTORE_COLLECTION` env var.

### Phase 7 — Docs + mise tasks + model registry

- **README + ARCHITECTURE.md refresh** — new top-level "The NCCE learning graph showcase" section; `INDEX.md` bump 23 → 24.
- **`mise.toml`** — add 4 new tasks (`data:ncce:download`, `data:ncce:extract`, `data:ncce:visualise`, `data:ncce:smoke`).
- **`model_registry.py`** — add `LEARNING_GRAPH` family with `ncce_y8_python`, `ncce_y7_scratch`, etc.

## Acceptance

- `data/bi_ep/syllabi_raw/uk_ncce/curriculum/` has 5 PDFs (sha256-verified via `INDEX.yaml`)
- `baml_extracts/learning_graph.baml` defines 8 classes + 9 functions
- `baml-cli generate && baml-cli test baml_extracts/learning_graph.baml` passes
- `python -m cocoindex_flows.uk_ncce.learning_graphs_app` runs on all 5 PDFs
- `python -m dlt_pipelines.uk_ncce_learning_graphs` emits 11 rows into `official_documents`
- `mise run dagster:list-assets | grep uk_ncce_learning_graph` shows 11 assets
- HF Space `gemini_hackathon_learning_graphs` builds + serves the SVG
- `openspec validate 2026-08-31-uk-ncce-learning-graph-showcase-v1 --strict` passes
- `mise run lint && mise run py:typecheck && mise run turbo typecheck` green
- `pytest gemini_hackathon_backend/tests/` passes (no regressions)
- `web tsc --noEmit` zero errors

## Dependencies

- **Blocked by:** the 4 NEW 2026-08-30 changes (`gcp-first-iac-refactor-v1`, `cocoindex-pdf-pipeline-v1`, `observability-otel-completeness-v1`, `retire-letta-wire-vertex-memory-bank-v1`) — all merged to main.
- **Unblocks:** the 2 follow-on changes (`2026-08-31-learning-graph-equivalency-graph-v1`, `2026-08-31-pedagogy-overlay-renderer-v1`).
- **Cross-repo:** the upstream cianfhoghlaim NCCE source folder is unchanged; this is a one-way verbatim copy.

## Compatibility

- **No code changes required** for callers — the new DLT resource + CocoIndex App + Dagster asset + BAML functions all slot into the existing BIEP substrate without breaking changes.
- The new `uk_ncce` jurisdiction is added to `JURISDICTION_BOARDS` as the 9th entry; existing pipelines are unaffected.
- The new BAML classes are additive — they extend (not replace) the existing `LCLearningOutcome` / `LCSyllabusDocument` pattern in `baml_extracts_education/`.
- The new Gradio studio + HF Space follow the existing 5-studio + 5-Space pattern; no changes to `hf_spaces/_generate.py`.