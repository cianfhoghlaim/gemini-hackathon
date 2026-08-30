# Tasks for 2026-08-31-learning-graph-equivalency-graph-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-learning-graph-equivalency-graph-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/{learning-graph-equivalency,orchestration-equivalency-graph}/spec.md` (2 spec deltas)
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-learning-graph-equivalency-graph-v1 --strict` passes

## Phase 1 — BAML extraction contract
- [ ] T1.1: `baml_extracts/extract_equivalency.baml` — add `CellEquivalent` class
- [ ] T1.2: `baml_extracts/extract_equivalency.baml` — add `ExtractCellEquivalencies` function
- [ ] T1.3: `baml_extracts/learning_graph_crossref.baml` — add `LearningGraphCrossReference` class
- [ ] T1.4: `uv run baml-cli generate`
- [ ] T1.5: `uv run baml-cli test baml_extracts/extract_equivalency.baml` passes (1+ new tests)
- [ ] T1.6: `uv run baml-cli test baml_extracts/learning_graph_crossref.baml` passes
- [ ] T1.7: commit + push Phase 1

## Phase 2 — Dagster asset group
- [ ] T2.1: `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graph_equivalencies.py` — 48 assets (8 jurisdictions × 6 subjects)
- [ ] T2.2: `orchestration/defs/3_model_lifecycle/learning_graph_equivalency_graph.py` — cross-walk graph asset
- [ ] T2.3: `dg list assets | grep learning_graph_equivalency` shows 48 + 1 assets
- [ ] T2.4: commit + push Phase 2

## Phase 3 — Activate the Equivalencies tab
- [ ] T3.1: `gemini_hackathon_gradio/an_learning_graph/equivalencies_tab.py` — replace stub with real implementation (Plotly Sankey)
- [ ] T3.2: The tab picks a cell + renders 7 equivalent cells in the other jurisdictions
- [ ] T3.3: commit + push Phase 3

## Phase 4 — Notebook walkthrough
- [ ] T4.1: `notebooks/12_learning_graph_equivalency_walkthrough.ipynb` — marimo walkthrough of one NCCE Y8 Python cell → 7 equivalent cells
- [ ] T4.2: Notebook runs without error end-to-end
- [ ] T4.3: commit + push Phase 4

## Phase 5 — Final validation
- [ ] T5.1: Firestore `prerequisiteEdges/{edge_id}` collection has ≥ 48 documents (sanity-check via `firestore.collection('prerequisiteEdges').get()`)
- [ ] T5.2: FalkorDB `:CellEquivalentEdge` graph has ≥ 48 edges (when FalkorDB is available — dev path)
- [ ] T5.3: `mise run lint && mise run py:typecheck && mise run turbo typecheck` green
- [ ] T5.4: `pytest gemini_hackathon_backend/tests/` passes (no regressions)
- [ ] T5.5: `openspec validate 2026-08-31-learning-graph-equivalency-graph-v1 --strict` passes
- [ ] T5.6: archive the OpenSpec change after deploy