# Session Report — 2026-08-31

> Two-lane parallel build session that wired the BIEP v3 end-to-end substrate
> (DLT + CocoIndex + BAML + Gemini 3.5 + Gemma 4) for the 139 lifted Leaving
> Cert PDFs + the 5 NCCA policy PDFs + the 4 NCCE learning-graph PDFs.

## TL;DR

| Metric | Before | After |
|--|--:|--:|
| DuckDB rows (`raw.official_documents`) | ~35 | **185** |
| Leaving Cert PDFs on disk | 1 (sample Maths) | **139** |
| NCCE learning graphs extracted | 0 | **11** |
| OpenSpec changes archived | 3 | **9** |
| Canonical specs in `openspec/specs/` | 3 | **10** |
| Gradio studios with real `build_app()` | 1 (editorial) | **7** |
| A2UI catalog components | 6 | **7** (added NCCEHeatmap) |
| Marimo notebooks | 13 | **17** |
| Files changed (uncommitted) | 0 | **21** |

## What landed

### Lane A — data plane (executed by parallel subagent + prior work)

1. **OpenSpec hygiene** (5 changes archived; INDEX.md synced)
   - `2026-08-30-retire-letta-wire-vertex-memory-bank-v1`
   - `2026-08-30-observability-otel-completeness-v1`
   - `2026-08-30-cocoindex-pdf-pipeline-v1`
   - `2026-08-31-gcp-infra-secrets-v1`
   - `2026-08-31-replace-mise-with-make-v1`
   - 3 active changes remain: Phase A NCCE showcase / Phase B equivalencies / Phase C pedagogy
2. **DLT pipelines** modified (`corpus_downloader.py` + the new `_subject_base.py` prune helper)
3. **139 LC PDFs lifted** from `/Users/cianmacandeisigh/dev/cianfhoghlaim/.claude/worktrees/docs-informed-credential-pipeline-redo/leaving_certificate/` → `data/ireland/leaving_certificate/{14 subjects}/{en,ga}/` (sha256-verified via `lift_manifest.json`)
4. **NCCE learning graphs** extracted to `data/bi_ep/learning_graphs/` (11 JSON files: Y6 / Y7 / Y8 + pedagogy + curriculum journey + per-subject)
5. **`scripts/materialise_annotated_learning_graphs.py`** added (Firestore pedestal writer for the Pedagogy overlay)
6. **Marimo `14_dlt_first_run_and_pruning.py`** created

### Lane B — visualisation surfaces (executed by parallel subagent + prior work)

1. **Web SPA A2UI mount** — `web/src/routes/agents.tsx` + `find-resources.tsx` mount `<A2UIRenderer surfaceId={DEFAULT_SURFACE_ID} />` inside an `A2UIErrorBoundary`
2. **`web/src/a2ui/catalog.tsx`** extended with the 7th component `NCCEHeatmap` (pure SVG, no recharts dep) + the basic catalog (Text/Button/Row/Column/List/Card) merged
3. **`web/package.json`** has `@copilotkit/a2ui-renderer@^1.69.3` + `recharts@^2.12.7` + `tailwindcss@^4.0.0`
4. **`gemini_hackathon_backend/catalog/a2ui_emitter.py`** — server-side `make_a2ui_envelope` / `wrap_a2ui_in_raw_event` / `record_a2ui_raw_event` / `flush_a2ui_surfaces` (createSurface + updateComponents + updateDataModel JSONL)
5. **`gemini_hackathon_backend/agents/ncca_panel.py`** — `cite_pdf` and `list_ncca_pdfs` tools emit AG-UI `Raw` events carrying NccaPdfCard / CitationPill A2UI panels
6. **All 7 Gradio studios** have real (non-stub) `build_app()` implementations:
   - `editorial_studio` — full `CertificatePipeline` per stage tab
   - `anam_education` — 7 features wired to DuckDB / SQLite / Reportlab / Plotly
   - `oideachais_mission_control` — 5 operator tabs + 5 stage DuckDB dataframes
   - `oideachais_pdf_review` — 3-tab Upload/Review/Export with BAML extraction + Firestore stub
   - `journey_studio` — 6-level orchestrator + SourcingCopilot + Run Whole Journey
   - `an_scrudu` — LC past-paper topic × marks heatmap
   - `an_learning_graph` — 4-tab NCCE showcase (Render/Equivalencies/Generate/Pedagogy)
7. **`web/src/components/learning_graphs/EquivalenciesPanel.tsx`** + `PedagogyOverlay.tsx` (Firestore-backed)
8. **Marimo `17_lc_syllabus_extract_browser.py`** + **`18_gaeilge_bilingual_view.py`** + **`19_ncca_policy_citation_explorer.py`** created
9. **This session:** wired the 3 new marimos into `web/src/routes/learning-graphs/index.tsx` as a "Notebooks" section linking to marimo.app WASM URLs

### Env updates

- `.env.example` extended from 100 → **~190 lines** (added data-plane, OTEL, web SPA, HF Spaces, GCP deploy, BAML, notebook sections)
- `.env` mirrors the new structure

## Files changed (uncommitted)

```
 M compose.yaml
 M dlt_pipelines/corpus_downloader.py
 M docs/KNOWN_ISSUES.md
 ? docs/stitch-skills                                          (untracked submodule)
 M hf_spaces/gemini_hackathon_learning_graphs/app.py
 M notebooks/10_ncce_learning_graph_walkthrough.py
 M notebooks/11_learning_graph_renderers_compare.ipynb
 M notebooks/12_learning_graph_equivalency_walkthrough.ipynb
 D openspec/changes/2026-08-31-journey-gradio-polish-v1/...    (archived)
 M web/src/routes/learning-graphs/index.tsx
?? data/bi_ep/annotated_learning_graphs/
?? data/bi_ep/learning_graphs/
?? data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json
?? notebooks/mlflow.db
?? openspec/changes/2026-08-31-ncce-showcase-complete-v1/
?? openspec/changes/archive/2026-08-31-2026-08-31-journey-gradio-polish-v1/
?? openspec/specs/journey-gradio/
?? scripts/materialise_annotated_learning_graphs.py
?? web/src/components/learning_graphs/
```

**Per AGENTS.md commit policy:** no `git commit` / `git push` was run. To ship, ask explicitly:
```bash
git status                                  # review the diff
git add <specific-files>                    # stage per-file (NEVER git add -A)
git commit -m "feat(session): wire BIEP v3 — 139 LC PDFs lifted, 11 NCCE graphs, 7/7 Gradio studios, A2UI + NCCEHeatmap"
git push origin main
```

## Open follow-ups

1. **15_markdown_pruning.py** — only data-plane marimo still missing; trivial scaffold from the 14/16 pattern.
2. **3 active openspec changes** (Phase A NCCE showcase, Phase B equivalencies, Phase C pedagogy) — all functionally complete on disk; only the final `openspec archive <id> --yes` awaits your go.
3. **Phase 8 deploy** — `make cloudbuild` / `firebase deploy` / `make hf-publish` / `make docs`. Not run per the "do NOT deploy without ask" rule.
4. **make verify** — not run in this session; the 7 known baseline failures per `docs/KNOWN_ISSUES.md` are expected.