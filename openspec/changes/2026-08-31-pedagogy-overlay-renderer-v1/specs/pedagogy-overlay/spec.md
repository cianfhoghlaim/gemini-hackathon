# Spec Delta: pedagogy-overlay (Phase 1 — dynamic extraction + cached overlay)

This delta is applied by the OpenSpec change
[`2026-08-31-pedagogy-overlay-renderer-v1`](../proposal.md). It describes the
**ADDED** Requirements to the canonical `pedagogy-overlay` capability
that this change introduces.

## ADDED Requirements

### Requirement: `baml_extracts/learning_graph.baml` SHALL expose an `ApplyPedagogyPrinciples` function

The module SHALL add:

- `AnnotatedLearningGraph` class — `(graph: LearningGraph, cell_annotations: map<cell_id, string[]>, pedagogy_source: "cache" | "cognee" | "live_pdf", generated_at: string)`
- `ApplyPedagogyPrinciples(graph: LearningGraph, principles: PedagogyPrinciple[]) -> AnnotatedLearningGraph` function

The function SHALL annotate every cell in the graph with the IDs of the
pedagogy principles that apply (e.g. a cell teaching "trace through a
sequence" gets tagged with `["PRIMM", "foster_program_comprehension"]`).

#### Scenario: Every cell gets at least 1 principle

- **WHEN** `ApplyPedagogyPrinciples` is called on the NCCE Y8 Python learning graph + the 12 NCCE pedagogy principles
- **THEN** every `LearningGraphCell` SHALL appear in `cell_annotations` with at least 1 principle ID
- **AND** the function SHALL return a non-null `AnnotatedLearningGraph`

### Requirement: `cocoindex_flows/uk_ncce/pedagogy_cache.py` SHALL cache the 12 pedagogy principles to disk + Cognee

The module SHALL expose a `@coco.fn(memo=True)` App that:

- Reads `data/bi_ep/syllabi_raw/uk_ncce/curriculum/pedagogy_principles.pdf`
- Calls `ExtractPedagogyPrinciples` BAML function
- Writes the 12 principles to `data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json` (keyed on sha256)
- Uploads to Cognee dataset `gh_cognee_pedagogy_dataset`

#### Scenario: First run extracts from PDF

- **WHEN** the cache file does not exist
- **THEN** the App SHALL call `ExtractPedagogyPrinciples` on the PDF
- **AND** write the 12 principles to disk
- **AND** upload to Cognee

#### Scenario: Second run is a no-op

- **WHEN** the cache file already exists for the current sha256
- **THEN** the App SHALL skip the extraction
- **AND** return the cached 12 principles in O(1)

#### Scenario: PDF change triggers re-extraction

- **WHEN** the source PDF's sha256 changes (new file uploaded)
- **THEN** the App SHALL detect the new sha256
- **AND** call `ExtractPedagogyPrinciples` again
- **AND** write the new 12 principles to a versioned cache file

### Requirement: `orchestration/defs/3_model_lifecycle/pedagogy_overlay.py` SHALL define 6 overlay assets

The module SHALL expose 6 Dagster assets (one per priority subject):
`pedagogy_overlay_cs`, `pedagogy_overlay_maths`, `pedagogy_overlay_english`, `pedagogy_overlay_gaeilge`, `pedagogy_overlay_chemistry`, `pedagogy_overlay_geography`.

Each asset SHALL:
- Depend on the corresponding `uk_ncce_learning_graphs` asset (from Change A)
- Call `ApplyPedagogyPrinciples` with the cached pedagogy principles
- Materialise the `AnnotatedLearningGraph` to Firestore `annotatedLearningGraphs/{graph_id}` + the local SQLite

#### Scenario: All 6 assets materialize successfully

- **WHEN** `dg launch --assets pedagogy_overlay_cs` is run
- **THEN** the asset SHALL emit a non-empty `AnnotatedLearningGraph`
- **AND** the corresponding Firestore document SHALL be created
- **AND** the SQLite row SHALL be inserted

### Requirement: The Pedagogy overlay tab in the Gradio studio SHALL render the coloured graph

The `gemini_hackathon_gradio/an_learning_graph/pedagogy_tab.py` SHALL
render the `AnnotatedLearningGraph` as an SVG where:

- Each cell is coloured by the dominant pedagogy principle
- Hovering over a cell shows the principle name + summary + how_to_apply
- A filter dropdown lets the user show only cells using a specific principle (e.g. "show only PRIMM cells")

#### Scenario: Filter shows only matching cells

- **WHEN** the user picks "PRIMM" from the filter dropdown
- **THEN** cells tagged with `"PRIMM"` SHALL be fully visible
- **AND** cells not tagged SHALL be greyed out
- **AND** the count of visible cells SHALL match the filter