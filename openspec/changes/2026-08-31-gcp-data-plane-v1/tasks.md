# Tasks for 2026-08-31-gcp-data-plane-v1

## Phase 0 — OpenSpec change folder (this commit)
- [x] T0.1: `openspec/changes/2026-08-31-gcp-data-plane-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/gcp-data-plane/spec.md` (1 spec delta)
- [x] T0.3: `openspec/changes/.../tasks.md` (this file)
- [x] T0.4: `openspec validate 2026-08-31-gcp-data-plane-v1 --strict` passes

## Phase 1 — BigQuery DLT destination (sub-task 2.1)
- [x] T1.1: `dlt_pipelines/_shared.py` gains `get_destination(name, database_path, bigquery_dataset)` polymorphic 4-backend factory
- [x] T1.2: `bigquery` branch returns `dlt.destinations.bigquery(dataset_name=...)` with `try/except ImportError` guard
- [x] T1.3: `tests/dlt/test_bigquery_destination.py` mocks `dlt.destinations.bigquery` and asserts kwargs

## Phase 2 — Vertex AI Vector Search target (sub-task 2.2)
- [x] T2.1: `VertexVectorSearchTarget` completed with `upsert`, `find_nearest`, `delete` methods (sync shim wrappers for the existing async `upsert_batch` / `find_nearest`)
- [x] T2.2: All methods wrapped in `try/except ImportError` for `google.cloud.aiplatform`
- [x] T2.3: `tests/cocoindex/test_vertex_target.py` mocks `MatchingEngineIndex` + `IndexEndpoint`

## Phase 3 — Dual-write capability (sub-task 2.3)
- [x] T3.1: `DualWriteTarget` composite class — fans out upsert/delete, reads from primary, raises on all-failed
- [x] T3.2: `get_vector_target()` returns `DualWriteTarget(Firestore, Vertex)` when `VECTOR_TARGET_DUAL_WRITE=1`
- [x] T3.3: `tests/cocoindex/test_dual_write_target.py` covers both targets, primary-only read, all-failed error

## Phase 4 — GCS substrate for PDF corpus (sub-task 2.4)
- [x] T4.1: New `_output_path()` helper in `corpus_downloader.py` + `pdf_downloader.py`
- [x] T4.2: GCS upload path via `google.cloud.storage.Client` with local fallback
- [x] T4.3: `tests/dlt/test_gcs_substrate.py` mocks `storage.Client` + asserts path shape

## Phase 5 — Lazy import guards + new `[dependency-groups] gcp` (sub-task 2.5)
- [x] T5.1: New `[dependency-groups] gcp` group in `pyproject.toml` (commented + 3 deps)
- [x] T5.2: Verify the offline-safe default still works without the gcp group
- [x] T5.3: Comment block above the new group documents `uv sync --group gcp`

## Phase 6 — Notebook 12 demo cell (sub-task 2.6)
- [x] T6.1: New code cell in `notebooks/12_learning_graph_equivalency_walkthrough.ipynb` demoing the Vertex path
- [x] T6.2: Execute the notebook via `jupyter nbconvert --to notebook --execute --inplace`

## Phase 7 — Docs + tests + commit + archive
- [x] T7.1: `docs/MODEL_POLICY.md` gains "Vertex AI Vector Search cost considerations" section
- [x] T7.2: `docs/KNOWN_ISSUES.md` gains 2 Phase 2 gap entries
- [x] T7.3: 4 new test files under `tests/{dlt,cocoindex}/`
- [x] T7.4: `pytest tests/` shows ≥362 passed (358 baseline + 4 new)
- [x] T7.5: `bash scripts/verify.sh` stays 6/8 green
- [x] T7.6: commit `feat(phase-2): add GCP data plane` (NO push)
- [x] T7.7: `openspec archive 2026-08-31-gcp-data-plane-v1` after commit

## Notes on what we explicitly did NOT touch

- **Phase 0 surfaces**: `gemini_hackathon/model_registry.py` (per Phase 0 commit `603637c` — canonical surface, out of scope).
- **`baml_extracts/` source files** (Phase 5 surface).
- **`cloud/terraform/`, `infra/`, `web/`, `hf_spaces/`, `gemini_hackathon_gradio/`, `orchestration/`, `journey/`** — all out of scope per "What NOT to touch" in the Phase 2 plan.
- **CI workflow** (`.github/workflows/ci.yml`) — no changes.
- **The Firestore default** in `get_vector_target()` remains unchanged — Firestore stays the zero-standing-infra default; Vertex is the opt-in.
- **Phase 1's 358 baseline tests** — all preserved unchanged.
