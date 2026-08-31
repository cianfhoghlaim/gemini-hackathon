# 2026-08-31-journey-gradio-polish-v1

> **Phase 4 of the gemini_hackathon polish plan.** Wires up the 4
> remaining Gradio studios + reconciles the Journey sourcing duplication
> + adds tests for the SourcingCopilot. Phase 0-3 (committed in
> `603637c` + `d7d0f3e` + `d1ef175` + `57fe477` + `f0f0fd4`) shipped the
> infrastructure (GCP + data plane + model registry); Phase 4 surfaces
> the work to judges + workshop hosts.

## Why

After Phase 0-3 the platform's substrate is solid:

- The 7-stage certificate pipeline (`gemini_hackathon/certificate/pipeline.py`) runs end-to-end against the 5 NCCA policy PDFs.
- The BAML extractor (`gemini_hackathon/syllabus/baml_extractor.py`) extracts the 8 LC6 + per-subject syllabi in offline-test mode.
- The 14-subject wiring registry (`gemini_hackathon/agents/registry.py`) covers 8 NCCA + 6 NCCA-adjacent subjects.
- The Journey 6 levels (0-5) are wired + tested in `journey/tests/`.

But four Gradio studios still display Markdown stubs ("Wired in W12.")
in 4 of their tabs, and the Journey sourcing module is duplicated
between `journey/sourcing/sourcing/` (Phase 3 subagent's scope creep)
and the canonical `gemini_hackathon/journey/sourcing/`.

This change:

1. Wires each Markdown-stub tab in `editorial_studio`, `anam_education`,
   `oideachais_mission_control`, and `oideachais_pdf_review` to a real
   operator that calls into the canonical pipeline.
2. Reconciles the Journey sourcing duplication (the inner tree is
   canonical; the outer duplicate is deleted).
3. Adds `journey/sourcing_copilot_tests/` so the SourcingCopilot's 7
   tools + the agent's tool-calling loop are exercised in CI.
4. Adds `tests/gradio/test_*.py` for each of the 4 polished studios so
   the `build_app()` smoke test runs in CI.

## What changes

### Phase 4.1 — editorial_studio polish

`gemini_hackathon_gradio/editorial_studio/app.py` had 4 Markdown-stub
tabs ("Wired in W12.") on the Aistear / Bunscoil / MeanScoil / Ollscoil
tabs. Each tab now wires to the 7-stage `CertificatePipeline` in
`gemini_hackathon/certificate/pipeline.py:87` with a `learner_id` text
input + a `subject` dropdown (sourced from `SUBJECT_WIRING_REGISTRY` in
`gemini_hackathon/agents/registry.py:94`) + an "Extract certificate"
button. The result renders as Markdown (the certificate summary) + JSON
(the full `CertificateRecord`).

### Phase 4.2 — anam_education polish

`gemini_hackathon_gradio/anam_education/app.py` had 7 tabs, of which
some were wired to data paths + Plotly + reportlab. We add a "Run BAML
extraction" button on each tab that calls `BAMLSyllabusExtractor.extract(subject=..., language="en")`
(setting `BAML_TEST_MODE=true` so the offline stub runs in the workshop
demo). The result renders as `gr.JSON()`.

### Phase 4.3 — oideachais_mission_control polish

`gemini_hackathon_gradio/oideachais_mission_control/app.py` had 5 tabs
already wired to DuckDB `raw.official_documents`. We add a "Refresh"
button on each tab + a 6th "Models" tab that renders the
`MODEL_REGISTRY._entries` as a `gr.Dataframe()` + a 7th "Observability"
tab that surfaces the last 5 structlog events.

### Phase 4.4 — oideachais_pdf_review polish

`gemini_hackathon_gradio/oideachais_pdf_review/app.py` had 1 Markdown
stub + the `_suggestion_model()` / `_explanation_model()` lookup but no
`@spaces.GPU` handler. We register a regular function (the
`@spaces.GPU` decorator is conditional — when `SPACE_ID` is set) that
calls the BAML extractor. We add a 3-tab layout (Upload / Review /
Export).

### Phase 4.5 — Journey sourcing dedupe + copilot tests

The `journey/sourcing/sourcing/` outer duplicate (created by Phase 3
scope creep) is deleted. The canonical
`gemini_hackathon/journey/sourcing/` (with the `_shared_fs()` singleton
pattern) is preserved as-is — it already has the better implementation.

A new `journey/sourcing_copilot_tests/` package is created with
`test_tools.py` (covering the 7 canonical tools) + `test_agent.py`
(covering the `build_copilot_agent()` factory's tool-binding loop).

### Phase 4.6 — Gradio studio verification + tests

`tests/gradio/test_editorial_studio.py` + `test_anam_education.py` +
`test_oideachais_mission_control.py` + `test_oideachais_pdf_review.py`
smoke-test each studio's `build_app()` returns a non-None `gr.Blocks`
and that each tab renders Markdown (not raw Python errors).

## Acceptance

- `grep -rE "#REPLACE-[0-9]" gemini_hackathon/ --include="*.py"` returns 0 hits (Phase 3 baseline)
- `grep -rE "Wired in W12" gemini_hackathon_gradio/` returns 0 hits (was 6)
- `test -d journey/sourcing/sourcing` returns false (was true)
- `journey/sourcing_copilot_tests/{__init__,test_tools,test_agent}.py` exist
- `tests/gradio/test_{editorial_studio,anam_education,oideachais_mission_control,oideachais_pdf_review}.py` exist
- `uv run pytest tests/ -v` passes 386+ tests (was 381)
- `bash scripts/verify.sh` stays at 6/8 [OK] (ticks 3+4 pre-existing baseline)
- `openspec validate 2026-08-31-journey-gradio-polish-v1 --strict` passes
- `for studio in editorial_studio anam_education oideachais_mission_control oideachais_pdf_review; do uv run python -c "from gemini_hackathon_gradio import $studio; ${studio}.build_app()"` succeeds for all 4

## Dependencies

- **Blocked by:** Phases 0-3 (`603637c` + `d7d0f3e` + `d1ef175` +
  `57fe477` + `f0f0fd4`). All on main.
- **Unblocks:** the Phase 5 work (`docs/GRADIO.md` refresh +
  `hf_spaces/` + `web/`).
- **Cross-repo:** no upstream impact. The duplicate
  `journey/sourcing/sourcing/` was Phase 3 scope creep — it never
  shipped to a remote.

## Compatibility

- **No code changes required** for callers — the polished Gradio tabs
  are additive (new operators on existing tabs).
- The deleted `journey/sourcing/sourcing/` outer duplicate was never
  imported (no `from journey.sourcing.sourcing.X import Y` anywhere
  in the repo — confirmed via `grep`).
- The new `journey/sourcing_copilot_tests/` is a test-only package
  with no runtime dependencies.
