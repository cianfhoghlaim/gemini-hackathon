# local-data-plane Specification

## Purpose
TBD - created by archiving change 2026-08-31-local-data-plane-v1. Update Purpose after archive.
## Requirements
### Requirement: `make dlt-smoke-all` SHALL run all DLT pipelines against the local DuckDB
The system SHALL meet the requirement: `make dlt-smoke-all` SHALL run all DLT pipelines against the local DuckDB.

`make dlt-smoke-all` SHALL execute the 5 DLT pipelines
(`official_doc_fetcher`, `safeguarding_fetcher`, `uk_ncce_learning_graphs`,
`pdf_downloader`, `corpus_downloader`) sequentially against the
local DuckDB at `data/gemini_hackathon.duckdb` and exit 0 when all 5
finish without raising. The DLT pipelines SHALL be offline-safe
(zero network egress) per the canonical contract.

#### Scenario: fresh clone + `make dlt-smoke-all`

- **WHEN** a fresh clone is set up via `make install` and the user runs `make dlt-smoke-all`
- **THEN** the command SHALL exit 0
- **AND** `data/gemini_hackathon.duckdb` SHALL contain ≥5 rows in `official_documents`
- **AND** `data/gemini_hackathon.duckdb` SHALL contain ≥1 row in `safeguarding_policies`
- **AND** `data/gemini_hackathon.duckdb` SHALL contain ≥5 rows in `pdf_metadata`
- **AND** no network egress SHALL be required

### Requirement: LanceDB local mode SHALL be selectable via `EMBED_BACKEND=sentence_transformers`
The system SHALL meet the requirement: LanceDB local mode SHALL be selectable via `EMBED_BACKEND=sentence_transformers`.

The CocoIndex Apps SHALL honour the `EMBED_BACKEND` env var. When
set to `sentence_transformers`, the Apps SHALL use the
`SentenceTransformerEmbedder` (BAAI/bge-m3, 1024-d) and write to
local LanceDB at `data/lancedb/gemini_hackathon.lance/` — the
canonical offline fallback path. When set to `vertex` (the default),
the Apps SHALL use the Vertex AI embedder (gemini-embedding-001,
1536-d) and write to Firestore / Vertex AI Vector Search in the
deployed path.

#### Scenario: `EMBED_BACKEND=sentence_transformers uv run python -m cocoindex_flows.ireland.junior_cycle_embedding`

- **WHEN** the user runs the canonical JC embedding App with `EMBED_BACKEND=sentence_transformers`
- **THEN** the App SHALL run end-to-end without crashing
- **AND** `data/lancedb/gemini_hackathon.lance/` SHALL contain at least 1 LanceDB table

#### Scenario: `EMBED_BACKEND=vertex` is the production default

- **WHEN** the user runs any CocoIndex App with no `EMBED_BACKEND` set
- **THEN** the App SHALL use the Vertex AI embedder (the production path)
- **AND** if Vertex AI creds are missing, the App SHALL fail loudly with a descriptive error

### Requirement: BAML extract chain SHALL be runnable offline via `BAML_TEST_MODE=true`
The system SHALL meet the requirement: BAML extract chain SHALL be runnable offline via `BAML_TEST_MODE=true`.

The BAML client SHALL honour the `BAML_TEST_MODE=true` env var. When
set, the client SHALL use the canonical `TestMock` client (already
wired in `baml_extracts/clients.baml`) so the 5 LC6 extraction
functions (`ExtractCurriculumSyllabus`, `ExtractExamPaperLayout`,
`ExtractMarkingSchemeGuideline`, `ExtractCrossLinguisticConcept`,
`ExtractSyllabusDiagram`) return deterministic stub-shaped output.
The downstream App (`cocoindex_flows.education.lc6_extraction_app`)
SHALL write the extracted rows to `data/bi_ep/extracted_syllabi.sqlite`.

#### Scenario: `BAML_TEST_MODE=true uv run python -m cocoindex_flows.education.lc6_extraction_app --subject mathematics --language en`

