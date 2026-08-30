# The NCCE Learning Graph Showcase

> The canonical guide for the
> [2026-08-31-uk-ncce-learning-graph-showcase-v1](../openspec/changes/2026-08-31-uk-ncce-learning-graph-showcase-v1/proposal.md)
> change — the **headline change of the 2026-08-31 batch**.

## What this is

The NCCE (National Centre for Computing Education) publishes a series of
**learning-graph PDFs** that show how a Y6-Y11 computing unit breaks
down into a row × column grid of skill outcomes per lesson. The BIEP
v3 substrate turns each of these PDFs into a structured
`LearningGraph` — a first-class row × column + prerequisite-arrows +
pedagogy-overlay + curriculum-journey model that every official syllabus
becomes after BAML extraction.

This showcase lifts 5 NCCE artefacts (4 PDFs + 1 deferred-download
placeholder) and ships the full BIEP v3 pipeline for them:

- DLT substrate → 11 `OFFICIAL_DOC_COLUMNS` rows
- CocoIndex App → grid-aware Markdown extraction
- BAML extraction → 8 classes + 9 functions
- Dagster asset group → 11 assets + 1 sensor
- Gradio studio → 4-tab interface (Render / Equivalencies / Generate / Pedagogy)
- HF Space → secondary distribution channel
- React landing page → `/learning-graphs`
- Firestore schema → `learningGraphs` + `prerequisiteEdges` collections
- Terraform env var → `LEARNING_GRAPH_FIRESTORE_COLLECTION`

## Data flow

```
                   ┌─────────────────────────────────────────────────┐
                   │  leabharlann/ollscoil_na_gaillimhe/education/   │
                   │  pgce/syllabus/                                  │
                   │  4 PDFs lifted verbatim                          │
                   │  1 S3 deferred-download placeholder              │
                   └────────────────────────────┬────────────────────┘
                                                │ cp (verbatim)
                                                ▼
                   ┌─────────────────────────────────────────────────┐
                   │  data/bi_ep/syllabi_raw/uk_ncce/curriculum/     │
                   │  + INDEX.yaml (sha256 verified)                 │
                   └────────────────────────────┬────────────────────┘
                                                │
        ┌───────────────────────────────────────┼─────────────────────┐
        ▼                                       ▼                     ▼
┌──────────────────┐                ┌─────────────────────┐  ┌─────────────────┐
│ dlt_pipelines/   │                │ cocoindex_flows/    │  │ baml_extracts/ │
│ uk_ncce_         │── 11 rows ────▶│ uk_ncce/learning_   │  │ learning_      │
│ learning_        │                │ graphs_app          │  │ graph.baml     │
│ graphs.py        │                │ (Docling grid       │  │ 8 classes +    │
│                  │                │  segmentation)      │  │ 9 functions    │
└────────┬─────────┘                └──────────┬──────────┘  └────────┬────────┘
         │                                     │                      │
         │                                     ▼                      ▼
         │                          ┌──────────────────────┐  ┌─────────────────────┐
         │                          │ data/bi_ep/syllabi_  │  │ orchestration/      │
         │                          │ md/uk_ncce/          │  │ defs/3_model_       │
         │                          │ (grid-aware MD)      │  │ lifecycle/uk_ncce_  │
         │                          └──────────────────────┘  │ learning_graphs.py  │
         │                                                    │ 11 Dagster assets   │
         │                                                    └──────────┬──────────┘
         │                                                               │
         │                                                               ▼
         │                                                    ┌─────────────────────┐
         │                                                    │ data/bi_ep/          │
         │                                                    │ learning_graphs/     │
         │                                                    │ + extracted_syllabi. │
         │                                                    │ sqlite + Firestore   │
         │                                                    │ learningGraphs       │
         │                                                    └──────────┬──────────┘
         │                                                               │
         │                                                               ▼
         │                                                    ┌─────────────────────┐
         │                                                    │ gemini_hackathon_    │
         │                                                    │ gradio/              │
         │                                                    │ an_learning_graph/   │
         │                                                    │ 4-tab Gradio studio  │
         │                                                    └──────────┬──────────┘
         │                                                               │
         │                                                               ▼
         │                                                    ┌─────────────────────┐
         │                                                    │ hf_spaces/           │
         │                                                    │ gemini_hackathon_    │
         │                                                    │ learning_graphs/     │
         │                                                    │ + web/src/routes/    │
         │                                                    │ learning-graphs/     │
         │                                                    └─────────────────────┘
         │
         ▼
┌──────────────────┐
│ Firestore        │
│ official_        │
│ documents        │
│ (existing        │
│  table)          │
└──────────────────┘
```

## The 8 BAML classes

