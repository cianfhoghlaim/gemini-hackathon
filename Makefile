# ============================================================================
# gemini-hackathon — common dev tasks.
# Run `make help` for the full list.
#
# Note: the canonical task runner is mise.toml (see `mise tasks`).
# This Makefile mirrors those tasks for users who prefer GNU make.
# Every recipe calls into uv, so the toolchain is identical to `mise run`.
# ============================================================================

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

UV ?= uv
PY := $(UV) run python
PYTEST := $(UV) run pytest
RUFF := $(UV) run ruff
MYPY := $(UV) run mypy
BAML := $(UV) run baml-cli

.DEFAULT_GOAL := help
.PHONY: help setup sync install lint format typecheck test test-cov \
        baml-generate baml-test baml-coverage baml-lint run dev down clean \
        docker-build docker-push docs notebook shell

# ----------------------------------------------------------------------------
# Help (auto-generated from the comments above each target)
# ----------------------------------------------------------------------------
help: ## show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\ngemini-hackathon — make targets\n\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@printf "\n"

# ----------------------------------------------------------------------------
# Bootstrap
# ----------------------------------------------------------------------------
setup: ## full bootstrap (uv install + sync + verify) — calls setup.sh
	@./setup.sh

sync: ## uv sync --all-extras
	$(UV) sync --all-extras

install: sync ## alias for sync

# ----------------------------------------------------------------------------
# Lint + format
# ----------------------------------------------------------------------------
lint: ## ruff check (lint only)
	$(RUFF) check .

lint-fix: ## ruff check --fix
	$(RUFF) check . --fix

format: ## ruff format (in-place)
	$(RUFF) format .

format-check: ## ruff format --check (CI mode)
	$(RUFF) format --check .

# ----------------------------------------------------------------------------
# Type check
# ----------------------------------------------------------------------------
typecheck: ## mypy gemini_hackathon/ (strict, dignified-python-312)
	$(BAML) generate
	$(MYPY) gemini_hackathon/

# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------
test: ## pytest tests/ (verbose)
	$(BAML) generate
	$(PYTEST) tests/ -v

test-cov: ## pytest + coverage report
	$(BAML) generate
	$(PYTEST) tests/ -v --cov=gemini_hackathon --cov-report=term-missing --cov-report=xml

test-fast: ## pytest -x --ff (stop on first failure)
	$(PYTEST) tests/ -x --ff

# ----------------------------------------------------------------------------
# BAML
# ----------------------------------------------------------------------------
baml-generate: ## regenerate baml_client/ + web/baml_client/
	$(BAML) generate

baml-test: ## run BAML extraction smoke tests
	$(BAML) generate
	$(BAML) test

baml-coverage: ## BAML test --coverage (per-function pass-rate)
	$(BAML) generate
	$(BAML) test --coverage

baml-lint: ## BAML lint (parser + schema validation)
	$(BAML) lint

# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------
run: ## uv run python -m gemini_hackathon.cli
	$(BAML) generate
	$(PY) -m gemini_hackathon.cli

shell: ## uv run python REPL with the project on PYTHONPATH
	$(PY)

# ----------------------------------------------------------------------------
# Docker
# ----------------------------------------------------------------------------
docker-build: ## docker build -t gemini-hackathon:dev .
	docker build -t gemini-hackathon:dev .

docker-push: ## docker push (uses DOCKERHUB_USER / DOCKERHUB_REPO env vars)
	docker tag gemini-hackathon:dev ${DOCKERHUB_USER:-cianfhoghlaim}/gemini-hackathon:dev
	docker push ${DOCKERHUB_USER:-cianfhoghlaim}/gemini-hackathon:dev

dev: ## docker compose up --build (local stack)
	docker compose up --build

down: ## docker compose down -v (nuclear: wipes the duckdb volume)
	docker compose down -v

# ----------------------------------------------------------------------------
# Docs
# ----------------------------------------------------------------------------
docs: ## export marimo notebooks to site/
	@mkdir -p site
	@if ls notebooks/*.py >/dev/null 2>&1; then \
		for nb in notebooks/*.py; do \
			name=$$(basename "$$nb" .py); \
			echo "Exporting $$nb -> site/$$name.html"; \
			$(UV) run marimo export html --no-show-code --no-include-inputs \
				"$$nb" -o "site/$$name.html"; \
		done; \
	else \
		echo '<!doctype html><title>gemini-hackathon</title>No notebooks yet.' \
			> site/index.html; \
	fi
	@touch site/.nojekyll

notebook: ## launch marimo edit notebooks/ (reactive UI)
	$(UV) run marimo edit notebooks/

# ----------------------------------------------------------------------------
# Cleanup
# ----------------------------------------------------------------------------
clean: ## remove build artefacts + caches
	rm -rf \
		.venv/ \
		.mypy_cache/ \
		.ruff_cache/ \
		.pytest_cache/ \
		.coverage \
		coverage.xml \
		htmlcov/ \
		build/ \
		dist/ \
		*.egg-info/ \
		site/ \
		baml_client/ \
		web/baml_client/
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

clean-data: ## nuke the DuckDB file (DESTRUCTIVE)
	rm -f data/*.duckdb data/*.duckdb.wal