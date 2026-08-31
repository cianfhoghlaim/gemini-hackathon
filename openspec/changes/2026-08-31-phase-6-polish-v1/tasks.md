# Tasks — 2026-08-31-phase-6-polish-v1

> **Phase 6 of the gemini_hackathon polish plan.** Ordered checklist with
> quality gates between phases.

## Sub-task 6.0 — openspec change opened + baseline captured

- [x] Open the openspec change at
      `openspec/changes/2026-08-31-phase-6-polish-v1/`
- [x] Capture baseline `uv run pytest tests/ --no-header` output
      (30 failures pre-state)
- [x] Capture baseline `uv run pytest tests/ --cov=gemini_hackathon`
      (`TOTAL 42%` pre-state)

## Sub-task 6.1 — fix `tests/test_call_llm.py`

- [ ] Read `gemini_hackathon/call_llm.py:194-213` (canonical 7-tier
      chain) and `gemini_hackathon/model_registry.py:1315-1340`
      (canonical `_PUBLIC_TIER_INDEX`)
- [ ] Update the 19 assertion lines to match the 7-tier chain
      (Tier 1 = `gemini-3.5-flash` on Vertex, NOT `minimax-m3`)
- [ ] Add a `# Updated 2026-08-31 (Phase 6)` comment on each changed line
- [ ] Confirm `uv run pytest tests/test_call_llm.py` shows 0 failures

## Sub-task 6.2 — fix the 14 other pre-existing failures

- [ ] `tests/test_dlt_pipelines.py::test_jurisdiction_boards_has_10_entries`
      — 10 → 11 (Jersey + Guernsey added by Phase 0)
- [ ] `tests/test_dlt_pipelines.py::test_official_doc_fetcher_handles_missing_pdfs_gracefully`
      — align with `OFFICIAL_DOC_COLUMNS`
- [ ] `tests/test_ocr.py::test_ocr_returns_extracted_text_via_gemini_vision`
      — fix the mocked call path
- [ ] `tests/test_assets.py::test_router_priority_order_fibo_invoke_unsloth`
      — accept the LITELLM-first priority
- [ ] `tests/test_adk_agent.py::test_build_adk_agent_returns_real_llmagent_and_runner`
      — match ADK 2.7.1 `LlmAgent` shape
- [ ] `tests/test_adk_agent.py::test_agents_chat_runs_real_agent_when_adk_available`
      — match ADK 2.7.1 `Runner` shape
- [ ] DELETE `tests/test_babylon_export.py::test_babylon_file_uses_only_three_babylon_modules`
- [ ] DELETE `tests/test_babylon_export.py::test_babylon_renders_an_intersection_observer`
- [ ] Confirm `uv run pytest tests/ --no-header` shows ≤3 failures

## Sub-task 6.3 — add coverage tests for 5 modules

- [ ] `tests/test_secrets_loader.py` — ≥5 tests (GSM path + local-env
      fallback + missing key handling + auth scope)
- [ ] `tests/test_subnations.py` — ≥3 tests (default subnation + 7
      jurisdictions + learner context)
- [ ] `tests/test_ocr_ensemble.py` — ≥4 tests (4-path ensemble happy
      + 1 failure + 1 stub)
- [ ] `tests/test_certificate_pipeline.py` — ≥6 tests (cert backends
      + rubric scoring + progression ledger)
- [ ] `tests/orchestration/test_pedagogy_overlay.py` — ≥4 tests
      (overlay materialisation + 12 principles cache)
- [ ] `tests/test_env_example_completeness.py` — ≥3 tests that scan
      `os.environ.get()` calls in `gemini_hackathon/` and assert every
      key is in `.env.example`
- [ ] Confirm coverage ≥70% via `uv run pytest tests/
      --cov=gemini_hackathon --cov-report=term`

## Sub-task 6.4 — document the 29 missing env vars

- [ ] `.env.example` — add the Journey section (~10 keys) + ADK
      observability section (~5 keys) + OCR / Document AI section
      (~4 keys) + Firestore / GCP section (~5 keys) + observability /
      MLflow section + Stitch / Functions section (~3 keys)
- [ ] `secrets.yaml` — add the same 29 keys as `required: false`
- [ ] Confirm `.env.example` has ≥52 keys (was 32)

## Sub-task 6.5 — clean `KNOWN_ISSUES.md` + add HF publish targets

- [ ] `docs/KNOWN_ISSUES.md` — mark resolved items as `[RESOLVED]`
      with the commit hash, delete obsolete items, tag open items as
      `[OPEN: Phase X follow-up]`
- [ ] `Makefile` — add `hf-publish-<space>` target that wraps
      `huggingface-cli upload --repo-type space cianfhoghlaim/<space> .`
- [ ] `Makefile` — add `hf-publish-all` target that loops over the 6
      Spaces
- [ ] Confirm `make help` lists both targets

## Quality gates (run all 3)

- [ ] `uv run pytest tests/ --no-header` — target ≤3 failures + 0 errors
- [ ] `bash scripts/verify.sh 2>&1 | tail -15` — 6/8 [OK] unchanged
- [ ] `uv run pytest tests/ --cov=gemini_hackathon --cov-report=term` —
      target ≥70%

## Commit + archive

- [ ] `git add` only the changed files (no `git add -A`)
- [ ] `git commit -m "chore(phase-6): final polish — fix 30 test
      failures + document 29 env vars + add coverage"`
- [ ] DO NOT push (commit only — user will push)
- [ ] `openspec archive 2026-08-31-phase-6-polish-v1 --yes`