```baml
class LearningGraph {
  id, jurisdiction, subject, year_level,
  rows, columns, cells,
  prerequisite_edges, pedagogy_principle_ids, skill_ribbons,
  source_pdf, source_pages, generated_at
}

class LearningGraphRow     { id, label, description, order_index }
class LearningGraphColumn  { id, label, order_index, lesson_number }
class LearningGraphCell    { id, row_id, column_id, skill_description,
                             syntax_code?, pedagogy_principle_ids[],
                             bloom_level, strand, confidence }
class PrerequisiteEdge     { source_cell_id, target_cell_id, kind, confidence }
class PedagogyPrinciple    { id, name, summary, how_to_apply, icon_url, source_page }
class CurriculumJourney    { id, jurisdiction, subject, year_levels[],
                             units_per_year[], attainment_targets[] }
class SkillRibbon          { id, label, applies_to_column_ids[], cross_cutting }
```

## The 9 BAML functions

### 3 generic

1. `ExtractLearningGraph(pdf_text, jurisdiction, subject, year_level)` → `LearningGraph`
2. `ExtractPedagogyPrinciples(pdf_text)` → `PedagogyPrinciple[]`
3. `ExtractCurriculumJourney(pdf_text, jurisdiction, subject)` → `CurriculumJourney`

### 6 per-subject (one per priority subject)

4. `ExtractCSLearningGraph(pdf_text, year_level)` → `CSLearningGraph`
5. `ExtractMathsLearningGraph(pdf_text, year_level)` → `MathsLearningGraph`
6. `ExtractEnglishLearningGraph(pdf_text, year_level)` → `EnglishLearningGraph`
7. `ExtractGaeilgeLearningGraph(pdf_text, year_level, language)` → `GaeilgeLearningGraph`
8. `ExtractChemistryLearningGraph(pdf_text, year_level)` → `ChemistryLearningGraph`
9. `ExtractGeographyLearningGraph(pdf_text, year_level)` → `GeographyLearningGraph`

The 6 per-subject classes use **composition** (a `base: LearningGraph`
field) rather than inheritance — BAML deliberately does not support
class inheritance. See `baml_extracts/learning_graph.baml` for the
canonical rationale + the per-subject strand + BloomLevel enums.

## The 4-tab Gradio studio

The headline surface — `gemini_hackathon_gradio.an_learning_graph`:

| Tab | What it does |
|---|---|
| **Render** | Pick (jurisdiction, subject, year_level) → render the canonical LearningGraph as a Plotly SVG heatmap with prerequisite edges overlaid |
| **Equivalencies** | STUB (shipped by [Change B](../openspec/changes/2026-08-31-learning-graph-equivalency-graph-v1/proposal.md)) — cell-level cross-jurisdiction equivalencies |
| **Generate from PDF** | Upload a syllabus PDF → run the per-subject BAML extractor → preview the generated row × column grid |
| **Pedagogy overlay** | STUB (shipped by [Change C](../openspec/changes/2026-08-31-pedagogy-overlay-renderer-v1/proposal.md)) — the 12 NCCE pedagogy principles overlay |

The theme integrates with the canonical British Isles 5-stage palette
(`Aistear / Bunscoil / MeanScoil / ScoilSinsearach / Ollscoil`) from
`gemini_hackathon_gradio/_common/theme.py`.

## Running locally

```bash
# 1. Lift the 4 NCCE PDFs (Phase 1 of the change)
#    — done at commit time; `data/bi_ep/syllabi_raw/uk_ncce/curriculum/`
#      contains the 4 PDFs + INDEX.yaml + the placeholder JSON.

# 2. Run the DLT substrate (11 OFFICIAL_DOC_COLUMNS rows)
uv run python -m dlt_pipelines.uk_ncce_learning_graphs

# 3. Run the CocoIndex App (grid-aware Markdown)
uv run python -m cocoindex_flows.uk_ncce.learning_graphs_app

# 4. Launch the 4-tab Gradio studio
uv run python -m gemini_hackathon_gradio.an_learning_graph

# 5. Or one-shot via mise
mise run data:ncce:download  # verifies the PDF lift
mise run data:ncce:extract   # DLT + CocoIndex
mise run data:ncce:visualise # the 4-renderer comparison notebook
mise run data:ncce:smoke     # full smoke (DLT + CocoIndex + Gradio)
```

## Acceptance

- `data/bi_ep/syllabi_raw/uk_ncce/curriculum/` has 5 PDFs (4 verbatim + 1 placeholder) + `INDEX.yaml` with sha256-verified entries
- `baml_extracts/learning_graph.baml` defines 8 classes + 9 functions (+ 6 per-subject composition classes)
- `baml-cli generate && baml-cli test baml_extracts/learning_graph.baml` passes (9 tests, 1 per function)
- `python -m cocoindex_flows.uk_ncce.learning_graphs_app` runs on all 5 PDFs (no crashes, .md output written)
- `python -m dlt_pipelines.uk_ncce_learning_graphs` emits 11 rows into `official_documents`
- HF Space `gemini_hackathon_learning_graphs` builds + serves the 4-tab studio
- `mise run lint && mise run py:typecheck && mise run turbo typecheck` green
- `pytest gemini_hackathon_backend/tests/` passes (no regressions)
- `web tsc --noEmit` zero errors
