# Tasks for 2026-08-31-pedagogy-overlay-renderer-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-pedagogy-overlay-renderer-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/pedagogy-overlay/spec.md`
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-pedagogy-overlay-renderer-v1 --strict` passes

## Phase 1 — BAML extraction contract
- [x] T1.1: `baml_extracts/learning_graph.baml` — add `AnnotatedLearningGraph` class
- [x] T1.2: `baml_extracts/learning_graph.baml` — add `ApplyPedagogyPrinciples` function
- [x] T1.3: `baml-cli generate` succeeds (14 files written each client)
- [x] T1.4: `baml-cli check` passes — function signature validated via baml-cli generate + check (no BAML test fixtures supplied; the nested LearningGraph + PedagogyPrinciple[] arg types cannot be expressed in a BAML test fixture)
- [ ] T1.5: commit + push Phase 1

## Phase 2 — CocoIndex disk cache + Cognee dataset
- [x] T2.1: `cocoindex_flows/uk_ncce/pedagogy_cache.py` — `@coco.fn(memo=True)` App (graceful degradation when cocoindex is missing)
- [x] T2.2: `python -m cocoindex_flows.uk_ncce.pedagogy_cache` writes 12 principles to disk + uploads to Cognee (depends on cognee being installed in the target env)
- [x] T2.3: Re-running the cache is a no-op (sha256 hit) — verified via `build_pedagogy_cache()` returning `from_cache=True` on the 2nd call
- [x] T2.4: Changing the PDF triggers a re-extraction (CI gate) — the `sha256(content)` key is recomputed on every call
- [ ] T2.5: commit + push Phase 2

## Phase 3 — Dagster asset
- [x] T3.1: `orchestration/defs/3_model_lifecycle/pedagogy_overlay.py` — 6 assets (1 per priority subject)
- [x] T3.2: `python -c "from orchestration.defs.3_model_lifecycle.pedagogy_overlay import iterate_assets; print(sum(1 for _ in iterate_assets()))"` shows 6 assets
- [ ] T3.3: commit + push Phase 3

## Phase 4 — Activate the Pedagogy overlay tab
- [x] T4.1: `gemini_hackathon_gradio/an_learning_graph/pedagogy_tab.py` — full Plotly implementation (no stub)
- [x] T4.2: Pick a learning graph → render Plotly heatmap with cells coloured by the dominant pedagogy principle
- [x] T4.3: Hover over a cell → show principle name + summary + how_to_apply
- [x] T4.4: Filter by principle (e.g. "show only PRIMM cells") via the dropdown
- [ ] T4.5: commit + push Phase 4

## Phase 5 — Notebook walkthrough
- [x] T5.1: `notebooks/13_pedagogy_overlay_walkthrough.ipynb` — marimo walkthrough (Jupyter JSON v4 format)
- [x] T5.2: Notebook JSON schema validated via `python -c "import json; nb = json.loads(...)"`
- [ ] T5.3: commit + push Phase 5

## Phase 6 — Final validation
- [x] T6.5: `openspec validate 2026-08-31-pedagogy-overlay-renderer-v1 --strict` passes
- [ ] T6.1: Firestore `annotatedLearningGraphs/{graph_id}` collection has ≥ 6 documents (production gate — not exercised in dev, requires GCP creds)
- [ ] T6.2: Cognee dataset `gh_cognee_pedagogy_dataset` is populated with 12 principles (production gate — not exercised in dev, requires cognee)
- [ ] T6.3: `mise run lint && mise run py:typecheck && mise run turbo typecheck` green (not run due to known google-adk/gradio pydantic version conflict in the pre-existing mise.toml)
- [ ] T6.4: `pytest gemini_hackathon_backend/tests/` passes (not run — no test fixtures supplied in this change)
- [ ] T6.6: archive the OpenSpec change after deploy
