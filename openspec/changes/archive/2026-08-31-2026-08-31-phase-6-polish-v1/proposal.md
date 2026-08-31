# Proposal — 2026-08-31-phase-6-polish-v1

> **One-liner:** final polish pass for the gemini_hackathon submission —
> fix the 30 pre-existing test failures, lift coverage from 42% to ≥70%,
> document the 29 missing env vars, and clean `KNOWN_ISSUES.md`.

## Why

Phases 0–5 closed the platform + content surfaces (Phases 1–5) and the
infrastructure / IaC substrate (Phases 0 + 3). The Python test suite
still has **30 pre-existing failures** (450 passing) and the
`gemini_hackathon/` package sits at **42% coverage** (well below the
`pyproject.toml` 70% threshold). Many env-var names that production code
references are not declared in `.env.example`, so a fresh `cp
.env.example .env` produces import-time `KeyError`s. Without a final
polish pass the submission's `make verify` gate shows 6/8 [OK] and the
README's claims about "all tests pass" are false.

Phase 6 closes these surface-level gaps without touching the
infrastructure substrate (Phases 0–5 are stable and committed):

## What Changes

1. **MODIFIED** `tests/test_call_llm.py` — fix the 19 assertions that
   drifted after the Gemma+Gemini refocus promoted Tier 3 → Tier 1
   (`gemini-3.5-flash` is now Tier 1 primary on Vertex, not Tier 3
   Agent Garden).
2. **MODIFIED** `tests/test_dlt_pipelines.py::test_jurisdiction_boards_has_10_entries`
   — bump expected count 10 → 11 (Jersey + Guernsey added by Phase 0).
3. **MODIFIED** `tests/test_dlt_pipelines.py::test_official_doc_fetcher_handles_missing_pdfs_gracefully`
   — align with the current `OFFICIAL_DOC_COLUMNS` shape.
4. **MODIFIED** `tests/test_ocr.py::test_ocr_returns_extracted_text_via_gemini_vision`
   — fix the mocked call to match the current VLM-backed path.
5. **MODIFIED** `tests/test_assets.py::test_router_priority_order_fibo_invoke_unsloth`
   — accept the LITELLM-first priority order added in Phase 8.
6. **MODIFIED** `tests/test_adk_agent.py` — match the 2.7.1 ADK
   `LlmAgent` import shape.
7. **DELETED** `tests/test_babylon_export.py::test_babylon_file_uses_only_three_babylon_modules`
   and `tests/test_babylon_export.py::test_babylon_renders_an_intersection_observer`
   (the `web/src/components/babylon/` tree is deferred per the
   `2026-08-27-defer-tuatha-consolidation-v1` change).
8. **NEW** `tests/test_secrets_loader.py` — ≥5 tests covering the
   GSM-first / local-env-fallback loader.
9. **NEW** `tests/test_subnations.py` — ≥3 tests for the
   Ireland/England/NI/Scotland/Wales/Jersey/Guernsey defaults.
10. **NEW** `tests/test_ocr_ensemble.py` — ≥4 tests covering the
    4-path ensemble (Document AI + Gemma-Vision + LiteLLM + stub).
11. **NEW** `tests/test_certificate_pipeline.py` — ≥6 tests covering
    the LC/JC certificate pipeline backends + rubric.
12. **NEW** `tests/orchestration/test_pedagogy_overlay.py` — ≥4 tests
    for the NCCE pedagogy overlay materialisation.
13. **NEW** `tests/test_env_example_completeness.py` — ≥3 tests that
    walk `gemini_hackathon/` source for `os.environ.get(...)` calls and
    assert every key is documented in `.env.example`.
14. **MODIFIED** `.env.example` — adds 29 missing keys
    (JOURNEY_*, ADK_*, GCP_PROJECT_ID, MLFLOW_TRACKING_URI, etc.)
15. **MODIFIED** `secrets.yaml` — adds the same 29 keys as
    `required: false` GSM mappings.
16. **MODIFIED** `docs/KNOWN_ISSUES.md` — marks resolved items as
    `[RESOLVED]`, deletes obsolete items.
17. **MODIFIED** `Makefile` — adds `hf-publish-<space>` and
    `hf-publish-all` targets (HuggingFace Space publishing).

No production code is touched (`gemini_hackathon/`,
`dlt_pipelines/`, `cocoindex_flows/`, `baml_extracts/`,
`gemini_hackathon_gradio/`, `hf_spaces/`, `journey/`, `orchestration/`,
`cloud/`, `web/`). The DLT source files for Ireland / Leabharlann /
Journey are untouched.

## Impact

- **Test count**: 30 failures → 0 (target ≤3 pre-existing that can't be fixed)
- **Coverage**: 42% → ≥70% (matches the `pyproject.toml` threshold)
- **`verify.sh`**: 6/8 [OK] (unchanged; the 2 ticks that fail are
  pre-existing ruff/mypy baseline per Phase 5 subagent)
- **`.env.example`**: 32 → 52+ keys
- **`secrets.yaml`**: 15 → 35+ mappings
- **`KNOWN_ISSUES.md`**: every line tagged `[RESOLVED]` or
  `[OPEN: Phase X follow-up]`
- **Makefile**: +2 new `hf-publish-*` targets

## Dependencies

- All Phases 0–5 commits (the platform + IaC substrate)
- `2026-08-30-gcp-first-iac-refactor-v1` (the GSM-first secrets
  loader that `tests/test_secrets_loader.py` covers)
- `2026-08-27-defer-tuatha-consolidation-v1` (the Babylon.js
  deprecation that justifies deleting
  `tests/test_babylon_export.py`)

## Quality gates

- `openspec validate 2026-08-31-phase-6-polish-v1 --strict`
- `uv run pytest tests/ --no-header` — target ≤3 failures + 0 errors
- `uv run pytest tests/ --cov=gemini_hackathon --cov-report=term` —
  target ≥70%
- `make verify` — 6/8 [OK] baseline unchanged (ruff + mypy baseline
  pre-existing)

## Rollback

`git revert <this-commit>` — Phase 6 is surface-level (tests + docs +
Makefile + secrets catalogue). The platform behavior is unaffected.
