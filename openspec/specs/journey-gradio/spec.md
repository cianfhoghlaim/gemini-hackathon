# journey-gradio Specification

## Purpose
TBD - created by archiving change 2026-08-31-journey-gradio-polish-v1. Update Purpose after archive.
## Requirements
### Requirement: The 4 remaining Gradio studios SHALL wire to their canonical pipelines (no Markdown stubs)

The 4 Gradio studios in `gemini_hackathon_gradio/` SHALL wire every tab
to a real operator that calls into the canonical platform pipelines:

- `editorial_studio` — `CertificatePipeline.run()` from
  `gemini_hackathon/certificate/pipeline.py:87` (the 7-stage pipeline)
- `anam_education` — `BAMLSyllabusExtractor.extract()` from
  `gemini_hackathon/syllabus/baml_extractor.py:30`
- `oideachais_mission_control` — `MODEL_REGISTRY._entries` +
  `raw.official_documents` from DuckDB
- `oideachais_pdf_review` — `BAMLSyllabusExtractor.extract()` + the
  `@spaces.GPU`-decorated handler pattern

#### Scenario: each studio's `build_app()` returns a non-None `gr.Blocks`

- **WHEN** `from gemini_hackathon_gradio import <studio>` is imported and
  `<studio>.build_app()` is called
- **THEN** the function SHALL return a non-None `gr.Blocks` instance
- **AND** every tab SHALL contain at least one operator component (not
  only `gr.Markdown`)

### Requirement: Each polished studio SHALL honour `BAML_TEST_MODE=true`

The system SHALL honour the `BAML_TEST_MODE=true` env var in the
BAML-calling tabs of `editorial_studio` + `anam_education` +
`oideachais_pdf_review`. When set, the tabs SHALL use the BAML
`TestMock` client (already wired in `baml_extracts/clients.baml`) so the
workshop demo runs offline.

#### Scenario: `BAML_TEST_MODE=true uv run python -c "from gemini_hackathon_gradio import editorial_studio; editorial_studio.build_app()"`

- **WHEN** the env var `BAML_TEST_MODE=true` is set
- **THEN** the studio's `build_app()` SHALL succeed without a network call
- **AND** the BAML-calling tab operators SHALL use the test-mock client

### Requirement: Journey sourcing duplication SHALL be eliminated

The system SHALL eliminate the `journey/sourcing/sourcing/` outer
duplicate (Phase 3 scope creep). The canonical
`gemini_hackathon/journey/sourcing/` (with the `_shared_fs()` singleton
pattern) SHALL remain as the single source of truth.

#### Scenario: `test -d journey/sourcing/sourcing` returns false

- **WHEN** this change is deployed
- **THEN** `test -d journey/sourcing/sourcing` SHALL return false
- **AND** `grep -rE "from journey.sourcing.sourcing" --include="*.py" .` SHALL return 0 hits

### Requirement: The SourcingCopilot SHALL have a tests package

A `journey/sourcing_copilot_tests/` package SHALL exist with at least
two test files (`test_tools.py` + `test_agent.py`). The tests SHALL
exercise the 7 canonical tools + the agent's tool-binding loop, using
`BAML_TEST_MODE=true` + the in-memory Firestore fallback so no GCP
creds are required.

#### Scenario: `uv run pytest journey/sourcing_copilot_tests/`

- **WHEN** the test suite is run with `BAML_TEST_MODE=true`
- **THEN** all tests SHALL pass (zero failures)
- **AND** no GCP / network access SHALL be required

