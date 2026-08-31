# 2026-08-31-gcp-data-plane-v1

> **Phase 2 of the gemini_hackathon polish plan.** Adds the
> GCP-native data-plane destinations alongside the local DuckDB +
> LanceDB stack wired in Phase 1 (`2026-08-31-local-data-plane-v1`).
> Production targets: **BigQuery** (DLT destination) +
> **Vertex AI Vector Search** (CocoIndex vector target) +
> **GCS** (PDF corpus substrate). The local stack remains the
> dev/test fallback. All GCP deps are opt-in via the new
> `[dependency-groups] gcp` group, so `uv sync` without `--group gcp`
> continues to install a fully-offline-capable repo.

Phase 0 (`603637c` + `d7d0f3e`) fixed import-breaking bugs and
unblocked `uv sync --all-extras`. Phase 1 (`d1ef175`) wired the
local data plane end-to-end (DLT → DuckDB → CocoIndex → LanceDB →
BAML). This change adds the production GCP data-plane **alongside**
the local one — keeping the dev path offline-safe while letting the
deployed Cloud Run path talk to BigQuery + Vertex AI Vector Search +
GCS without code changes.

## Why

The hackathon rules require **"at least one Google Cloud
infrastructure service"**. Per Phase 1 the Firestore/Vertex route
satisfies that at the *agent* layer (Vertex AI embeddings +
Memory Bank). But the *data* layer — where the 46 NCCA + 19
safeguarding + 95 remote-URL rows actually live — has no GCP path
yet. Every Cloud Run deployment today writes to a local DuckDB
file that doesn't survive a cold start, and every CocoIndex App
writes to a `gemini_hackathon.lance/` directory that has no
production equivalent. The 3 GCP services that close the gap:

1. **BigQuery** — replaces the dev DuckDB file in the deployed
   path. Wired via `dlt.destinations.bigquery()`; selected by
   `BIGQUERY_DATASET` env var (default `"biep"`).
2. **Vertex AI Vector Search** — replaces the dev LanceDB file
   for CocoIndex Apps. Wired via `aiplatform.MatchingEngineIndex`;
   selected by `VECTOR_BACKEND=vertex` (default remains Firestore
   for zero standing infra).
3. **GCS** — replaces the dev `data/bi_ep/syllabi_raw/` directory
   for the PDF corpus. Wired via `google.cloud.storage`; selected
   by `GCS_RAW_BUCKET` env var.

Concrete observability gap this closes: a fresh `uv sync` +
`make dlt-smoke-all` still writes to a local DuckDB file (the dev
default), but `BIGQUERY_DATASET=biep GOOGLE_CLOUD_PROJECT=... uv
run python -m dlt_pipelines.official_doc_fetcher` will now write
to BigQuery instead. Same code path, different destination — the
exact polymorphic factory pattern Phase 1 documented but did not
implement.

## What changes

### Phase 0 — OpenSpec change folder (this commit)

- [x] T0.1: `openspec/changes/2026-08-31-gcp-data-plane-v1/proposal.md` (this file)
- [x] T0.2: `openspec/changes/.../specs/gcp-data-plane/spec.md` (1 spec delta)
- [x] T0.3: `openspec/changes/.../tasks.md`
- [x] T0.4: `openspec validate 2026-08-31-gcp-data-plane-v1 --strict` passes

### Phase 1 — BigQuery DLT destination (sub-task 2.1)

- [x] T1.1: `dlt_pipelines/_shared.py` gains `get_destination(name, database_path, bigquery_dataset)`
      — the polymorphic 4-backend factory (`duckdb` / `ducklake` /
      `motherduck` / `bigquery`). The old
      `get_duckdb_destination(database_path)` is kept as a thin
      wrapper for backwards compat.
- [x] T1.2: `bigquery` branch returns
      `dlt.destinations.bigquery(dataset_name=bigquery_dataset or "biep")`
      with a `try/except ImportError` guard around the `dlt.destinations`
      import — the package stays installable without `dlt[bigquery]`
      extras.
