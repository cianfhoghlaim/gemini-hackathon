# ============================================================================
# gemini-hackathon — the canonical Google project-management Makefile.
#
# This is the ONLY task runner for local dev. Every recipe is a thin
# wrapper around `uv`, `docker compose`, `baml-cli`, or direct
# `python -m` invocations — there is no `mise.toml`, no `task` file,
# no `justfile`, no `lefthook.yml`.
#
# The pattern matches every example in docs/cocoindex_examples/* (the
# official CocoIndex repo) + every project in docs/adk-examples/*:
#   pyproject.toml + .env.example + README.md + Makefile
#
# Usage:
#   make help            # the canonical Google `help` target
#   make                 # alias for `make help`
#   make install         # uv sync --all-groups
#   make baml            # regenerate + test the BAML client
#   make verify          # the 8-tick verify gate (calls scripts/verify.sh)
#   make dev             # docker compose up --build (the local stack)
#   make cloudbuild      # gcloud builds submit --config=cloudbuild.yaml
#
# Adding a new target? Append it below with a `## description` comment
# and run `make help` — the awk-parsed help block picks it up.
# ============================================================================

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

UV       ?= uv
PY       := $(UV) run python
PYTEST   := $(UV) run pytest
RUFF     := $(UV) run ruff
MYPY     := $(UV) run mypy
BAML     := $(UV) run baml-cli
DAGSTER  := $(UV) run dagster
DG       := $(UV) run dg

.DEFAULT_GOAL := help
.PHONY: help
help: ## show this help message (the default target)
	@awk 'BEGIN {FS = ":.*##"; printf "\ngemini-hackathon \xe2\x80\x94 make targets\n\n"} \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' \
		$(MAKEFILE_LIST)
	@printf "\nSee docs/LOCAL_DEV.md for the 5-step local dev recipe.\n\n"

# ============================================================================
# Setup — bootstrap a fresh checkout
# ============================================================================
.PHONY: install baml setup
install: ## uv sync --all-groups (deps + every dependency group)
	$(UV) sync --all-groups

baml: ## regenerate the BAML client + run BAML tests
	$(BAML) generate
	$(BAML) test

setup: ## full bootstrap — uv install + sync + .env + baml + verify
	./scripts/dev.sh

# ============================================================================
# Quality gates — the CI suite (mirrors .github/workflows/ci.yml)
# ============================================================================
.PHONY: lint format typecheck test test-cov verify
lint: ## ruff check + ruff format --check
	$(RUFF) check .
	$(RUFF) format --check .

format: ## ruff format (in-place)
	$(RUFF) format .

typecheck: ## mypy gemini_hackathon/ (strict, dignified-python-312)
	$(BAML) generate
	$(MYPY) gemini_hackathon/

test: ## pytest tests/ -v
	$(BAML) generate
	$(PYTEST) tests/ -v

test-cov: ## pytest + coverage report
	$(BAML) generate
	$(PYTEST) tests/ -v --cov=gemini_hackathon --cov-report=term-missing --cov-report=xml

verify: ## the 8-tick verify gate (calls scripts/verify.sh)
	./scripts/verify.sh

# ============================================================================
# App runners — the surface an operator interacts with
# ============================================================================
.PHONY: run backend web notebook docs shell
run: ## uv run python -m gemini_hackathon.cli (the canonical CLI entry)
	$(BAML) generate
	$(PY) -m gemini_hackathon.cli

backend: ## boot the Python backend on :8000 (FastAPI + ADK 2)
	$(BAML) generate
	$(PY) -m gemini_hackathon.backend

web: ## boot the TanStack Start web surface on :3000
	cd web && bun run dev

notebook: ## launch marimo edit notebooks/ (reactive UI)
	$(UV) run marimo edit notebooks/

docs: ## export marimo notebooks to site/ (for gh-pages deploy)
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

shell: ## drop into a uv-managed Python REPL (project on PYTHONPATH)
	$(PY)

# ============================================================================
# Data plane — DLT pipelines + CocoIndex Apps + NCCE showcase
# ============================================================================
.PHONY: dlt-smoke-all cocoindex-update ncce-extract ncce-visualise compare-demo \
        lift-lc-pdfs extract-ondisk-pdfs \
        llama-swap-download-models
dlt-smoke-all: ## run every DLT pipeline (offline-safe; writes to DuckDB)
	$(PY) -m dlt_pipelines.official_doc_fetcher
	$(PY) -m dlt_pipelines.safeguarding_fetcher
	$(PY) -m dlt_pipelines.uk_ncce_learning_graphs
	$(PY) -m dlt_pipelines.pdf_downloader
	$(PY) -m dlt_pipelines.corpus_downloader

cocoindex-update: ## run every CocoIndex App (offline-safe; writes to local FS)
	$(PY) -m cocoindex_flows.pdf.pdf_to_markdown_app
	$(PY) -m cocoindex_flows.uk_ncce.learning_graphs_app
	$(PY) -m cocoindex_flows.ireland.lc_subject_embedding
	$(PY) -m cocoindex_flows.ireland.junior_cycle_embedding
	$(PY) -m cocoindex_flows.education.lc6_extraction_app
	$(PY) -m cocoindex_flows.equivalency.equivalency_graph_app

