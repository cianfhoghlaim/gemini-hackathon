# Proposal — 2026-08-31-submission-scope-realignment-v1

> **One-liner:** realign the 2026-08-31 demo submission to the **97 in-scope PDFs**
> (5 NCCA policies + 5 NCCE artefacts + 87 English LC syllabi + 1 sample) without
> rewriting the BIEP substrate or deleting the deferred jurisdictions from the code
> surface.

## Why

The All Things Agentic 2026 hackathon judges evaluate the **demo**, not the
abstract substrate. The current repo exercises the full 9-jurisdiction BIEP
orchestration, but the live demo path uses a focused 97-PDF corpus. Without
explicit documentation, reviewers can mistake "the BIEP substrate is wider than
what the demo runs on" for "the demo is incomplete". This realignment:

1. Codifies the 97-PDF in-scope corpus in `docs/SUBMISSION_SCOPE.md`
2. Surfaces a canonical DuckDB view `raw.official_documents_in_scope`
3. Preserves the 8 deferred jurisdictions on disk + in code (no deletions)
4. Adds the ADK `generate_asset` tool that emits a `NccaPdfCard` A2UI surface
   so the certificate flow is end-to-end visible at `/agents`
5. Lands the 5-step demo script (`docs/DEMO_SCRIPT.md`) + the `/compare-models`
   route + the editorial-studio BAML wire-up so the demo flow is reproducible

The substrate is preserved (DLT + CocoIndex + BAML + Google ADK + Gemma 4 +
Gemini 3.5 + A2UI + Gradio + Web SPA), the demo path is focused.

## What Changes

1. **NEW** `docs/SUBMISSION_SCOPE.md` — the canonical scope statement
2. **NEW** `docs/DEMO_SCRIPT.md` — the 5-step demo flow
3. **MODIFIED** `README.md` — adds a scope banner + a "Quick demo" section
4. **MODIFIED** `AGENTS.md` — adds the `submission-scope` skill row (2.5)
5. **MODIFIED** `docs/VIEW_AND_TEST.md` — adds a "Run the 5-step demo" pointer
6. **MODIFIED** `web/src/routes/compare-models.tsx` — NEW route for vision comparison
7. **MODIFIED** `web/src/routes/__root.tsx` — adds header "Demo" link
8. **MODIFIED** `web/src/router.tsx` — registers the new route
9. **MODIFIED** `gemini_hackathon_backend/agents/ncca_panel.py` — adds `generate_asset` tool
10. **MODIFIED** `gemini_hackathon_gradio/editorial_studio/app.py` — BAML subject lookup

No file is deleted. No jurisdiction scraper is dropped. No BAML schema is
removed. The deferred code remains in `dlt_pipelines/_base/` + `data/ireland/
leaving_certificate/_deferred_ga/` for the post-hackathon expansion pack.

## Impact

- **Demo path**: shorter, reproducible, judge-friendly (5 steps)
- **In-scope corpus**: 97 PDFs (canonical view `raw.official_documents_in_scope`)
- **Deferred**: 52 Gaeilge PDFs + 35 DuckDB rows + 8 jurisdiction scrapers
  (kept on disk + in code, deferred per the existing openspec changes)
- **ADK surface**: 4 tools now (cite_pdf, fetch_highlight, list_ncca_pdfs,
  generate_asset) — the new `generate_asset` emits a `NccaPdfCard` A2UI surface
- **Editorial studio**: BAML extraction wire-up on the 5 stage tabs (was only
  certificate rendering)

## Dependencies

- `2026-08-27-ncca-policy-corpus-as-certificate-source-v1` (closed) — the 5 NCCA PDFs
- `2026-08-27-official-lc-jc-certificate-pipeline-v1` (closed) — the cert pipeline
- `2026-08-27-fibo-image-generation-v1` (closed) — the asset-generation path
- `2026-08-31-uk-ncce-learning-graph-showcase-v1` (active) — the NCCE 5 PDFs
- `2026-08-27-defer-ni-wales-scotland-iom-v1` (deferred) — explicit ack of deferred jurisdictions
- `2026-08-27-deferred-jersey-guernsey-v1` (deferred) — explicit ack of deferred jurisdictions

## Quality gates

- `openspec validate 2026-08-31-submission-scope-realignment-v1 --strict`
- `make lint` (ruff + ruff format)
- `make typecheck` (mypy on the gemini_hackathon package)
- `cd web && bun run tsc --noEmit` (TypeScript)

## Rollback

If the demo path is judged insufficient, revert by:
1. `git revert <this-commit>`
2. The BIEP substrate (DLT + CocoIndex + BAML + ADK + Gradio + Web) is untouched
3. The deferred jurisdictions remain in code — re-enable by flipping
   `dlt_pipelines/_base/_active_jurisdictions.yaml` (future work)