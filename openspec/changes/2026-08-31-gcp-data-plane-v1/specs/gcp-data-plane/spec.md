# Spec Delta: gcp-data-plane (Phase 2 — GCP data plane destinations)

This delta is applied by the OpenSpec change
[`2026-08-31-gcp-data-plane-v1`](../proposal.md). It describes the
**ADDED** Requirements to the canonical `gcp-data-plane` capability
that this change introduces.

## ADDED Requirements

### Requirement: `get_destination()` SHALL support 4 DLT backends
The system SHALL meet the requirement: `get_destination()` SHALL support 4 DLT backends.

The `dlt_pipelines._shared.get_destination()` factory SHALL accept a
`name` argument selecting one of 4 backends:

1. `duckdb` — local DuckDB file (the dev default; offline-safe).
2. `ducklake` — DuckLake-backed DuckDB (Phase 3 wires the real
   catalog; Phase 2 keeps the local DuckDB fallback).
3. `motherduck` — MotherDuck cloud (deferred; Phase 2 returns the
   local DuckDB fallback).
4. `bigquery` — Google Cloud BigQuery via
   `dlt.destinations.bigquery(dataset_name=...)`.

The `bigquery` branch SHALL read the dataset name from the
`bigquery_dataset` argument (preferred) or the `BIGQUERY_DATASET` env
var (default `"biep"`). The legacy `get_duckdb_destination()` SHALL
remain as a thin wrapper for backwards compat — every existing
caller SHALL continue to work without modification.

#### Scenario: `get_destination("bigquery", bigquery_dataset="test_biep")`

- **WHEN** the user calls `get_destination("bigquery", bigquery_dataset="test_biep")`
- **THEN** the factory SHALL return `dlt.destinations.bigquery(dataset_name="test_biep")` (mocked in unit tests)
- **AND** the factory SHALL NOT touch the local filesystem

#### Scenario: `get_destination("duckdb")` is the dev default

- **WHEN** the user calls `get_destination("duckdb")` with no args
- **THEN** the factory SHALL return a DuckDB destination pointing at `gemini_hackathon.duckdb` (per Phase 1)
- **AND** the parent directory SHALL be created if missing

### Requirement: Vertex AI Vector Search SHALL be selectable via `VECTOR_BACKEND=vertex`
The system SHALL meet the requirement: Vertex AI Vector Search SHALL be selectable via `VECTOR_BACKEND=vertex`.

The `cocoindex_flows._shared._vector_target.VertexVectorSearchTarget`
class SHALL wrap `google.cloud.aiplatform.MatchingEngineIndex` and
expose 3 sync methods: `upsert(key, vector, metadata=None)`,
`find_nearest(query_vector, k=10, distance_strategy="COSINE")`, and
`delete(key)`. All 3 SHALL be wrapped in `try/except ImportError` for
`google.cloud.aiplatform` — the package SHALL remain importable
without GCP deps installed (returning empty results from stub mode).

Env vars (read at construction time):

- `VERTEX_VECTOR_SEARCH_INDEX` — index display name (default `"gemini-hackathon-index"`)
- `VERTEX_VECTOR_SEARCH_ENDPOINT` — endpoint display name (default `"gemini-hackathon-endpoint"`)
- `VERTEX_VECTOR_SEARCH_DEPLOYED_INDEX_ID` — deployed index ID
- `VERTEX_VECTOR_SEARCH_DIMENSIONS` — vector dimensions (default 768)
- `VERTEX_VECTOR_SEARCH_REGION` — GCP region (default `"europe-west1"`)

#### Scenario: `VECTOR_BACKEND=vertex` selects the Vertex target

- **WHEN** the user calls `get_vector_target(backend="vertex")` with `google-cloud-aiplatform` installed
- **THEN** the factory SHALL return a `VertexVectorSearchTarget` instance
- **AND** the instance SHALL be backed by `aiplatform.MatchingEngineIndex(index_id)` + `MatchingEngineIndexEndpoint(endpoint_id)`

#### Scenario: `google-cloud-aiplatform` not installed

- **WHEN** `google-cloud-aiplatform` is not in the Python environment
- **THEN** the constructor SHALL log a warning and return a stub instance
- **AND** all 3 methods (`upsert`, `find_nearest`, `delete`) SHALL return their documented empty values (0 / [] / None)

### Requirement: `VECTOR_TARGET_DUAL_WRITE=1` SHALL fan out writes to both Firestore and Vertex
The system SHALL meet the requirement: `VECTOR_TARGET_DUAL_WRITE=1` SHALL fan out writes to both Firestore and Vertex.

