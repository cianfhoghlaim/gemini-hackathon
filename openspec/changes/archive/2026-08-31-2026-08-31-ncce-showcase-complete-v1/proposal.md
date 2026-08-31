# 2026-08-31-ncce-showcase-complete-v1

> **Phase 5 of the 2026-08-31 gemini_hackathon polish plan.** Completes
> the NCCE learning-graph showcase: real React components for the
> Equivalencies + Pedagogy overlay tabs, the 5th PDF (or a documented
> placeholder), the annotated_learning_graphs materialisation, the HF
> Space Pedagogy tab, and the 4 NCCE notebooks verified end-to-end.

## Why

Phases 0–4 of the polish plan wired the 6-tick foundation:

- Phase 0 (`603637c` + `d7d0f3e`) — `uv sync --all-extras` + the 8-tick verify gate
- Phase 1 (`d1ef175`) — local data plane (DLT → DuckDB → CocoIndex → LanceDB → BAML)
- Phase 2 (`57fe477`) — GCP data plane (BigQuery + Vertex AI Vector Search + GCS)
- Phase 3 (`f0f0fd4`) — GCP infra (Terraform v2 + Secret Manager + Stitch + scope-creep)
- Phase 4 (`26bcb999`) — Journey + Gradio polish (4 studios + sourcing dedupe + copilot tests)

By the end of Phase 4 the **5 NCCE PDFs are lifted** (4 verbatim + 1
placeholder), the **BAML contract is in place** (8 classes + 9
functions in `baml_extracts/learning_graph.baml`), the **11 Dagster
assets are registered**, the **4-tab Gradio studio** ships
(`an_learning_graph`), the **HF Space** ships, and the **React
landing page** embeds the HF Space via iframe.

But **Phase 4 left 5 stub gaps** that this change closes:

1. `web/src/routes/learning-graphs/index.tsx:75,83` mark the
   Equivalencies + Pedagogy overlay tabs as `<em>stub</em>`. The React
   page renders an iframe but does not exercise the underlying
   Firestore collections.
2. `data/bi_ep/syllabi_raw/uk_ncce/curriculum/curriculum_journey_full_2024_2025.placeholder.json`
   remains a placeholder JSON; the 5th PDF download is still deferred.
3. `data/bi_ep/annotated_learning_graphs/` doesn't exist. The
   `pedagogy_overlay` Dagster asset materialises this directory but
   has not been run end-to-end.
4. `hf_spaces/gemini_hackathon_learning_graphs/app.py` falls back to
   a `gr.Markdown` placeholder when the `gemini_hackathon_gradio`
   package is unavailable — the Pedagogy tab therefore has no real
   implementation in the public Space.
5. Notebooks 10–13 (the 4 NCCE walkthroughs) have not been
   end-to-end-verified; their import paths may have drifted from the
   canonical surface.

Without this change the showcase is **structurally complete but
operationally unproven** — the React page has dead stub text, the
materialised overlay cache is missing, and the HF Space has a
placeholder fallback that masks real Pedagogy behaviour.

## What changes

### Phase 5.1 — NCCE curriculum journey PDF (or documented placeholder)

- **Attempt** to fetch the real NCCE Curriculum Journey PDF from the
  S3 URL in `data/bi_ep/syllabi_raw/uk_ncce/curriculum/curriculum_journey_full_2024_2025.placeholder.json`
- **If successful**: replace the placeholder with the real PDF and
  update `INDEX.yaml` sha256 + the `bytes` field.
- **If unsuccessful**: keep the placeholder and document the failure
  in `KNOWN_ISSUES.md`.

### Phase 5.2 — Annotated learning graphs materialisation

- **Run** `python -m cocoindex_flows.uk_ncce.pedagogy_cache` to
  populate `data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json`.
- **Invoke** the 6 `pedagogy_overlay_*` Dagster assets to populate
  `data/bi_ep/learning_graphs/uk_ncce_{cs,maths,english,gaeilge,chemistry,geography}_extracted_graph.json`
  + the SQLite mirror.
- **Materialise** the annotated graphs to `data/bi_ep/annotated_learning_graphs/<subject>.json`
  via the `pedagogy_overlay` module's helper.

### Phase 5.3 — React learning-graphs route

- **New `web/src/components/learning_graphs/EquivalenciesPanel.tsx`** —
  subscribes to the Firestore `cellEquivalents` collection (jurisdiction
  = `UK_NCCE`, limit 50) and renders a list of `CellEquivalent`
  records showing `(sourceCell, targetCell, targetJurisdiction,
  confidence)`.
- **New `web/src/components/learning_graphs/PedagogyOverlay.tsx`** —
  subscribes to the Firestore `annotatedLearningGraphs` collection
  (graphId matches the route's selected subject) and renders the 12
  NCCE pedagogy principles as coloured badges.
- **Update `web/src/routes/learning-graphs/index.tsx`** to import the
  two components and replace the `<em>stub</em>` text.

### Phase 5.4 — HF Space Pedagogy tab

- **Verify** `hf_spaces/gemini_hackathon_learning_graphs/app.py` has
  all 4 tabs (Render, Equivalencies, Generate, Pedagogy).
- **Wire** the Pedagogy tab to read
  `data/bi_ep/annotated_learning_graphs/<subject>.json` from the
  public HF Space cache, or fall back to the placeholder Markdown
  when the cache is cold.

### Phase 5.5 — Notebooks 10-13 end-to-end

- **Run** notebooks 10–13 via `jupyter nbconvert --execute --inplace`
  to verify their import paths are still valid.
- **Fix** any broken imports (e.g. `dlt_pipelines.uk_ncce_learning_graphs.run`).
- **Document** any persistent gaps (e.g. a notebook that needs the
  Curriculum Journey PDF before it can render).

### Phase 5.6 — Verify the showcase runs end-to-end

- **Run** `make ncce-extract && make ncce-visualise` and verify they
  produce output.
- **Document** any failures in `KNOWN_ISSUES.md`.

## Acceptance

- `data/bi_ep/syllabi_raw/uk_ncce/curriculum/` has 4 PDFs + 1
  placeholder (or 5 PDFs if the S3 download succeeded).
- `data/bi_ep/annotated_learning_graphs/<subject>.json` exists for
  ≥ 4 priority subjects.
- `web/src/routes/learning-graphs/index.tsx` has 0 `<em>stub</em>` lines.
- `web/src/components/learning_graphs/EquivalenciesPanel.tsx` and
  `PedagogyOverlay.tsx` exist and export default components.
- `hf_spaces/gemini_hackathon_learning_graphs/app.py` has 4 tabs.
- Notebooks 10–13 import without `ModuleNotFoundError`.
- `KNOWN_ISSUES.md` is updated with any persistent gaps.
- `make verify` is still 6/8 [OK] (no regression).
- `uv run pytest tests/ -v` passes ≥ 412 tests (≥ 4 new tests).
- `openspec validate 2026-08-31-ncce-showcase-complete-v1 --strict` passes.

## Dependencies

- **Blocked by:** Phases 0–4 (committed).
- **Unblocks:** nothing (this is the final polish phase of the
  2026-08-31 batch).
- **Cross-repo:** none.

## Compatibility

- **No code changes required** for callers — Phase 5 is purely
  surface-level (React components + asset materialisation + notebook
  verification).
- The new React components are additive; they slot into the existing
  `web/src/routes/learning-graphs/` route without breaking the
  iframe embedding.
- The new annotated_learning_graphs JSON files are written to a
  sibling of the existing `learning_graphs/` directory; downstream
  consumers that look at `learning_graphs/` are unaffected.
