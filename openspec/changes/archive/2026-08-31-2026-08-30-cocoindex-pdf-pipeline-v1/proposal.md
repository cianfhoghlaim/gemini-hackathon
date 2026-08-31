# 2026-08-30-cocoindex-pdf-pipeline-v1

> **Phase 2 of the multi-stage plan (see AGENTS.md). Build the CocoIndex
> PDF extraction pipeline that processes the 13 official British Isles
> syllabus / exam-paper / marking-scheme PDFs into Markdown.**

## Why

The current state (`dlt_pipelines/official_doc_fetcher.py`) emits DLT
catalog rows for the 8 BI jurisdictions. The Ireland NCCA resource is
filesystem-based (it scans `leaving_certificate/<subject>/<en|ga>/*.pdf`).
The remaining 7 jurisdictions emit only remote-URL catalog rows — the
URL is recorded but the PDF is never downloaded. This means the
CocoIndex extraction pipeline (Phases 3-5) cannot run on them.

Phase 2 closes this gap: download the 7 remote PDFs locally, then
process all 13 through a single CocoIndex App that emits Markdown
suitable for BAML extraction.

## What changes

### Phase 2a — Download the 7 remote PDFs (this change)

- **NEW `dlt_pipelines/pdf_downloader.py`** — reads the `official_documents`
  DuckDB table for rows with `source_kind='remote_url'`, downloads each
  URL to `data/bi_ep/syllabi_raw/<source_key>/<subject>/<lang>/<sha256>.pdf`,
  computes `sha256_hash` + `page_count` (via `pypdf`) + `file_size_bytes`,
  and updates the row's source_kind to `'downloaded'`. Idempotent —
  re-running the downloader skips already-downloaded files (matched by
  sha256).
- **NEW `data/bi_ep/syllabi_raw/.gitignore`** — raw PDFs never get
  committed to git
- **NEW `tests/test_pdf_downloader.py`** — mocks HTTP (via
  `unittest.mock` + `httpx`), verifies dedup + idempotency + the
  DuckDB upsert path
- **NEW `notebooks/02_pdf_downloader_demo.ipynb`** — jupyter walkthrough
  of one download with checksum display

### Phase 2b — pdf_to_markdown CocoIndex App (next commit)

- **NEW `cocoindex_flows/pdf/pdf_to_markdown_app.py`** — `@coco.fn.as_async(runner=coco.GPU)`
  Docling converter. Walks `data/bi_ep/syllabi_raw/` recursively. Writes
  `data/bi_ep/syllabi_md/<subnation>/<stage>/<subject>/<lang>/<stem>.md`
  preserving the directory tree.
- **NEW `cocoindex_flows/pdf/_shared.py`** — `memoised_converter()` cached
  `DocumentConverter` instance + `extract_markdown(content: bytes) -> str` helper.
- **NEW `cocoindex_flows/pdf/benchmark.py`** — head-to-head benchmark:
  pymupdf4llm vs docling vs pypdfium2 vs marker. Logs time/quality table
  to MLflow.
- **NEW `orchestration/defs/3_model_lifecycle/bi_ep_pdf_assets.py`** —
  Dagster asset that runs `cocoindex update pdf_to_markdown_app`; depends
  on the `dlt_pdf_downloader` asset.

### Phase 2c — Quality gate + benchmark notebook (final commit)

- All 13 PDFs converted successfully.
- `notebooks/03_pdf_processing_benchmark.ipynb` — interactive
  walkthrough of benchmark results; users can pick the backend and see
  per-file timing.

## Acceptance

- `data/bi_ep/syllabi_raw/<source_key>/<subject>/<lang>/<sha256>.pdf` files exist for all `KNOWN_OFFICIAL_URLS` rows
- `pdf_path` in the `official_documents` DuckDB table is rewritten from URL to local path; `source_kind = 'downloaded'`
- SHA256 + page_count + file_size_bytes populated for all rows
- `python -m dlt_pipelines.pdf_downloader` runs twice; second run is a no-op
- `pytest tests/test_pdf_downloader.py` passes
- `pytest gemini_hackathon_backend/tests/` passes (no regressions)
- `web tsc --noEmit` zero errors

## Dependencies

- **Blocked by:** Phase 0 (memory) + Phase 1 (observability) — already pushed in commits `ebef31e` + `2805037`.
- **Unblocks:** Phase 3 (BAML extraction), Phase 4 (equivalency graph), Phase 5 (model comparison harness).
- **Cross-repo:** the CocoIndex PDF App shape is lifted from `docs/cocoindex_examples/pdf_embedding/main.py:55-147`.

## Compatibility

- The downloader reads from the `official_documents` table that
  `dlt_pipelines/official_doc_fetcher.py` writes. Both share the schema
  defined in `OFFICIAL_DOC_COLUMNS`.
- `source_kind='remote_url'` rows are picked up; `source_kind='filesystem'`
  rows (Ireland) are left untouched.
- Re-running is idempotent (sha256 match).
- The downloader does NOT modify `dlt_pipelines/official_doc_fetcher.py` —
  it's an additive module that reads + writes the same table.