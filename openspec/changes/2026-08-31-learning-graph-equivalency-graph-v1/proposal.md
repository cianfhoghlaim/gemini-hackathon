# 2026-08-31-learning-graph-equivalency-graph-v1

> **The 2nd change of the 2026-08-31 batch.** Extends the BIEP
> cross-jurisdiction equivalency graph from **linear topics** (the
> existing `ExtractEquivalencies` in `baml_extracts/extract_equivalency.baml`)
> to **cell-level** equivalencies: for every cell in every learning
> graph, build a pointer to the equivalent cell(s) in the 7 other BI
> jurisdictions.

## Why

The previous openspec change (`2026-08-31-uk-ncce-learning-graph-showcase-v1`)
ships the **structured learning graphs** — row × column grids with
prerequisite arrows. But those grids are **per-jurisdiction**: the
NCCE Y8 Python learning graph and the AQA GCSE Computer Science
specification both cover "binary search" but they live in completely
different shapes.

Without an equivalency layer, the BIEP has 6-jurisdiction × 6-subject
isolated graphs. With this change, every cell in every graph has a
pointer to its equivalents in the 7 other jurisdictions — turning
the 36 isolated graphs into **1 cross-walked graph**.

This is the natural extension of the existing
`baml_extracts/extract_equivalency.baml` `ExtractEquivalencies`
function (which handles linear topics) into the cell-level case.

## What changes

### Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-learning-graph-equivalency-graph-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/{learning-graph-equivalency,orchestration-equivalency-graph}/spec.md` (2 spec deltas)
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-learning-graph-equivalency-graph-v1 --strict` passes

### Phase 1 — BAML extraction contract (cell-level)

- **Extend `baml_extracts/extract_equivalency.baml`** with `ExtractCellEquivalencies`:
  - Input: `source_cell: LearningGraphCell`, `source_jurisdiction: Jurisdiction`, `target_jurisdictions: Jurisdiction[]`
  - Output: `map<Jurisdiction, CellEquivalent>`
  - `CellEquivalent` class: `(cell_id, jurisdiction, subject, year_level, confidence, notes)`
- **New `baml_extracts/learning_graph_crossref.baml`** — `LearningGraphCrossReference` class:
  - `(source_graph_id, target_graph_id, jurisdiction_pair, cell_edges: CellEquivalent[], overall_confidence, generated_at)`

### Phase 2 — Dagster asset group

- **Extend `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graph_equivalencies.py`** — one asset per (jurisdiction × subject) tuple = 8 × 6 = 48 cells worth of equivalency edges (where jurisdiction ∈ {ENGLAND, WALES, NI, IRELAND, SCOTLAND, JERSEY, GUERNSEY, ISLE_OF_MAN} and subject ∈ {computer_science, mathematics, english, gaeilge, chemistry, geography})
- **New `orchestration/defs/3_model_lifecycle/learning_graph_equivalency_graph.py`** — Dagster asset that builds the cross-walk graph in:
  - Firestore `prerequisiteEdges/{edge_id}` collection
  - FalkorDB `:CellEquivalentEdge` mirror (when FalkorDB is available — Phase 8 dev-deploy path)

### Phase 3 — Activate the Equivalencies tab in the Gradio studio

- **Extend `gemini_hackathon_gradio/an_learning_graph/equivalencies_tab.py`** — replace the stub from Change A with the real implementation:
  - Pick a cell → show the equivalent cells in the 7 other jurisdictions
  - Visualise the cross-walk as a Sankey-style diagram (Plotly)

### Phase 4 — Notebook walkthrough

- **New `notebooks/12_learning_graph_equivalency_walkthrough.ipynb`** — marimo walkthrough of the cross-walk from a single NCCE Y8 Python cell to its equivalents in NCCA LC CS + AQA GCSE CS + Edexcel GCSE CS + WJEC GCSE CS + CCEA GCSE CS

## Acceptance

- `baml_extracts/extract_equivalency.baml` defines `ExtractCellEquivalencies` + `CellEquivalent`
- `baml_extracts/learning_graph_crossref.baml` defines `LearningGraphCrossReference`
- `baml-cli generate && baml-cli test` passes for both new functions
- `mise run dagster:list-assets | grep learning_graph_equivalency` shows 48 assets + the cross-walk graph asset
- The Equivalencies tab in the Gradio studio renders 7 equivalent cells for a single source cell
- Firestore `prerequisiteEdges/{edge_id}` collection has ≥ 1 document per (jurisdiction × subject) pair = ≥ 48 documents
- `notebooks/12_*.ipynb` runs without error
- `openspec validate 2026-08-31-learning-graph-equivalency-graph-v1 --strict` passes
- `mise run lint && mise run py:typecheck && mise run turbo typecheck` green

## Dependencies

- **Blocked by:** `2026-08-31-uk-ncce-learning-graph-showcase-v1` (the structured learning graphs must exist before cell-level equivalencies can be computed).
- **Unblocks:** nothing (this is the final cross-jurisdiction layer).
- **Cross-repo:** the upstream cianfhoghlaim `baml_extracts/extract_equivalency.baml` is unchanged.

## Compatibility

- **No code changes required** for callers — `ExtractCellEquivalencies` is additive.
- The new Firestore collection (`prerequisiteEdges`) is created with read-public / write-admin rules per the new `firestore.rules` from Change A.
- The new Dagster assets slot into the existing 5-layer `orchestration/defs/` tree without breaking changes.