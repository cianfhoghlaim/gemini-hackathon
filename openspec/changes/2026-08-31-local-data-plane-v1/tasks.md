# Tasks for 2026-08-31-local-data-plane-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-local-data-plane-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/local-data-plane/spec.md` (1 spec delta)
- [x] T0.3: `openspec/changes/.../tasks.md` (this file)
- [x] T0.4: `openspec validate 2026-08-31-local-data-plane-v1 --strict` passes

## Phase 1 — DLT smoke (3 flagship pipelines → DuckDB)
- [x] T1.1: `uv run python -m dlt_pipelines.official_doc_fetcher` runs and writes ≥5 rows
- [x] T1.2: `uv run python -m dlt_pipelines.pdf_page_metadata` runs and writes ≥5 rows
- [x] T1.3: `uv run python -m dlt_pipelines.safeguarding_fetcher` runs and writes ≥1 row
- [x] T1.4: `data/gemini_hackathon.duckdb` exists with ≥5 rows in `official_documents`
- [x] T1.5: `KNOWN_ISSUES.md` documents the `data/ireland/leaving_certificate/<subject>/<lang>/` gap
- [x] T1.6: minimal stub `data/ireland/leaving_certificate/mathematics/en/README.md`

## Phase 2 — compose target switch (spec verification only)
- [x] T2.1: `docker compose config --quiet` exits 0
- [x] T2.2: `Dockerfile` sets `DUCKDB_PATH=/app/data/gemini.duckdb`
- [x] T2.3: `compose.yaml` mounts `duckdb-data:/app/data`
- [x] T2.4: `compose.yaml` has no errors
- [x] T2.5: NOT starting docker compose

## Phase 3 — LanceDB local mode (sentence_transformers)
- [x] T3.1: `data/lancedb/.gitkeep` + `.gitignore` comment
- [x] T3.2: `EMBED_BACKEND=sentence_transformers uv run python -m cocoindex_flows.ireland.junior_cycle_embedding` runs
- [x] T3.3: `data/lancedb/gemini_hackathon.lance/` exists + populated
- [x] T3.4: `docs/LOCAL_DEV.md` "Local data plane" section added

## Phase 4 — BAML extract chain (offline TestMock)
- [x] T4.1: `uv run baml-cli generate` regenerates client
- [x] T4.2: `BAML_TEST_MODE=true uv run python -m cocoindex_flows.education.lc6_extraction_app --subject mathematics --language en` writes ≥1 row
- [x] T4.3: `SQLITE_PATH` env override honoured

## Phase 5 — Notebooks 02, 03, 04
- [x] T5.1: `02_pdf_downloader_demo.ipynb` executed via `jupyter nbconvert --execute --inplace` (or gap documented + skipped)
- [x] T5.2: `03_pdf_processing_benchmark.ipynb` executed (or gap documented)
- [x] T5.3: `04_baml_extraction_walkthrough.ipynb` executed (or gap documented)
- [x] T5.4: import path fixes applied inline (max-1 line per fix)
- [x] T5.5: corpus gaps documented in notebook markdown cells

## Phase 6 — Observability stack spec verification
- [x] T6.1: 5 Langfuse services present in `compose.yaml`
- [x] T6.2: `MLFLOW_TRACKING_URI` env wired to `http://mlflow:5000`
- [x] T6.3: `LANGFUSE_HOST` env wired (default cloud.langfuse.com; documented local override)
- [x] T6.4: `gemini-hackathon` service gains 3 `depends_on` entries (langfuse-web, langfuse-postgres, mlflow)

## Phase 7 — New integration tests
- [x] T7.1: `tests/dlt/test_official_doc_fetcher_e2e.py` — `tmp_path` + `DUCKDB_PATH` env override + asserts ≥1 row
- [x] T7.2: `tests/cocoindex/test_lancedb_local_mode.py` — `EMBED_BACKEND=sentence_transformers` + asserts LanceDB table exists
- [x] T7.3: `tests/baml/test_extract_chain_offline.py` — `BAML_TEST_MODE=true` + asserts SQLite has ≥1 row
- [x] T7.4: all 3 tests marked `@pytest.mark.integration`
- [x] T7.5: `pytest -m integration` shows 3 new passed

## Phase 8 — Quality gates + docs + commit + archive
- [x] T8.1: `make dlt-smoke-all` exits 0
- [x] T8.2: `make cocoindex-update` exits 0 OR gracefully no-ops
- [x] T8.3: `make ncce-extract` exits 0
- [x] T8.4: `make compare-demo` exits 0
- [x] T8.5: `pytest` shows ≥354 + 3 = 357 passed
- [x] T8.6: `bash scripts/verify.sh` 8/8 green (per Phase 0 baseline; ticks 3+4 out of scope)
- [x] T8.7: `docs/LOCAL_DEV.md` updated with "Local data plane" section
- [x] T8.8: `KNOWN_ISSUES.md` updated with 3 documented gaps
- [x] T8.9: commit `chore(phase-1): wire local data plane end-to-end` (NO push)
- [x] T8.10: `openspec archive 2026-08-31-local-data-plane-v1` after commit

## Notes on what we explicitly did NOT touch

- **Phase 0 surfaces**: `gemini_hackathon/model_registry.py` (per Phase 0 commit `603637c` — the canonical surface, out of scope).
- **`baml_extracts/` source files** (Phase 5 surface — BAML contract changes go through a separate openspec change).
- **`cloud/`, `infra/`, `web/`, `gemini_hackathon_gradio/`, `orchestration/`, `journey/`, `hf_spaces/`** — all out of scope per the instruction "What NOT to touch".
- **CI workflow** (`.github/workflows/ci.yml`) — no changes; the 3 new tests run under `-m integration` which is opt-in.
- **Production DLT destination** (`ducklake_gemini_hackathon` + `motherduck_gemini_hackathon`) — the local DuckDB file is the offline dev default; the prod Cloud Run path uses BigQuery.
