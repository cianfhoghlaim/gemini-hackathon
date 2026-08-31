# Tasks — 2026-08-31-submission-scope-realignment-v1

## Phase 0 — Scope the submission

- [x] Create `docs/SUBMISSION_SCOPE.md` (canonical 97-PDF scope)
- [x] Add 5-line banner to `README.md` under the title
- [x] Add row 2.5 to the priority skills table in `AGENTS.md`
- [x] Create `openspec/changes/2026-08-31-submission-scope-realignment-v1/`
  - [x] `proposal.md` (Why + What Changes + Impact + Dependencies)
  - [x] `tasks.md` (this file)
  - [x] `specs/in-scope-substrate/spec.md` (codified view + deferred pattern)
- [x] Add the new change row to `openspec/changes/INDEX.md` (active section)

## Phase 1 — Defer the 52 Gaeilge PDFs (Lane A owns the data move)

- [x] Move 52 Gaeilge LC PDFs to `data/ireland/leaving_certificate/_deferred_ga/`
- [x] Refresh `notebooks/04_corpus_inventory.py` to count the 97 in-scope PDFs

## Phase 2 — Refresh the DuckDB views (Lane A)

- [x] Drop+recreate `raw.official_documents_deferred` (35 rows)
- [x] Create the canonical `raw.official_documents_in_scope` view

## Phase 3 — Defer the 8 jurisdiction scrapers (Lane A)

- [x] Gate `dlt_pipelines/_base/jurisdiction_pipeline_base.py` behind `_active_jurisdictions.yaml`
- [x] Gate `_subject_base.py` behind the same flag
- [x] Document the toggle in `dlt_pipelines/_base/README.md`

## Phase 4 — BAML schema + ADK verification (Lane B verify-only)

- [x] Read all 8 LC subject BAML contracts in `baml_extracts_education/subjects/`
- [x] Confirm `baml_extracts_education/stages/leaving_cycle.baml` (5+3 LC6 functions)
- [x] Confirm `baml_extracts/learning_graph.baml` (8 classes + 9 functions)
- [x] Confirm `gemini_hackathon/agents/stages/leaving_certificate/__init__.py`
      14-subject specialists' `baml_functions` mapping
- [x] Print verification results to stdout (no file changes)

## Phase 5 — DiffusionGemma → certificate → A2UI showcase

- [x] Add `generate_asset` tool to `gemini_hackathon_backend/agents/ncca_panel.py`
- [x] Register `generate_asset` in the `tools = [...]` list
- [x] Update `NCCA_PANEL_INSTRUCTION` to mention the new tool
- [x] Verify `web/src/routes/agents.tsx` renders the A2UI surface (no change)

## Phase 6 — Demo script + UI wiring

- [x] Create `docs/DEMO_SCRIPT.md` (5-step demo)
- [x] Create `web/src/routes/compare-models.tsx`
- [x] Add `<Link to="/compare-models">Demo</Link>` to `web/src/routes/__root.tsx` header
- [x] Register `compare-models` in `web/src/router.tsx`
- [x] Update `docs/VIEW_AND_TEST.md` to point at the demo script
- [x] Update `README.md` "Quick demo" section
- [x] Modify `gemini_hackathon_gradio/editorial_studio/app.py`:
      add `_baml_subject_lookup` + BAML call in `_on_click`

## Phase 7 — Quality gates

- [ ] `openspec validate 2026-08-31-submission-scope-realignment-v1 --strict`
- [ ] `make lint`
- [ ] `make typecheck`
- [ ] `cd web && bun run tsc --noEmit`
- [ ] `uv run python -c "from gemini_hackathon_backend.agents.ncca_panel import generate_asset"`

## Phase 8 — Archive

- [ ] `openspec archive 2026-08-31-submission-scope-realignment-v1 --yes` (post-deploy)