# Spec Delta: pdf-pipeline (Phase 2)

This delta is applied by the OpenSpec change
[`2026-08-30-cocoindex-pdf-pipeline-v1`](../proposal.md). It describes
the **ADDED** Requirements to the canonical `pdf-pipeline` capability.

## ADDED Requirements

### Requirement: Phase 2a — PDF downloader materialises remote-URL PDFs locally

The system SHALL provide `dlt_pipelines/pdf_downloader.py` with a
`run_downloader()` function that:

1. Reads every row in the `official_documents` DuckDB table where
   `source_kind = 'remote_url'`
2. Downloads each URL to a canonical local path
   `data/bi_ep/syllabi_raw/<source_key>/<subject>/<lang>/<sha256>.pdf`
3. Computes `sha256_hash`, `page_count` (via pypdf), and `file_size_bytes`
4. Updates the row with the local path + computed metadata +
   `source_kind = 'downloaded'`
5. Is idempotent: re-running the function is a no-op when the row has
   already been downloaded (zero rows match the `remote_url` filter)

#### Scenario: first run downloads all 7 remote-URL PDFs

- **WHEN** `run_downloader()` is called for the first time against a
  populated `official_documents` table containing 7 `remote_url` rows
- **THEN** the function SHALL download all 7 PDFs to disk
- **AND** SHALL compute sha256 + page_count + file_size_bytes for each
- **AND** SHALL update each row's pdf_path to the local path + source_kind
  to `downloaded`
- **AND** SHALL return `{"considered": 7, "downloaded": 7, "skipped": 0, "failed": 0}`

#### Scenario: second run is a no-op

- **WHEN** `run_downloader()` is called after the first run completed
- **THEN** the SQL filter `WHERE source_kind = 'remote_url'` SHALL return
  zero rows
- **AND** the function SHALL return `{"considered": 0, "downloaded": 0, "skipped": 0, "failed": 0}`
- **AND** SHALL NOT re-fetch any HTTP URLs

#### Scenario: one PDF fails to download

- **WHEN** the HTTP fetch raises (e.g. 404 or timeout) for one row
- **THEN** the function SHALL log `pdf_downloader.failed url=<url> reason=<error>`
- **AND** SHALL increment `stats["failed"]`
- **AND** SHALL leave the failed row's `source_kind` as `'remote_url'`
  (so a re-run can retry)
- **AND** SHALL continue to process the remaining rows

#### Scenario: DuckDB file missing

- **WHEN** the configured DuckDB file does not exist
- **THEN** the function SHALL log
  `pdf_downloader.duckdb_missing path=<path>`
- **AND** SHALL return `{"considered": 0, "downloaded": 0, "skipped": 0, "failed": 0}`
- **AND** SHALL NOT raise

### Requirement: Raw PDF directory is git-ignored

The `data/bi_ep/syllabi_raw/` directory SHALL contain a `.gitignore` file
that excludes all files (the downloaded PDFs are reproducible from
`KNOWN_OFFICIAL_URLS` + `run_downloader()`).

#### Scenario: raw PDFs never committed to git

- **WHEN** `git check-ignore data/bi_ep/syllabi_raw/<source_key>/<subject>/<lang>/<sha256>.pdf` is run
- **THEN** git SHALL report the file as ignored

### Requirement: Phase 2a tests cover happy + failure + idempotent paths

The `tests/test_pdf_downloader.py` file SHALL contain at least 10 tests
covering:

1. ``_safe_filename_part`` sanitization edge cases
2. ``_page_count`` for valid + invalid PDF bytes
3. ``_compute_sha256`` matches `hashlib.sha256`
4. ``_already_downloaded`` empty + present cases
5. ``_local_path_for`` canonical path shape
6. ``run_downloader`` no-DuckDB no-op
7. ``run_downloader`` mock-fetch writes file + updates DuckDB row
8. ``run_downloader`` second run is idempotent (no-op)
9. ``run_downloader`` handles fetch failure
10. ``run_downloader`` zero-remote-rows no-op

#### Scenario: all 10 tests pass

- **WHEN** `pytest tests/test_pdf_downloader.py` is run
- **THEN** 12 tests SHALL pass (the 10 minimum + 2 edge cases)
- **AND** zero tests SHALL fail