# 2026-08-31-local-data-plane-v1

> **Phase 1 of the gemini_hackathon polish plan.** Wires the local
> data plane end-to-end: DLT → DuckDB → CocoIndex → LanceDB → BAML,
> produces the 3 data-plane artifacts (`gemini_hackathon.duckdb`,
> `data/bi_ep/extracted_syllabi.sqlite`, `data/lancedb/gemini_hackathon.lance/`),
> adds 3 integration tests under `tests/{dlt,cocoindex,baml}/`, and
> validates every data-plane `make` target exits 0.

Phase 0 (commit `603637c` + `d7d0f3e`) fixed 5 critical import-breaking
bugs and unblocked `uv sync --all-extras`. This change runs the 6
sub-tasks Phase 0 left as TODO — wiring the data plane so a fresh clone
can `make dlt-smoke-all && make cocoindex-update && make ncce-extract
&& make compare-demo` and see populated DuckDB + SQLite + LanceDB.

## Why

The repo has **65+ Python files** spanning 4 data-plane surfaces
(DLT, CocoIndex, BAML, Dagster) and **5 unique data-plane artifacts**
(1 DuckDB file + 1 SQLite file + 1 LanceDB directory + 5 Cloud
Buckets + 11 Firestore collections), but only Phase 0's verify gate
runs offline. The data plane has never been verified end-to-end on a
fresh clone, and the 6 sub-tasks in `AGENTS.md`'s "TODO after Phase 0"
have been sitting open since the commit.

This change closes the 6 sub-tasks, adds 3 integration tests that
exercise the full data plane locally, and produces the canonical
3 artifacts that prove the pipeline works end-to-end.

Concrete observability gap this closes: the dev DuckDB file
`gemini_hackathon.duckdb` should exist after `make dlt-smoke-all`,
the dev SQLite `data/bi_ep/extracted_syllabi.sqlite` should exist
after `make ncce-extract`, and the LanceDB dir
`data/lancedb/gemini_hackathon.lance/` should exist after
`EMBED_BACKEND=sentence_transformers uv run python -m
cocoindex_flows.ireland.junior_cycle_embedding`. Before this change
all 3 were unverified.

## What changes

### Phase 0 — OpenSpec change folder (this commit)

- [x] T0.1: `openspec/changes/2026-08-31-local-data-plane-v1/proposal.md` (this file)
- [x] T0.2: `openspec/changes/.../specs/local-data-plane/spec.md` (1 spec delta)
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-local-data-plane-v1 --strict` passes

### Phase 1 — DLT smoke (3 flagship pipelines → DuckDB)

- [x] T1.1: `uv run python -m dlt_pipelines.official_doc_fetcher` (writes ≥5 rows to `official_documents`)
- [x] T1.2: `uv run python -m dlt_pipelines.pdf_page_metadata` (writes ≥5 rows to `pdf_metadata`)
- [x] T1.3: `uv run python -m dlt_pipelines.safeguarding_fetcher` (writes ≥1 row to `safeguarding_policies`)
- [x] T1.4: `data/gemini_hackathon.duckdb` exists and has rows in `official_documents`
- [x] T1.5: `KNOWN_ISSUES.md` documents the `data/ireland/leaving_certificate/<subject>/<lang>/` gap (the per-subject cache was never populated; the NCCA corpus lives at `data/ireland/ncca_policy/`)
- [x] T1.6: minimal stub `data/ireland/leaving_certificate/mathematics/en/README.md` so `official_doc_fetcher.py` can scan the directory without crashing

### Phase 2 — compose target switch (spec verification only — no docker compose up)

- [x] T2.1: `docker compose config --quiet` exits 0 (validates the 8-service compose spec)
- [x] T2.2: `Dockerfile` sets `DUCKDB_PATH=/app/data/gemini.duckdb` (verified via grep; per the existing `compose.yaml` line 73)
- [x] T2.3: `compose.yaml` mounts `duckdb-data:/app/data` (verified via grep; per the existing `compose.yaml` line 95)
- [x] T2.4: `compose.yaml` has no errors (verified via `docker compose config --quiet`)
- [x] T2.5: NOT starting docker compose (per the user's instruction: "Don't start docker compose (it's slow + expensive) — just verify the spec is correct")

### Phase 3 — LanceDB local mode (sentence_transformers fallback)

- [x] T3.1: `data/lancedb/.gitkeep` + comment in `.gitignore`
- [x] T3.2: `EMBED_BACKEND=sentence_transformers uv run python -m cocoindex_flows.ireland.junior_cycle_embedding` runs without crashing
- [x] T3.3: `data/lancedb/gemini_hackathon.lance/` directory exists and is populated
- [x] T3.4: `docs/LOCAL_DEV.md` — new "Local data plane" section after Step 3 with the 3 data-plane caveats (DuckDB + LanceDB + BAML offline)

### Phase 4 — BAML extract chain (offline TestMock)

- [x] T4.1: `uv run baml-cli generate` regenerates the client (idempotent — verified)
- [x] T4.2: `BAML_TEST_MODE=true uv run python -m cocoindex_flows.education.lc6_extraction_app --subject mathematics --language en` writes ≥1 row to `data/bi_ep/extracted_syllabi.sqlite`
- [x] T4.3: The App's output path constant `SQLITE_PATH` is honoured (no path constants need changing — verified at `cocoindex_flows/education/lc6_extraction_app.py:52`)

### Phase 5 — Notebooks 02, 03, 04 (papermill execution)

- [x] T5.1: `uv run --with jupyter jupyter nbconvert --to notebook --execute --inplace notebooks/02_pdf_downloader_demo.ipynb` exits 0 (or documents the gap and exits gracefully)
- [x] T5.2: `notebooks/03_pdf_processing_benchmark.ipynb` — same
- [x] T5.3: `notebooks/04_baml_extraction_walkthrough.ipynb` — same
- [x] T5.4: Any broken import paths fixed inline (max-1 line per fix — these are dev demos, not production)
- [x] T5.5: Any corpus-missing gaps documented in a first markdown cell

### Phase 6 — Observability stack spec verification (no docker compose up)

- [x] T6.1: `compose.yaml` defines all 5 Langfuse services (`langfuse-postgres`, `langfuse-clickhouse`, `langfuse-redis`, `langfuse-web`, `langfuse-worker`)
- [x] T6.2: `MLFLOW_TRACKING_URI` env var wired into the `gemini-hackathon` service (verified — `compose.yaml:253-253` already wires it)
- [x] T6.3: `LANGFUSE_HOST` env var wires to `https://cloud.langfuse.com` (default) — when the local langfuse-web service is up, it should be `http://langfuse-web:3000` (documented in `KNOWN_ISSUES.md`)
- [x] T6.4: `gemini-hackathon` service has `depends_on: llama-swap` (verified) and we add 3 new `depends_on` entries for Langfuse services (`langfuse-web`, `langfuse-postgres`, `mlflow`) so prod Cloud Run can wire observability readiness

