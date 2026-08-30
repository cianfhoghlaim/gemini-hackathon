# Tasks for 2026-08-31-pedagogy-overlay-renderer-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-pedagogy-overlay-renderer-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/pedagogy-overlay/spec.md`
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-pedagogy-overlay-renderer-v1 --strict` passes

## Phase 1 — BAML extraction contract
- [ ] T1.1: `baml_extracts/learning_graph.baml` — add `AnnotatedLearningGraph` class
- [ ] T1.2: `baml_extracts/learning_graph.baml` — add `ApplyPedagogyPrinciples` function
- [ ] T1.3: `uv run baml-cli generate`
- [ ] T1.4: `uv run baml-cli test baml_extracts/learning_graph.baml` passes for `ApplyPedagogyPrinciples`
- [ ] T1.5: commit + push Phase 1

## Phase 2 — CocoIndex disk cache + Cognee dataset
- [ ] T2.1: `cocoindex_flows/uk_ncce/pedagogy_cache.py` — `@coco.fn(memo=True)` App
- [ ] T2.2: `python -m cocoindex_flows.uk_ncce.pedagogy_cache` writes 12 principles to disk + uploads to Cognee
- [ ] T2.3: Re-running the cache is a no-op (sha256 hit)
- [ ] T2.4: Changing the PDF triggers a re-extraction (CI gate)
- [ ] T2.5: commit + push Phase 2

## Phase 3 — Dagster asset
- [ ] T3.1: `orchestration/defs/3_model_lifecycle/pedagogy_overlay.py` — 6 assets (1 per priority subject)
- [ ] T3.2: `dg list assets | grep pedagogy_overlay` shows 6 assets
- [ ] T3.3: commit + push Phase 3

## Phase 4 — Activate the Pedagogy overlay tab
- [ ] T4.1: `gemini_hackathon_gradio/an_learning_graph/pedagogy_tab.py` — replace stub with real implementation
- [ ] T4.2: Pick a learning graph → render SVG with cells coloured by principle
- [ ] T4.3: Hover over a cell → show principle name + summary + how_to_apply
- [ ] T4.4: Filter by principle (e.g. "show only PRIMM cells")
- [ ] T4.5: commit + push Phase 4

## Phase 5 — Notebook walkthrough
- [ ] T5.1: `notebooks/13_pedagogy_overlay_walkthrough.ipynb` — marimo walkthrough
- [ ] T5.2: Notebook runs without error end-to-end
- [ ] T5.3: commit + push Phase 5

## Phase 6 — Final validation
- [ ] T6.1: Firestore `annotatedLearningGraphs/{graph_id}` collection has ≥ 6 documents (1 per priority subject)
- [ ] T6.2: Cognee dataset `gh_cognee_pedagogy_dataset` is populated with 12 principles
- [ ] T6.3: `mise run lint && mise run py:typecheck && mise run turbo typecheck` green
- [ ] T6.4: `pytest gemini_hackathon_backend/tests/` passes (no regressions)
- [ ] T6.5: `openspec validate 2026-08-31-pedagogy-overlay-renderer-v1 --strict` passes
- [ ] T6.6: archive the OpenSpec change after deploy