- **WHEN** the user runs the LC6 extraction App with `BAML_TEST_MODE=true`
- **THEN** the App SHALL run end-to-end without raising
- **AND** `data/bi_ep/extracted_syllabi.sqlite` SHALL contain ≥1 row in `extracted_syllabi`
- **AND** no network egress SHALL be required

### Requirement: integration tests SHALL exercise the full data plane
The system SHALL meet the requirement: integration tests SHALL exercise the full data plane.

The `tests/` tree SHALL contain 3 integration test files (one per
data-plane surface) that exercise the full data plane end-to-end on
a fresh clone. Each test SHALL be marked `@pytest.mark.integration`
and SHALL be opt-in via `pytest -m integration`.

The 3 tests SHALL be:

1. `tests/dlt/test_official_doc_fetcher_e2e.py` — uses `tmp_path`
   + `DUCKDB_PATH` env override to redirect the destination file,
   runs `official_doc_fetcher.run()`, and asserts the
   `official_documents` table has ≥1 row.
2. `tests/cocoindex/test_lancedb_local_mode.py` — sets
   `EMBED_BACKEND=sentence_transformers`, runs
   `junior_cycle_embedding` once, and asserts the LanceDB table
   exists at `data/lancedb/gemini_hackathon.lance`.
3. `tests/baml/test_extract_chain_offline.py` — sets
   `BAML_TEST_MODE=true`, runs `lc6_extraction_app` for
   `mathematics/en`, and asserts the SQLite output has ≥1 row.

When the optional deps (`lancedb`, `sentence-transformers`) are not
installed, the corresponding test SHALL be skipped with a clear
pytest skip message — not fail.

#### Scenario: `pytest -m integration` shows 3 passed

- **WHEN** the user runs `pytest -m integration tests/` on a fresh clone
- **THEN** the command SHALL show 3 passed tests (1 per data-plane surface)
- **AND** the new tests SHALL be additive — they SHALL NOT modify the 354 Phase 0 baseline tests

### Requirement: `docs/LOCAL_DEV.md` SHALL document the Local data plane section
The system SHALL meet the requirement: `docs/LOCAL_DEV.md` SHALL document the Local data plane section.

The `docs/LOCAL_DEV.md` SHALL contain a "Local data plane" section
that documents the 3 data-plane caveats (DuckDB, LanceDB, BAML
offline) and the 3 `make` targets (`dlt-smoke-all`,
`cocoindex-update`, `ncce-extract`) operators use to verify the
pipeline end-to-end.

#### Scenario: `docs/LOCAL_DEV.md` is the canonical reference

- **WHEN** an operator clones the repo + wants to verify the data plane
- **THEN** the operator SHALL be able to follow `docs/LOCAL_DEV.md` end-to-end
- **AND** the "Local data plane" section SHALL cross-link `KNOWN_ISSUES.md` for any documented gaps

### Requirement: `KNOWN_ISSUES.md` SHALL be the canonical gap log
The system SHALL meet the requirement: `KNOWN_ISSUES.md` SHALL be the canonical gap log.

The `KNOWN_ISSUES.md` SHALL document 3 gaps surfaced during Phase 1:

1. The per-LC cache at `data/ireland/leaving_certificate/<subject>/<lang>/`
   was never populated — only the `data/ireland/ncca_policy/` corpus
   exists. The `official_doc_fetcher` scans the per-LC cache and
   finds nothing, so `data/ireland/leaving_certificate/` only contains
   a stub `README.md`.
2. The local `LANGFUSE_HOST` env var defaults to `https://cloud.langfuse.com`
   (the cloud route) — operators who run `docker compose up` need
   to set `LANGFUSE_HOST=http://langfuse-web:3000` to point at the
   local Langfuse v3 service.
3. The LanceDB path `data/lancedb/gemini_hackathon.lance/` is
   gitignored — only `data/lancedb/.gitkeep` is committed.

#### Scenario: `KNOWN_ISSUES.md` exists and is non-empty

- **WHEN** an operator encounters an unexpected behaviour in the data plane
- **THEN** `KNOWN_ISSUES.md` SHALL exist at the repo root
- **AND** SHALL document at least the 3 Phase 1 gaps above