ncce-extract: ## run the NCCE DLT + CocoIndex pipeline (the 2026-08-31 batch)
	$(PY) -m dlt_pipelines.uk_ncce_learning_graphs
	$(PY) -m cocoindex_flows.uk_ncce.learning_graphs_app

ncce-visualise: ## launch the 4-tab Gradio studio (Render / Equivalencies / Generate / Pedagogy)
	$(PY) -m gemini_hackathon_gradio.an_learning_graph

compare-demo: ## run the Gemini-vs-Gemma4 comparison harness (writes to DuckDB)
	$(PY) scripts/compare_demo.py

llama-swap-download-models: ## download the 7 active llama-swap GGUFs from HuggingFace (Gemma+Gemini refocus)
	./scripts/llama_swap_download_models.sh

lift-lc-pdfs: ## lift the 134-PDF LC corpus from cianfhoghlaim worktree (Phase 4)
	$(PY) scripts/lift_lc_pdfs.py

extract-ondisk-pdfs: ## extract structured BAML data from the 10 on-disk PDFs (writes to extracted_syllabi.sqlite)
	$(PY) scripts/extract_ondisk_pdfs.py

# ============================================================================
# Cloud — Cloud Run + Cloud Build + Hugging Face
# ============================================================================
.PHONY: docker-build dev down cloudbuild hf-publish hf-publish-aistear \
        hf-publish-bunscoil hf-publish-junior-cycle hf-publish-leaving-certificate \
        hf-publish-learning-graphs hf-publish-editorial-studio hf-publish-all
docker-build: ## docker build -t gemini-hackathon:dev .
	docker build -t gemini-hackathon:dev .

dev: ## docker compose up --build (the local stack: backend + lakehouse + observability)
	docker compose up --build

down: ## docker compose down -v (nuclear: wipes the duckdb volume)
	docker compose down -v

cloudbuild: ## gcloud builds submit --config=cloudbuild.yaml (the prod deploy)
	gcloud builds submit --config=cloudbuild.yaml --project=$$GCP_PROJECT

# ============================================================================
# HuggingFace Space publish — per-Space recipes (wired 2026-08-31 Phase 6)
# ============================================================================
# Updated 2026-08-31 (Phase 6): the 6 hf-publish-<space> targets wrap
# `huggingface-cli upload --repo-type space cianfhoghlaim/<space> .` per
# `hf_spaces/README.md:27-30`. `hf-publish-all` iterates the 6 known Spaces.
# Requires `huggingface-cli login` to have been run (no HF credentials in dev).
#
# Usage:
#   make hf-publish-<space>      # publish one Space (e.g. hf-publish-aistear)
#   make hf-publish-all           # publish all 6
#
# The Spaces (in shipping order):
#   1. aistear              — Early childhood (Aistear)
#   2. bunscoil             — Primary school (Bunscoil)
#   3. junior-cycle         — Junior Cycle (NCCA)
#   4. leaving-certificate  — Leaving Certificate (NCCA)
#   5. learning-graphs      — Cross-subject learning graphs (NCCE)
#   6. editorial-studio     — Cloud Run editorial studio
HF ?= huggingface-cli
HF_OWNER := cianfhoghlaim

hf-publish-aistear:             ## publish the Aistear HF Space
	cd hf_spaces/gemini_hackathon_aistear && $(HF) upload $(HF_OWNER)/gemini_hackathon_aistear . --repo-type space

hf-publish-bunscoil:            ## publish the Bunscoil HF Space
	cd hf_spaces/gemini_hackathon_bunscoil && $(HF) upload $(HF_OWNER)/gemini_hackathon_bunscoil . --repo-type space

hf-publish-junior-cycle:        ## publish the Junior Cycle HF Space
	cd hf_spaces/gemini_hackathon_junior_cycle && $(HF) upload $(HF_OWNER)/gemini_hackathon_junior_cycle . --repo-type space

hf-publish-leaving-certificate: ## publish the Leaving Certificate HF Space
	cd hf_spaces/gemini_hackathon_leaving_certificate && $(HF) upload $(HF_OWNER)/gemini_hackathon_leaving_certificate . --repo-type space

hf-publish-learning-graphs:     ## publish the Learning Graphs HF Space
	cd hf_spaces/gemini_hackathon_learning_graphs && $(HF) upload $(HF_OWNER)/gemini_hackathon_learning_graphs . --repo-type space

hf-publish-editorial-studio:    ## publish the Editorial Studio HF Space
	cd hf_spaces/gemini_hackathon_editorial_studio && $(HF) upload $(HF_OWNER)/gemini_hackathon_editorial_studio . --repo-type space

hf-publish-all:                  ## publish all 6 HF Spaces in shipping order
	@set -e; \
	for space in aistear bunscoil junior_cycle leaving_certificate learning_graphs editorial_studio; do \
		echo "--- $$space ---"; \
		$(MAKE) hf-publish-$$space; \
	done

hf-publish: ## regenerate + push the 6 HF Spaces mirrors (alias for hf-publish-all)
	make hf-publish-all

# ============================================================================
# Hygiene — nuke caches + build artefacts
# ============================================================================
.PHONY: clean clean-data
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
		site/
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

clean-data: ## nuke the DuckDB file (DESTRUCTIVE)
	rm -f data/*.duckdb data/*.duckdb.wal