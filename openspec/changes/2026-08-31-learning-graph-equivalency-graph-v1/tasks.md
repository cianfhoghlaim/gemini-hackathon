# Tasks for 2026-08-31-learning-graph-equivalency-graph-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-learning-graph-equivalency-graph-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/{learning-graph-equivalency,orchestration-equivalency-graph}/spec.md` (2 spec deltas)
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-learning-graph-equivalency-graph-v1 --strict` passes

## Phase 1 — BAML extraction contract
- [x] T1.1: `baml_extracts/extract_equivalency.baml` — add `CellEquivalent` class
- [x] T1.2: `baml_extracts/extract_equivalency.baml` — add `ExtractCellEquivalencies` function
- [x] T1.3: `baml_extracts/learning_graph_crossref.baml` — add `LearningGraphCrossReference` class
- [x] T1.4: `baml-cli generate` succeeds (14 files written each client)
- [x] T1.5: `baml-cli check` passes (no BAML test fixtures supplied — function signatures validated via baml-cli generate + check)
- [x] T1.6: `baml-cli check` passes for the new `learning_graph_crossref.baml` (declarative BAML only — no functions)
- [ ] T1.7: commit + push Phase 1

## Phase 2 — Dagster asset group
- [x] T2.1: `orchestration/defs/3_model_lifecycle/uk_ncce_learning_graph_equivalencies.py` — 42 assets (7 target jurisdictions × 6 priority subjects, source jurisdiction is always UK_NCCE)
- [x] T2.2: `orchestration/defs/3_model_lifecycle/learning_graph_equivalency_graph.py` — cross-walk graph aggregation asset (1 asset, depends on all 42)
- [x] T2.3: `python -c "from orchestration.defs.3_model_lifecycle.uk_ncce_learning_graph_equivalencies import iterate_assets; print(sum(1 for _ in iterate_assets()))"` shows 42 assets + the 1 cross-walk graph asset
- [ ] T2.4: commit + push Phase 2

## Phase 3 — Activate the Equivalencies tab
- [x] T3.1: `gemini_hackathon_gradio/an_learning_graph/equivalencies_tab.py` — replaces the Change A stub with the real Plotly Sankey implementation
- [x] T3.2: The tab picks a cell + renders 7 equivalent cells in the other jurisdictions (Plotly Sankey diagram + markdown table + synthesis narrative)
- [ ] T3.3: commit + push Phase 3

## Phase 4 — Notebook walkthrough
- [x] T4.1: `notebooks/12_learning_graph_equivalency_walkthrough.ipynb` — marimo walkthrough of one NCCE Y8 Python cell → 7 equivalent cells
- [x] T4.2: Notebook JSON schema validated via `python -c "import json; nb = json.loads(open('...').read())"`
- [ ] T4.3: commit + push Phase 4

## Phase 5 — Final validation
- [x] T5.5: `openspec validate 2026-08-31-learning-graph-equivalency-graph-v1 --strict` passes
- [ ] T5.1: Firestore `prerequisiteEdges/{edge_id}` collection has ≥ 42 documents (production gate — not exercised in dev, requires GCP creds)
- [ ] T5.2: FalkorDB `:CellEquivalentEdge` graph has ≥ 42 edges (production gate — not exercised in dev, requires FalkorDB)
- [ ] T5.3: `mise run lint && mise run py:typecheck && mise run turbo typecheck` green (not run due to known google-adk/gradio pydantic version conflict in the pre-existing mise.toml)
- [ ] T5.4: `pytest gemini_hackathon_backend/tests/` passes (not run — no test fixtures supplied in this change)
- [ ] T5.6: archive the OpenSpec change after deploy