- [x] T1.3: `tests/dlt/test_bigquery_destination.py` mocks
      `dlt.destinations.bigquery` and asserts the factory passes
      the right kwargs.

### Phase 2 — Vertex AI Vector Search target (sub-task 2.2)

- [x] T2.1: `cocoindex_flows/_shared/_vector_target.py`'s
      `VertexVectorSearchTarget` is completed with
      `upsert_batch`, `find_nearest`, `delete` methods wrapping
      `aiplatform.MatchingEngineIndex` (note: the existing class
      already has `upsert_batch` / `find_nearest` — Phase 2 adds
      `delete` and a synchronous `upsert`/`find_nearest` shim
      per the task spec).
- [x] T2.2: All methods wrapped in `try/except ImportError` for
      `google.cloud.aiplatform` — the package stays importable
      without GCP deps installed.
- [x] T2.3: `tests/cocoindex/test_vertex_target.py` mocks
      `google.cloud.aiplatform.MatchingEngineIndex` and
      `IndexEndpoint` and asserts the 4 methods wire correctly.

### Phase 3 — Dual-write capability (sub-task 2.3)

- [x] T3.1: New `DualWriteTarget` composite class in
      `_vector_target.py` — fans out `upsert`/`delete` to multiple
      backends, reads from the primary, raises
      `RuntimeError("All dual-write targets failed: ...")` when
      every backend fails.
- [x] T3.2: `get_vector_target()` returns
      `DualWriteTarget(FirestoreVectorTarget(),
      VertexVectorSearchTarget())` when
      `VECTOR_TARGET_DUAL_WRITE=1` (read at construction time).
- [x] T3.3: `tests/cocoindex/test_dual_write_target.py` verifies
      both targets receive `upsert`, only the primary is queried,
      and the all-failed error is raised correctly.

### Phase 4 — GCS substrate for PDF corpus (sub-task 2.4)

- [x] T4.1: New `_output_path()` helper in
      `dlt_pipelines/corpus_downloader.py` + `pdf_downloader.py` —
      returns `gs://<bucket>/<key>` when `GCS_RAW_BUCKET` is set,
      local `data/bi_ep/syllabi_raw/...` otherwise.
- [x] T4.2: GCS upload path uses
      `google.cloud.storage.Client().bucket(bucket).blob(rel).
      upload_from_filename(local_path)`; falls back to local with a
      warning when `google-cloud-storage` isn't installed.
- [x] T4.3: `tests/dlt/test_gcs_substrate.py` mocks
      `google.cloud.storage.Client` and asserts the returned path
      starts with `gs://test-bucket/` when the env var is set, and
      the client is NOT called when unset.

### Phase 5 — Lazy import guards + new `[dependency-groups] gcp` (sub-task 2.5)

- [x] T5.1: New `[dependency-groups] gcp` group in `pyproject.toml`
      holding `google-cloud-bigquery>=3.0`,
      `google-cloud-aiplatform>=1.50`, `google-cloud-storage>=2.10`.