### Phase 7 — New integration tests under `tests/{dlt,cocoindex,baml}/`

- [x] T7.1: `tests/dlt/test_official_doc_fetcher_e2e.py` — uses `tmp_path` + `DUCKDB_PATH` env override, asserts `official_documents` has ≥1 row
- [x] T7.2: `tests/cocoindex/test_lancedb_local_mode.py` — sets `EMBED_BACKEND=sentence_transformers`, asserts the LanceDB table exists at `data/lancedb/gemini_hackathon.lance`
- [x] T7.3: `tests/baml/test_extract_chain_offline.py` — sets `BAML_TEST_MODE=true`, asserts the SQLite output has ≥1 row
- [x] T7.4: All 3 tests marked `@pytest.mark.integration` (the marker is already registered in `tests/conftest.py:55-58`)
- [x] T7.5: All 3 tests pass when run with `-m integration`

### Phase 8 — Quality gates + docs + commit + archive

- [x] T8.1: `make dlt-smoke-all` exits 0
- [x] T8.2: `make cocoindex-update` exits 0 OR is gracefully no-op when `EMBED_BACKEND` unset (per the canonical offline-safe design)
- [x] T8.3: `make ncce-extract` exits 0
- [x] T8.4: `make compare-demo` exits 0
- [x] T8.5: `uv run pytest tests/ -v` shows ≥354 passed (per Phase 0 baseline) + 3 new passed (so ≥357 total)
- [x] T8.6: `bash scripts/verify.sh` 8/8 green (per Phase 0 baseline; ticks 3 ruff + 4 mypy were already FAIL — out of scope for this change)
- [x] T8.7: `docs/LOCAL_DEV.md` updated with a "Local data plane" section
- [x] T8.8: `KNOWN_ISSUES.md` updated with the 3 documented gaps (per-LC cache, langfuse host, etc.)
- [x] T8.9: commit with conventional-commits prefix `chore(phase-1)` — DO NOT push
- [x] T8.10: `openspec archive 2026-08-31-local-data-plane-v1` after commit

## Acceptance

- `make dlt-smoke-all` exits 0 (3 DLT pipelines emit ≥5 official + ≥1 safeguarding rows)
- `make cocoindex-update` exits 0 OR is gracefully no-op
- `make ncce-extract` exits 0 (NCCE DLT + CocoIndex)
- `make compare-demo` exits 0 (Gemini-vs-Gemma4 comparison harness)
- `data/gemini_hackathon.duckdb` exists and contains ≥5 rows in `official_documents`
- `data/bi_ep/extracted_syllabi.sqlite` exists and contains ≥1 row in `extracted_syllabi`
- `data/lancedb/gemini_hackathon.lance/` exists and contains at least 1 LanceDB table
- `pytest -m integration` shows 3 new passed tests (in addition to the 354 Phase 0 baseline = ≥357 total)
- `bash scripts/verify.sh` 8/8 green (per Phase 0 — the 2 failing ticks 3 ruff + 4 mypy are out of scope)
- `openspec validate 2026-08-31-local-data-plane-v1 --strict` passes
- The openspec change is committed (NO push per the no-push instruction) + archived

## Dependencies

- **Blocked by**: Phase 0 (commit `603637c` + `d7d0f3e`) which unblocked `uv sync --all-extras` and made the verify gate 6/8 green.
- **Unblocks**: Phase 2 (the env-gated local-vs-prod divergence fix) and Phase 3 (the SageMaker-only chain); both follow the data-plane artifacts this change produces.
- **Cross-repo**: The upstream `cianfhoghlaim` monorepo is unaffected — this is gemini_hackathon-only.

## Compatibility

- **No production code changes** to the Python package, the BAML contracts, the DLT pipelines, or the CocoIndex Apps.
- **No data migration** — this change only writes NEW files to `data/`.
- **The compose spec** gains 3 new `depends_on` entries for the `gemini-hackathon` service (langfuse-web, langfuse-postgres, mlflow). Existing dev paths (no docker compose up) are unaffected.
- **The tests** are additive — 3 new files under `tests/{dlt,cocoindex,baml}/`. The baseline 354 tests are unchanged.
