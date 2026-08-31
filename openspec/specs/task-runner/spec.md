# task-runner Specification

## Purpose
TBD - created by archiving change 2026-08-31-replace-mise-with-make-v1. Update Purpose after archive.
## Requirements
### Requirement: `mise.toml` SHALL be deleted from the repo root
The system SHALL meet the requirement: `mise.toml` SHALL be deleted from the repo root.
The repo root SHALL NOT contain a `mise.toml` file. Local development
SHALL be orchestrated via the canonical Google pattern: a self-documenting
`Makefile` + `scripts/dev.sh` + `scripts/verify.sh`. Operators who
previously ran `mise run <task>` SHALL switch to `make <target>` (or direct
`uv run python -m ...` invocations).

#### Scenario: `mise.toml` no longer exists

- **WHEN** `ls mise.toml` is run at the repo root
- **THEN** the command SHALL exit non-zero (file not found)

#### Scenario: No `mise` references remain

- **WHEN** `git grep mise` is run (excluding `.openspec/changes/2026-08-31-replace-mise-with-make-v1/` + `openspec/`)
- **THEN** the command SHALL return 0 matches
- **AND** every remaining reference SHALL be in this OpenSpec change folder or in the deprecated `docs/DEPLOYMENT.md` historical context

### Requirement: `Makefile` SHALL expose the canonical Google `help` target
The system SHALL meet the requirement: `Makefile` SHALL expose the canonical Google `help` target.
The `Makefile` SHALL expose a `help` target that prints every phony
target with its `## description` comment, sorted alphabetically. The
help target SHALL be the default target.

#### Scenario: `make help` prints the table

- **WHEN** `make help` is run
- **THEN** the command SHALL exit 0
- **AND** the output SHALL contain every phony target's name + description
- **AND** the targets SHALL be sorted alphabetically

### Requirement: `Makefile` SHALL expose 25 phony targets covering every local workflow
The system SHALL meet the requirement: `Makefile` SHALL expose 25 phony targets covering every local workflow.
The `Makefile` SHALL expose at minimum these 25 phony targets:

- **Setup**: `install`, `baml`, `setup` (alias for `scripts/dev.sh`)
- **Quality**: `lint`, `format`, `typecheck`, `test`, `verify` (alias for `scripts/verify.sh`)
- **App runners**: `run`, `backend`, `web`, `notebook`, `docs`, `shell`
- **Data plane**: `dlt:smoke-all`, `cocoindex:update`, `ncce:extract`, `ncce:visualise`, `compare:demo`
- **Cloud**: `docker:build`, `dev` (docker compose up), `down` (docker compose down)
- **Hygiene**: `clean`, `help` (the Google `help` target itself)

Each target SHALL be a `.PHONY` target with a `## description` comment.

#### Scenario: `make help` lists all 25 targets

- **WHEN** `make help` is run
- **THEN** the output SHALL list at least 25 target lines
- **AND** every target SHALL have a non-empty `## description` comment

### Requirement: `scripts/dev.sh` SHALL be the one-shot local dev bootstrap
The system SHALL meet the requirement: `scripts/dev.sh` SHALL be the one-shot local dev bootstrap.
The `scripts/dev.sh` script SHALL wrap the canonical Google 5-step local dev recipe: (1) `uv sync --all-extras`, (2) `cp .env.example .env`, (3) `make baml`, (4) `make dev`, (5) verify with `make verify`.

#### Scenario: `scripts/dev.sh` is runnable

- **WHEN** `./scripts/dev.sh` is run on a fresh clone
- **THEN** the script SHALL exit 0 on success
- **AND** every step in the 5-step recipe SHALL be visibly logged

### Requirement: `scripts/verify.sh` SHALL be the 8-tick verify gate
The system SHALL meet the requirement: `scripts/verify.sh` SHALL be the 8-tick verify gate.
The `scripts/verify.sh` script SHALL run 8 verify ticks and print `[OK]` / `[FAIL]` for each:

1. Python imports (every `gemini_hackathon.*` module imports cleanly)
2. BAML client generated + tests pass
3. Lint (ruff check + ruff format --check)
4. Typecheck (mypy gemini_hackathon/)
5. DLT smoke (run `dlt_pipelines.uk_ncce_learning_graphs` + verify 11 rows emitted)
6. CocoIndex smoke (run `cocoindex_flows.uk_ncce.learning_graphs_app` + verify 5 .md files)
7. Gradio imports (every `gemini_hackathon_gradio.*` module imports cleanly)
8. Dagster imports (every `orchestration.defs.3_model_lifecycle.*` module imports cleanly)

The script SHALL exit 0 only when all 8 ticks pass.

#### Scenario: All 8 ticks pass on a clean checkout

- **WHEN** `./scripts/verify.sh` is run after `make install && make baml`
- **THEN** the script SHALL print 8 `[OK]` lines
- **AND** SHALL exit 0

#### Scenario: A failing tick exits non-zero

- **WHEN** any of the 8 ticks fails
- **THEN** the script SHALL print at least 1 `[FAIL]` line
- **AND** SHALL exit non-zero
- **AND** SHALL not abort the remaining ticks (operator sees the full picture)

### Requirement: `docs/LOCAL_DEV.md` SHALL be the step-by-step local dev guide
The system SHALL meet the requirement: `docs/LOCAL_DEV.md` SHALL be the step-by-step local dev guide.
The `docs/LOCAL_DEV.md` SHALL be a ~250-LOC step-by-step guide covering: (1) Install + configure, (2) Bring up the lakehouse + observability stack, (3) Run the data plane (DLT → CocoIndex → BAML), (4) Run the Dagster assets, (5) Launch the Gradio studio + HF Space. It SHALL also include a "Where to find key data + schemas" cheat-sheet and a "What to do when something breaks" section.

#### Scenario: `docs/LOCAL_DEV.md` is the canonical reference

- **WHEN** an operator clones the repo + wants to know how to run things locally
- **THEN** the operator SHALL be able to follow `docs/LOCAL_DEV.md` end-to-end
- **AND** the README §11 "Quick start" SHALL cross-link `docs/LOCAL_DEV.md`

