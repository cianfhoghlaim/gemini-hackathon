# Spec Delta: dlt-pipelines-uk-ncce (Phase 1 — DLT substrate for NCCE PDFs)

This delta is applied by the OpenSpec change
[`2026-08-31-uk-ncce-learning-graph-showcase-v1`](../proposal.md). It describes the
**ADDED** Requirements to the canonical `dlt-pipelines` capability
that this change introduces.

## ADDED Requirements

### Requirement: `JURISDICTION_BOARDS` SHALL include `uk_ncce` as the 9th British Isles jurisdiction

The `dlt_pipelines/_shared.py` `JURISDICTION_BOARDS` mapping SHALL add a
new entry:

```
"uk_ncce": {
    "name": "United Kingdom (NCCE)",
    "country": "UK",
    "awarding_body": "NCCE",
    "covers": ["England", "Wales", "Northern Ireland", "Isle of Man"],
    "curriculum_source": "https://teachcomputing.org/curriculum",
    "s3_bucket": "ncce-curriculum-production.s3.eu-west-1.amazonaws.com",
    "priority_subjects": [
        "computer_science",
        "mathematics",
        "english",
        "gaeilge",  # cross-walked via the NCCA Gaeilge LC curriculum
        "chemistry",
        "geography",
    ],
}
```

#### Scenario: JURISDICTION_BOARDS is well-formed

- **WHEN** `python -c "from dlt_pipelines._shared import JURISDICTION_BOARDS; assert 'uk_ncce' in JURISDICTION_BOARDS"` is run
- **THEN** the command SHALL exit 0
- **AND** the `uk_ncce` entry SHALL have all 6 required keys

### Requirement: `dlt_pipelines/uk_ncce_learning_graphs.py` SHALL emit 11 rows into `official_documents`

The new module SHALL expose one `@dlt.resource` that yields 11 rows:

- 5 PDF rows for the NCCE artefacts:
  - `learning_graph_intro_to_python_programming_y8.pdf` (year=8, subject=computer_science, kind=learning_graph)
  - `learning_graph_programming_essentials_in_scratch_parts_i_ii_y7.pdf` (year=7, subject=computer_science, kind=learning_graph)
  - `learning_graph_variables_in_games_y6.pdf` (year=6, subject=computer_science, kind=learning_graph)
  - `pedagogy_principles.pdf` (year=null, subject=null, kind=pedagogy_principles)
  - `curriculum_journey_full_2024_2025.pdf` (year=range(7,12), subject=computer_science, kind=curriculum_journey)
- 6 per-subject rows that point at the same 5 PDFs but tagged with each priority subject (so the per-subject extractors can find their source)

#### Scenario: DLT pipeline runs idempotently

- **WHEN** `python -m dlt_pipelines.uk_ncce_learning_graphs` is run twice
- **THEN** the first run SHALL emit 11 new rows
- **AND** the second run SHALL emit 0 new rows (sha256 dedup)

#### Scenario: All 11 rows have valid OFFICIAL_DOC_COLUMNS

- **WHEN** the rows are persisted
- **THEN** every row SHALL have all 12 `OFFICIAL_DOC_COLUMNS` populated (source_key, source_name, jurisdiction, level, language, subject, pdf_path, file_size_bytes, page_count, sha256_hash, source_kind, fetched_at)

### Requirement: `data/bi_ep/syllabi_raw/uk_ncce/curriculum/` SHALL contain 5 sha256-verified PDFs

The directory SHALL contain 5 PDFs lifted from the NCCE source + 1
`INDEX.yaml` that records sha256 checksums for each.

#### Scenario: INDEX.yaml verifies

- **WHEN** `python -c "import yaml, hashlib; ..."` (the INDEX verifier) is run
- **THEN** all 5 PDFs SHALL match their declared sha256
- **AND** the command SHALL exit 0

#### Scenario: 4 PDFs are verbatim copies of the leabharlann source

- **WHEN** `diff <(sha256sum leabharlann/.../pgce/syllabus/learning_graph_intro_to_python_programming_y8.pdf) <(sha256sum data/bi_ep/syllabi_raw/uk_ncce/curriculum/learning_graph_intro_to_python_programming_y8.pdf)` is run
- **THEN** the diff SHALL be empty (bytes-identical)