# polish Specification

## Purpose
TBD - created by archiving change 2026-08-31-phase-6-polish-v1. Update Purpose after archive.
## Requirements
### Requirement: The final test suite SHALL pass
The gemini_hackathon Python test suite MUST pass with ≤3 pre-existing
failures and 0 errors after the Phase 6 polish pass.

#### Scenario: Call LLM tier chain tests pass

- **WHEN** the Phase 6 polish completes `tests/test_call_llm.py`
- **THEN** `uv run pytest tests/test_call_llm.py` SHALL report 0 failures

#### Scenario: DLT pipeline jurisdiction tests pass

- **WHEN** `tests/test_dlt_pipelines.py::test_jurisdiction_boards_has_10_entries` runs
- **THEN** it SHALL assert 11 jurisdictions (Ireland + England + NI + Scotland + Wales + Jersey + Guernsey)

#### Scenario: Babylon export tests removed

- **WHEN** the Phase 6 change is archived
- **THEN** `tests/test_babylon_export.py` SHALL no longer exist

### Requirement: Test coverage SHALL be ≥ 70%
The `gemini_hackathon/` Python package MUST report ≥70% line coverage
as enforced by `pyproject.toml`.

#### Scenario: Coverage threshold met

- **WHEN** `uv run pytest tests/ --cov=gemini_hackathon --cov-report=term` completes
- **THEN** the `TOTAL` line SHALL report `≥ 70%`

### Requirement: Env-var documentation SHALL be complete
Every env-var consumed by the application MUST be declared in
`.env.example` (with a default or with an inline explanation).

#### Scenario: Env-var-completeness test passes

- **WHEN** `tests/test_env_example_completeness.py` scans every Python module under `gemini_hackathon/`
- **THEN** the union of env-var names SHALL be a subset of `.env.example` keys

### Requirement: Secrets catalogue SHALL match `.env.example`
Every env-var name in `.env.example` MUST have a matching entry in
`secrets.yaml` so the GSM catalogue stays in sync with the local env file.

#### Scenario: Secrets catalogue audit passes

- **WHEN** `scripts/audit_gsm.py` runs against the updated `.env.example`
- **THEN** it SHALL report parity between `.env.example` keys and `secrets.yaml` env_var fields

### Requirement: Known issues entries SHALL be tagged
Every line item in `docs/KNOWN_ISSUES.md` MUST be tagged either
`[RESOLVED]` or `[OPEN: Phase X follow-up]`.

#### Scenario: All entries tagged

- **WHEN** `rg '\[(RESOLVED|OPEN:)' docs/KNOWN_ISSUES.md` runs
- **THEN** every row in every table SHALL match either pattern

### Requirement: HuggingFace Space publish Makefile targets SHALL be wired
The `Makefile` MUST expose `hf-publish-<space>` and `hf-publish-all`
targets that wrap `huggingface-cli upload --repo-type space
cianfhoghlaim/<space> .` per `hf_spaces/README.md:27-30`.

#### Scenario: hf-publish-<space> targets each Space

- **WHEN** `make hf-publish-<space>` runs with `<space>` set to any of the 6 known Spaces
- **THEN** the target SHALL upload via `huggingface-cli upload --repo-type space cianfhoghlaim/<space> .`

#### Scenario: hf-publish-all iterates the 6 Spaces

- **WHEN** `make hf-publish-all` runs
- **THEN** the target SHALL iterate the 6 known Spaces and invoke the per-Space target for each