The `DualWriteTarget` composite class SHALL accept multiple
`VectorTarget` backends and fan out every `upsert(key, vector,
metadata=None)` and `delete(key)` call to all of them. Reads via
`find_nearest(query_vector, k=10)` SHALL be served by the **primary**
target only (the first target passed to the constructor, or the
explicit `primary=` kwarg).

Failure semantics:

- `upsert`: if every target fails, `DualWriteTarget` SHALL raise
  `RuntimeError("All dual-write targets failed: [...]")`. If at
  least one succeeds, the errors from the others SHALL be collected
  and returned (caller decides whether to log).
- `delete`: best-effort — failures are silently logged (deletes
  must not abort a CocoIndex ingest run).

`get_vector_target()` SHALL return
`DualWriteTarget(FirestoreVectorTarget(), VertexVectorSearchTarget())`
when `VECTOR_TARGET_DUAL_WRITE=1`. The env var SHALL be read at
construction time, not per-call.

#### Scenario: dual-write fans out to both targets

- **WHEN** the user calls `dual.upsert("k1", [0.1]*768, {"src": "test"})`
- **THEN** both `FirestoreVectorTarget` and `VertexVectorSearchTarget` SHALL receive the call
- **AND** `dual.find_nearest([0.1]*768, k=5)` SHALL hit only the primary (Firestore)

#### Scenario: all dual-write targets fail

- **WHEN** every target in `DualWriteTarget` raises on `upsert`
- **THEN** `DualWriteTarget` SHALL raise `RuntimeError("All dual-write targets failed: ...")`
- **AND** the error message SHALL include the type name + error message of every failed target

### Requirement: GCS substrate SHALL be opt-in via `GCS_RAW_BUCKET`
The system SHALL meet the requirement: GCS substrate SHALL be opt-in via `GCS_RAW_BUCKET`.

The `dlt_pipelines.corpus_downloader._write_bytes()` and
`dlt_pipelines.pdf_downloader` functions SHALL write to
`gs://<bucket>/<source_key>/<subject>/<lang>/<sha256>.pdf` when the
`GCS_RAW_BUCKET` env var is set. When unset, the functions SHALL
fall back to local
`data/bi_ep/syllabi_raw/<source_key>/<subject>/<lang>/<sha256>.pdf`.

The GCS upload path SHALL use
`google.cloud.storage.Client().bucket(bucket).blob(rel).upload_from_filename(local_path)`
and SHALL wrap the import in `try/except ImportError` so the package
remains importable without `google-cloud-storage` installed.

#### Scenario: `GCS_RAW_BUCKET=test-bucket` returns a `gs://` URI

- **WHEN** the user calls the helper with `GCS_RAW_BUCKET=test-bucket`
- **THEN** the returned path SHALL start with `gs://test-bucket/`
- **AND** the `google.cloud.storage.Client` SHALL be constructed and called exactly once

#### Scenario: `GCS_RAW_BUCKET` unset falls back to local

- **WHEN** the user calls the helper without `GCS_RAW_BUCKET` set
- **THEN** the `google.cloud.storage.Client` SHALL NOT be constructed
- **AND** the returned path SHALL be a local `Path` under `data/bi_ep/syllabi_raw/`

### Requirement: GCP dependencies SHALL be opt-in via `[dependency-groups] gcp`
The system SHALL meet the requirement: GCP dependencies SHALL be opt-in via `[dependency-groups] gcp`.

The `pyproject.toml` SHALL declare a new `[dependency-groups] gcp`
group containing `google-cloud-bigquery>=3.0`,
`google-cloud-aiplatform>=1.50`, `google-cloud-storage>=2.10`. The
group SHALL be commented: "Install with `uv sync --group gcp` for the
GCP-backed data plane; the default install is local-only (DuckDB +
LanceDB)."

The group's deps SHALL NOT be in `default-groups` in
`[tool.uv]`, so `uv sync` without `--group gcp` continues to
install a fully-offline-capable repo.

#### Scenario: `uv sync` without `--group gcp`

- **WHEN** the user runs `uv sync` without `--group gcp`
- **THEN** the project SHALL install successfully
- **AND** `python -c "from gemini_hackathon.model_registry import MODEL_REGISTRY"` SHALL exit 0
- **AND** `python -c "from google.cloud import bigquery"` SHALL fail with `ModuleNotFoundError`

#### Scenario: `uv sync --group gcp`

- **WHEN** the user runs `uv sync --group gcp`
- **THEN** the 3 GCP deps SHALL be installed
- **AND** `python -c "from google.cloud import bigquery, aiplatform, storage"` SHALL exit 0
