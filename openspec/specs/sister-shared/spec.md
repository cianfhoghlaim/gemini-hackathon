# sister-shared Specification

## Purpose
TBD - created by archiving change 2026-09-13-gemini-hackathon-sister-umbrella-v1. Update Purpose after archive.

## Requirements

### Requirement: gemini_hackathon uses `baml_src -> baml_extracts` symlink

The gemini_hackathon repo SHALL carry a `baml_src` symlink pointing
to the canonical `baml_extracts/` directory (NOT a copy).

#### Scenario: baml_src is a symlink

- **WHEN** an operator runs `ls -la /Users/cianmacandeisigh/dev/gemini_hackathon/baml_src`
- **THEN** the output MUST show `baml_src -> baml_extracts` (NOT a regular directory)

### Requirement: gemini_hackathon uses `dlt_pipelines/` not `dlt_sources/`

The gemini_hackathon repo SHALL carry DLT pipelines under
`dlt_pipelines/` (NOT `dlt_sources/`).

#### Scenario: dlt_sources is absent

- **WHEN** an operator runs `ls /Users/cianmacandeisigh/dev/gemini_hackathon/dlt_sources`
- **THEN** the output MUST be `No such file or directory`
- **AND** `ls /Users/cianmacandeisigh/dev/gemini_hackathon/dlt_pipelines` MUST return ≥10 entries

### Requirement: gemini_hackathon owns 6 sister-specific HF Spaces

The gemini_hackathon repo SHALL own 6 Hugging Face Spaces at
`hf_spaces/gemini_hackathon_<stage>/` (aistear, bunscoil,
junior_cycle, leaving_certificate, editorial_studio,
learning_graphs).

#### Scenario: 6 HF Space subdirs exist

- **WHEN** an operator runs `ls /Users/cianmacandeisigh/dev/gemini_hackathon/hf_spaces/`
- **THEN** the output MUST list exactly 6 directories prefixed with `gemini_hackathon_`

### Requirement: gemini_hackathon uses GCP-first IaC (cloud/terraform/)

The gemini_hackathon repo SHALL use the GCP-first IaC surface at
`cloud/terraform/` (Cloud Run + BigQuery + BigLake Iceberg +
Workload Identity Federation + Secret Manager).

#### Scenario: cloud/terraform/ is the canonical IaC surface

- **WHEN** an operator runs `ls /Users/cianmacandeisigh/dev/gemini_hackathon/cloud/terraform/modules/`
- **THEN** the output MUST list ≥12 Terraform module directories
- **AND** the repo SHALL NOT contain a top-level `bonneagar/stacks/` directory

### Requirement: gemini_hackathon ships a standalone MODEL_REGISTRY

The gemini_hackathon repo SHALL carry a standalone
`gemini_hackathon/model_registry.py` (a trimmed port of
`meaisinfhoghlaim/models/model_registry.py`) covering at minimum
the `text_llm`, `ocr_vision`, `image_gen`, and `learning_graph`
families.

#### Scenario: MODEL_REGISTRY is queryable

- **WHEN** an operator runs `uv run python -c "from gemini_hackathon.model_registry import MODEL_REGISTRY; print(len(MODEL_REGISTRY))"`
- **THEN** the output MUST be `>= 30` entries
- **AND** MUST include the 9 M3 chokepoint aliases (minimax-m3, kimi-k2.6, glm-5.1, minimax-m2.5, mimo-v2.5, deepseek-v4-flash, deepseek-v4-pro, kimi-k2.7-code, kimi-k3)
