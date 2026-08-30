# Tasks for 2026-08-30-cocoindex-pdf-pipeline-v1

## Phase 2a — PDF downloader
- [x] T1: OpenSpec change folder + proposal.md
- [ ] T2: `dlt_pipelines/pdf_downloader.py` — read `official_documents` for remote_url rows; download to `data/bi_ep/syllabi_raw/<source_key>/<subject>/<lang>/<sha256>.pdf`; compute sha256 + page_count + file_size_bytes; upsert with source_kind='downloaded'
- [ ] T3: `data/bi_ep/syllabi_raw/.gitignore` — ignore raw PDFs
- [ ] T4: `tests/test_pdf_downloader.py` — mock HTTP, verify dedup + idempotency + DuckDB upsert
- [ ] T5: `notebooks/02_pdf_downloader_demo.ipynb` — jupyter walkthrough
- [ ] T6: `pytest tests/test_pdf_downloader.py` passes
- [ ] T7: commit + push Phase 2a

## Phase 2b — pdf_to_markdown CocoIndex App (next phase)
- [ ] T8: `cocoindex_flows/pdf/_shared.py` — memoised Docling converter + helper
- [ ] T9: `cocoindex_flows/pdf/pdf_to_markdown_app.py` — `@coco.fn.as_async(runner=coco.GPU)` App
- [ ] T10: `cocoindex_flows/pdf/benchmark.py` — pymupdf4llm vs docling vs pypdfium2 vs marker
- [ ] T11: `orchestration/defs/3_model_lifecycle/bi_ep_pdf_assets.py` — Dagster asset
- [ ] T12: commit + push Phase 2b

## Phase 2c — Quality gate + benchmark notebook
- [ ] T13: All 13 PDFs converted; spot-check 2 by opening the .md
- [ ] T14: `notebooks/03_pdf_processing_benchmark.ipynb` — interactive walkthrough
- [ ] T15: commit + push Phase 2c

## Phase 2 validation
- [ ] T16: `openspec validate 2026-08-30-cocoindex-pdf-pipeline-v1 --strict` passes
- [ ] T17: `pytest` — no new failures (7 pre-existing per KNOWN_ISSUES.md)
- [ ] T18: web `tsc --noEmit` zero errors
- [ ] T19: archive the OpenSpec change after deploy