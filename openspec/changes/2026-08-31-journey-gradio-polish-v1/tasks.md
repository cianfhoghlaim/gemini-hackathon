# Tasks for 2026-08-31-journey-gradio-polish-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-journey-gradio-polish-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/journey-gradio/spec.md` written
- [x] T0.3: `openspec/changes/.../tasks.md` (this file)
- [x] T0.4: `openspec validate 2026-08-31-journey-gradio-polish-v1 --strict` passes

## Phase 4.1 — editorial_studio polish
- [x] T4.1.1: `gemini_hackathon_gradio/editorial_studio/app.py` — replace 4 Markdown stubs on Aistear / Bunscoil / MeanScoil / Ollscoil tabs with real `CertificatePipeline.run()` operators (learner_id + subject dropdown + "Extract certificate" button)
- [x] T4.1.2: Add `subject_dropdown` sourced from `SUBJECT_WIRING_REGISTRY` (`gemini_hackathon/agents/registry.py:94`)
- [x] T4.1.3: Each tab's operator returns `(markdown_summary, json_record)` rendered via `gr.Markdown()` + `gr.JSON()`
- [x] T4.1.4: Remove the "Wired in W12." markers

## Phase 4.2 — anam_education polish
- [x] T4.2.1: `gemini_hackathon_gradio/anam_education/app.py` — add a "Run BAML extraction" button on each of the 7 tabs (Curriculum Map / Chemistry Visual / Exit Card / Gaelscribhneoir / Bilingual EN/GA / Certificate / Skill Progression)
- [x] T4.2.2: Each button calls `BAMLSyllabusExtractor.extract(subject=..., language="en")` with `BAML_TEST_MODE=true` for offline demo
- [x] T4.2.3: Render the `ExtractedSyllabus` as `gr.JSON()`

## Phase 4.3 — oideachais_mission_control polish
- [x] T4.3.1: `gemini_hackathon_gradio/oideachais_mission_control/app.py` — add "Refresh" button to each of the 5 stage tabs
- [x] T4.3.2: Add a 6th "Models" tab rendering `MODEL_REGISTRY._entries` as `gr.Dataframe()`
- [x] T4.3.3: Add a 7th "Observability" tab showing last 5 structlog events (mocked for now)

## Phase 4.4 — oideachais_pdf_review polish
- [x] T4.4.1: `gemini_hackathon_gradio/oideachais_pdf_review/app.py` — replace the 1 Markdown stub with a 3-tab layout (Upload / Review / Export)
- [x] T4.4.2: Register a `@spaces.GPU`-decorated handler (conditional on `SPACE_ID` env var; falls back to a regular function in non-Space mode)
- [x] T4.4.3: The handler calls the BAML extractor + persists the review event to `_REVIEW_LOG`

## Phase 4.5 — Journey sourcing dedupe + copilot tests
- [x] T4.5.1: Verified no caller imports `journey.sourcing.sourcing.X` (`grep -rE "from journey.sourcing.sourcing" --include="*.py"` returns 0)
- [x] T4.5.2: Verified canonical `gemini_hackathon/journey/sourcing/` is already better (has `_shared_fs()` singleton; the outer duplicate lacks it — no improvements to port)
- [x] T4.5.3: Delete `journey/sourcing/sourcing/` (the outer duplicate)
- [x] T4.5.4: Create `journey/sourcing_copilot_tests/__init__.py` + `test_tools.py` + `test_agent.py`
- [x] T4.5.5: `test_tools.py` covers the 7 canonical tools (`get_status`, `list_artefacts`, `mark_excluded`, `list_cloud_run_services`, `list_scheduled_jobs`, `trigger_step`, `recommend_next_steps`) with `BAML_TEST_MODE=true`
- [x] T4.5.6: `test_agent.py` covers `build_copilot_agent()` + `build_runner()` tool-binding

## Phase 4.6 — Gradio studio verification + tests
- [x] T4.6.1: `tests/gradio/test_editorial_studio.py` — `build_app()` returns non-None; each of the 4 newly-wired tabs renders Markdown
- [x] T4.6.2: `tests/gradio/test_anam_education.py` — `build_app()` returns non-None; all 7 tabs present
- [x] T4.6.3: `tests/gradio/test_oideachais_mission_control.py` — `build_app()` returns non-None; 5 (now 7) tabs render
- [x] T4.6.4: `tests/gradio/test_oideachais_pdf_review.py` — `build_app()` returns non-None; 3 tabs work
- [x] T4.6.5: Each studio's `for studio in ...; do uv run python -c "..."` smoke-test passes

## Quality gates
- [x] TG.1: `uv run pytest tests/ -v` — 386+ tests pass (was 381)
- [x] TG.2: `bash scripts/verify.sh` — 6/8 [OK] (pre-existing baseline)
- [x] TG.3: `grep -rE "Wired in W12|deferred|W3 scaffolding" gemini_hackathon_gradio/` — 0 hits (was 6)
- [x] TG.4: `grep -rE "#REPLACE-[0-9]" gemini_hackathon/ --include="*.py"` — 0 hits (Phase 3 baseline)
- [x] TG.5: `test -d journey/sourcing/sourcing` — false (deduped)

## Commit + archive
- [x] TC.1: `git commit -m "feat(phase-4): wire Journey + Gradio polish — 4 studios + sourcing dedupe + copilot tests"` (no push)
- [x] TC.2: `openspec archive 2026-08-31-journey-gradio-polish-v1 --yes`