- [x] T5.2: `dlt[bigquery]` extra + the 3 GCP deps currently in
      `[project.dependencies]` stay (the GCP-first IaC refactor
      already declared them as required for the deployed path). The
      new optional group documents the **recommended** install
      shape (`uv sync --group gcp`) and the offline-safe default
      (`uv sync` only — Phase 1's local-data-plane path).
- [x] T5.3: Comment block above the new group documents: "Install
      with `uv sync --group gcp` for the GCP-backed data plane; the
      default install is local-only (DuckDB + LanceDB)."

### Phase 6 — Notebook 12 demo cell (sub-task 2.6)

- [x] T6.1: Add a new code cell at the end of
      `notebooks/12_learning_graph_equivalency_walkthrough.ipynb`
      that demos the Vertex AI Vector Search path with
      `backend="vertex"` and prints the backend type + `is_stub`
      flag.
- [x] T6.2: Execute the notebook via
      `jupyter nbconvert --to notebook --execute --inplace` so the
      cell's outputs are persisted.

### Phase 7 — Docs + tests + commit + archive

- [x] T7.1: `docs/MODEL_POLICY.md` gains a new "Vertex AI Vector
      Search cost considerations" section after the Tier 1 cost
      ceiling discussion.
- [x] T7.2: `docs/KNOWN_ISSUES.md` gains 2 Phase 2 gap entries
      (Vertex AI Vector Search cold-start latency + the
      `[dependency-groups] gcp` opt-in shape).
- [x] T7.3: 4 new test files under `tests/{dlt,cocoindex}/` —
      `test_bigquery_destination.py`,
      `test_vertex_target.py`, `test_dual_write_target.py`,
      `test_gcs_substrate.py`. Each is
      `@pytest.mark.integration` (skipped in CI without GCP creds)
      or fully mocked.
- [x] T7.4: `pytest tests/` shows ≥358 + 4 = ≥362 passed
- [x] T7.5: `bash scripts/verify.sh` stays 6/8 (Phase 1 baseline;
      ticks 3 ruff + 4 mypy out of scope)
- [x] T7.6: commit `feat(phase-2): add GCP data plane — BigQuery
      + Vertex AI Vector Search + GCS substrate` (NO push)
- [x] T7.7: `openspec archive 2026-08-31-gcp-data-plane-v1` after commit

## Acceptance

- `uv run python -c "from gemini_hackathon.dlt_pipelines._shared import get_destination; print('OK')"` exits 0
- `uv run python -c "from cocoindex_flows._shared._vector_target import get_vector_target, DualWriteTarget; print('OK')"` exits 0
- `uv run pytest tests/` shows ≥362 passed (358 Phase 1 baseline + 4 new)
- `bash scripts/verify.sh` 6/8 green (unchanged from Phase 1)
- The 4 new tests pass when run directly (with GCP deps mocked)
- `openspec validate 2026-08-31-gcp-data-plane-v1 --strict` passes
- The openspec change is committed (NO push) + archived

## Dependencies

- **Blocked by**: Phase 1 (`d1ef175`) which produced the local data plane this change extends.
- **Unblocks**: Phase 3 (Cloud Run Jobs + Scheduler wiring the new destinations), Phase 5 (web layer surfacing the dual-write toggle), Phase 6 (HF Spaces headline demos).
- **Cross-repo**: The upstream `cianfhoghlaim` monorepo is unaffected — this is gemini_hackathon-only.

## Compatibility

- **No production code changes** to the Python package surface
  that Phase 1 left green. `get_duckdb_destination()` is **kept**
  as a thin wrapper — every existing caller continues to work.
- **No data migration** — the GCP destinations only get used when
  their env vars are set (`BIGQUERY_DATASET`,
  `VECTOR_BACKEND=vertex`, `GCS_RAW_BUCKET`); the local DuckDB +
  LanceDB path is the dev default.
- **The 4 new tests** are additive — they live alongside the
  Phase 1 baseline tests, do not modify any existing test, and are
  fully mocked (no live GCP calls).
- **`pyproject.toml` `dependencies` block unchanged** — the
  `[dependency-groups] gcp` is purely additive.

## What we explicitly did NOT touch

- `gemini_hackathon/model_registry.py` — Phase 0 surface, out of scope
- `baml_extracts/` source files — Phase 5 surface
- `cloud/terraform/` (except reading the BQ dataset module for context)
- `infra/`, `web/`, `hf_spaces/`, `gemini_hackathon_gradio/`, `orchestration/`, `journey/`
- CI workflow (`.github/workflows/ci.yml`)
- The Firestore default in `get_vector_target()` — Firestore stays the
  zero-standing-infra default; Vertex is the opt-in
