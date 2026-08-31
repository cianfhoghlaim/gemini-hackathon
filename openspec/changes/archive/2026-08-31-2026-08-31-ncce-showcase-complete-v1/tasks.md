# 2026-08-31-ncce-showcase-complete-v1 — tasks

Phase 5 of the 2026-08-31 polish plan. The 6 sub-tasks for completing the NCCE learning-graph showcase.

## T0 — OpenSpec change folder

- [x] T0.1: `openspec/changes/2026-08-31-ncce-showcase-complete-v1/proposal.md` written
- [x] T0.2: `openspec/changes/2026-08-31-ncce-showcase-complete-v1/specs/ncce-showcase/spec.md` written
- [x] T0.3: `openspec/changes/2026-08-31-ncce-showcase-complete-v1/tasks.md` written (this file)
- [x] T0.4: `openspec validate 2026-08-31-ncce-showcase-complete-v1 --strict` passes

## T1 — Sub-task 5.1: NCCE curriculum journey PDF (or placeholder documentation)

- [ ] T1.1: Attempt to fetch the Curriculum Journey PDF from the S3 URL.
- [ ] T1.2: If successful: replace placeholder JSON with real PDF + update `INDEX.yaml` sha256.
- [ ] T1.3: If unsuccessful: document the failure in `KNOWN_ISSUES.md`.

## T2 — Sub-task 5.2: Materialise annotated learning graphs

- [ ] T2.1: Run `python -m cocoindex_flows.uk_ncce.pedagogy_cache` to populate the disk cache.
- [ ] T2.2: Invoke the 6 `pedagogy_overlay_*` Dagster assets to materialise the SQLite mirror.
- [ ] T2.3: Materialise the annotated graphs to `data/bi_ep/annotated_learning_graphs/<subject>.json`.

## T3 — Sub-task 5.3: React learning-graphs route

- [ ] T3.1: Write `web/src/components/learning_graphs/EquivalenciesPanel.tsx`.
- [ ] T3.2: Write `web/src/components/learning_graphs/PedagogyOverlay.tsx`.
- [ ] T3.3: Update `web/src/routes/learning-graphs/index.tsx` to import + use the new components.

## T4 — Sub-task 5.4: HF Space Pedagogy tab

- [ ] T4.1: Verify `hf_spaces/gemini_hackathon_learning_graphs/app.py` has 4 tabs.
- [ ] T4.2: Wire the Pedagogy tab to read `data/bi_ep/annotated_learning_graphs/`.

## T5 — Sub-task 5.5: Notebooks 10-13 end-to-end

- [ ] T5.1: Run `jupyter nbconvert --execute --inplace notebooks/10_ncce_learning_graph_walkthrough.py`.
- [ ] T5.2: Run `jupyter nbconvert --execute --inplace notebooks/11_learning_graph_renderers_compare.ipynb`.
- [ ] T5.3: Run `jupyter nbconvert --execute --inplace notebooks/12_learning_graph_equivalency_walkthrough.ipynb`.
- [ ] T5.4: Run `jupyter nbconvert --execute --inplace notebooks/13_pedagogy_overlay_walkthrough.ipynb`.
- [ ] T5.5: Fix any broken import paths.

## T6 — Sub-task 5.6: Verify the showcase end-to-end

- [ ] T6.1: Run `make ncce-extract` and verify it produces output.
- [ ] T6.2: Run `make ncce-visualise` and verify it produces output.
- [ ] T6.3: Document any failures in `KNOWN_ISSUES.md`.

## T7 — New tests

- [ ] T7.1: `tests/cocoindex/test_ncce_learning_graphs.py` — verify 5 PDFs + 6 annotated JSONs.
- [ ] T7.2: `tests/baml/test_learning_graph_extract.py` — verify 16 functions generate code.
- [ ] T7.3: `tests/orchestration/test_pedagogy_overlay_asset.py` — verify Dagster asset materialises.
- [ ] T7.4: `tests/test_ncce_showcase_e2e.py` — verify `make ncce-extract && make ncce-visualise` runs.

## T8 — Quality gates

- [ ] T8.1: `uv run pytest tests/ -v` passes ≥ 412 tests.
- [ ] T8.2: `bash scripts/verify.sh` is 6/8 [OK] (no regression).
- [ ] T8.3: `npx tsc --noEmit` is 0 errors (web/ TS compiles).

## T9 — Commit + archive

- [ ] T9.1: Commit Phase 5 with `feat(phase-5): complete NCCE showcase — 5th PDF + React route + HF Space + pedagogy materialisation`.
- [ ] T9.2: `openspec archive 2026-08-31-ncce-showcase-complete-v1 --yes`.
