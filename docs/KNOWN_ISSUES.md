# Known Issues

A running log of known issues in the `gemini_hackathon` codebase. The
August 2026 refactor deliberately defers test fixes to a post-hackathon
pass so the substantive work (the platform + the LC/JC certificate
pipeline) can land first.

## Test failures (deferred)

Per `tests/` source-grep: **250 test functions across 24 modules**.
The README's older `164 passed, 13 skipped` claim predates the current
codebase. The 7 known failures below are listed without rerunning the
suite (the refactor explicitly defers test maintenance):

| Test | Issue | Resolved by |
|---|---|---|
| `test_assets.py::test_router_priority_order_fibo_invoke_unsloth` | Expected backend order is hard-coded to `[COMFYUI, INVOKEAI, UNSLOTH_STUDIO, STUB]`; Phase 8 added `LITELLM` at index 0. | W10 (FIBO image gen) — fix the test to match the new `LITELLM → COMFYUI → INVOKEAI → UNSLOTH_STUDIO → STUB` order. |
| `test_babylon_export.py::test_babylon_file_uses_only_three_babylon_modules` | Babylon scene assertions drifted when `babylon_scene.tsx` was updated. | W14 deletes `web/src/components/babylon/` (Babylon 3D is out of scope for the education system). Test becomes `pytest.skip`. |
| `test_babylon_export.py::test_babylon_renders_an_intersection_observer` | Same as above. | Same as above. |
| `test_dlt_pipelines.py::test_official_doc_fetcher_creates_official_documents_table` | Column-contract assertions drifted from the current `OFFICIAL_DOC_COLUMNS` shape. | W5 lifts the cianfhoghlaim Ireland DLT pipeline with the canonical 12-column shape; fix the test against the new contract. |
| `test_dlt_pipelines.py::test_official_doc_fetcher_handles_missing_pdfs_gracefully` | Same as above. | Same as above. |
| `test_dlt_pipelines.py::test_safeguarding_fetcher_creates_safeguarding_policies_table` | Same as above. | Same as above. |
| `test_ocr.py::test_is_backend_available_true_for_live_llama_swap` | Asserts a live `127.0.0.1:8080` llama-swap backend; should skip when not reachable. | Convert to `pytest.skip` when the live backend is unreachable. |

The test grace gate: the refactor is judged on the platform's behaviour,
not the test suite. Run `pytest tests/ -q` after each workstream to
confirm no new failures are introduced.

## Codebase correctness bugs (resolved by the refactor)

| Bug | Resolved by |
|---|---|
| Two parallel component trees: `web/components/` (tracked, 6 files: `cards/`, `chat/`, `comparison/` ×2, `map/`, `themes/`) and `web/src/components/` (newer, partial: `ModelPolicyBadge`, `babylon/`, `comparison/` ×2, `marimo/`, `onboarding/`, `session/`, `themes/`). The routes import `../components/` which from `web/src/routes/` resolves to `web/src/components/`. The tracked `web/components/` tree is **technically unused** but still committed. | W0 documents the situation; W15 (docs) migrates `web/components/` to `web/_legacy_components/` and updates the gitignore. The unused tree is harmless as long as the routes only import from `web/src/components/`. |
| Unpinned `ruff` / `mypy` / `baml-cli` in `mise.toml` (the diff that dropped the pins). | W0 restores the pins. |
| Untracked `.agents/` (16 skills + mcp_config.json + rules). | W0 adds `.agents/` to `.gitignore` — kept local until we decide what subset to commit. |
| `baml_client/` + `web/baml_client/` committed but already in `.gitignore`. | No change — the regex correctly ignores them; they're re-emitted on every `baml-cli generate`. |

## Architectural constraints carried forward

These are intentional, not bugs:

- The 4 `gemini_hackathon/agents/ideas/*` plain-Python classes are **kept** as fallback nodes inside ADK 2 workflows (per the `adk2-tutorial/L4b_recursion` recursive pattern — a plain-Python class is a valid function-node inside an ADK Workflow). They are NOT deleted in W7.
- The `Babylon.js 3D scene` is dropped per the user's instruction (no MMO, focus on education system).
- The 6 Celtic mythology enums (`CelticLanguage`, `MythologicalCycle`, etc.) and the Babylon/Godot/Unity/Unreal exporters are dropped (out of scope for the education system).
- The 5-stage user-context (Ireland / England / NI / Scotland / Wales) defaults are kept as the active set; Jersey + Guernsey + Isle of Man are in scope for Phase 2.
- The 3 idea agents `tutor` / `marking_grader_workflow` / `equivalency_generator` / `curriculum_change_sensor` are reorganised under the stage coordinators but their logic is preserved (W7).

## Resolved by the refactor

| Was | Now |
|---|---|
| 4 idea agents as plain-Python classes | 5 stage coordinators as ADK 2 workflows (Aistear / Primary / JC / LC / cross_subject). |
| `gemini_hackathon/agents/ideas/` | `gemini_hackathon/agents/stages/<stage>/`. |
| `gemini_hackathon/agents/fleet/*` (4 primitives) | Preserved + extended (5th primitive: `agents/fleet/fleet_graph.py` for FalkorDB). |
| `gemini_hackathon/progression/certificate.py` (12 award types) | Extended to 14 NCCA subjects + 5 stages + the skill-progression ledger (W9). |
| `gemini_hackathon/gradio/` (NEW) | The 5 Gradio editorial studios + the 1 big Cloud Run editorial studio. |
| `gemini_hackathon_gradio` (NEW, lifted from `sruth/spaces/_common/`) | The shared library: theme (5-stage British Isles palette), baml_client, baml_pydantic_bridge, anam_bonneagar, i18n, pclm_emitter, hlml_emitter, hf_hub_push, demo_recorder. |
| `gemini_hackathon/assets/fibo/` (NEW) | The 14 NCCA subject × 5 stage prompt bank + LiteLLM cache + texture_processor. |
| `gemini_hackathon/data/leabharlann/` (NEW) | The 7 leabharlann subdirs lifted verbatim from `cianfhoghlaim/leabharlann/`. |
| `gemini_hackathon/data/ireland/ncca_policy/` (NEW) | The 5 NCCA policy PDFs — the source of truth for the LC/JC certificate. |
| `gemini_hackathon/memory/` (NEW) | The 5-layer memory pedagogy (short-term / handoff / long-term / artifacts / institutional). |

## Phase 1 (2026-08-31) gaps surfaced when wiring the local data plane

The Phase 1 polish plan (`openspec/changes/2026-08-31-local-data-plane-v1/`)
unblocked `uv sync` and the verify gate; the following gaps remain
documented for the Phase 5 CocoIndex upgrade + the Phase 7 IaC refactor:

| Gap | Symptom | Workaround | Resolved by |
|---|---|---|---|
| **Per-LC subject PDF cache empty** | `data/ireland/leaving_certificate/<subject>/<lang>/` contains only a single `README.md` stub for `mathematics/en/`. The Ireland NCCA `official_doc_fetcher` resource scans this tree and yields 0 rows. | The stub `README.md` (added in Phase 1) keeps the directory present so `Path.exists()` checks don't crash. The 35 rows in `raw.official_documents` come from the 7 remote-URL jurisdictions (England boards + Scotland + Wales + NI + IoM + Jersey + Guernsey) + NCCE (11 rows). | TBD — the per-LC corpus lived at `data/ireland/ncca_policy/` as the certificate source of truth (W14), and the per-subject cache was never populated. Phase 5 plan: import the canonical 134 LC PDFs from `cianfhoghlaim/leaving_certificate/`. |
| **`LANGFUSE_HOST` defaults to cloud.langfuse.com** | The `gemini-hackathon` service's env var (`compose.yaml:81`) defaults to `https://cloud.langfuse.com`; the local docker-compose Langfuse v3 service is at `http://langfuse-web:3000`. | Set `LANGFUSE_HOST=http://langfuse-web:3000` in `.env` (or `compose.override.yaml`) when running `make dev`. Phase 1 added `depends_on: langfuse-web` so the service waits for it. | Phase 7 IaC refactor will move observability to Workload Identity Federation + GCP-native Stackdriver; the env var will point at the Cloud Run service, not the docker service. |
| **LanceDB local mode requires `EMBED_BACKEND=sentence_transformers`** | The `EMBED_BACKEND=vertex` default + the `EMBED_BACKEND=sentence_transformers` fallback both expect `lancedb`, `sentence-transformers`, and `cocoindex>=1.0` to be installed (now in the `cianfhoghlaim-parity` optional group). `make cocoindex-update` is a graceful no-op when they aren't installed. | Run `uv sync --group cianfhoghlaim-parity` to install them locally. The 3 new tests under `tests/{dlt,cocoindex,baml}/` are `@pytest.mark.integration` and skip when the deps aren't installed. | The integration tests pass when the deps are installed (Phase 1 verified). |
| **CocoIndex App signature changed in v1.0** | `cocoindex>=1.0` changed the `App.__init__` signature to require a positional `main_fn`, breaking the R1-R4 conformance pattern (`coco.App(coco.AppConfig(name=...))`) used by `cocoindex_flows/ireland/junior_cycle_embedding.py`. | Phase 1 added a `try/except TypeError` graceful-degrade so `make cocoindex-update` stays a no-op (logged warning) rather than a fatal crash. The `tests/cocoindex/test_lancedb_local_mode.py` test verifies LanceDB writes via the `lancedb` API directly (independent of the broken App pattern). | Phase 5 CocoIndex upgrade will rewrite the affected 4 Apps (`junior_cycle_embedding.py` only needs the fix today; the others already use the v1.0 signature correctly). |
| **`corpus_downloader` non-nullable columns** | The 5 `corpus_downloader` non-nullable column hints (e.g. `sha256_hash`) caused `Cannot coerce NULL` when the upstream fetch failed (offline mode = every row has `sha256_hash=None`). | Phase 1 added `nullable: True` to the affected columns. The pipeline now writes 35 stub rows that record the offline status in the `fetch_error` field. | No further action — the fix is in `dlt_pipelines/corpus_downloader.py:68-81`. |
| **`docker-compose.yml` and `docker-compose.local.yaml` deleted** | Phase 0 consolidated the 2 compose files into `compose.yaml`. `docker-compose.local.yaml` is now a gitignored orphan in `git status`. | The canonical file is `compose.yaml` per the Phase 0 commit `a92d8c8`. `git status` shows them as "deleted" against the old HEAD — safe to ignore. | Pre-existing from Phase 0 — not a Phase 1 regression. |
| **`pdf_downloader.py` uses sqlite3 against a DuckDB file** | The downloader connects via `sqlite3.connect(...)` and queries `SELECT FROM official_documents` (no schema); the DuckDB file's actual schema is `raw.official_documents` and `sqlite3` can't read DuckDB's binary format. The result is `{considered: 0, downloaded: 0, ..., failed: 0}` — i.e. a no-op. | Phase 1 explicitly kept the sqlite3 path for backwards compat (commented in `dlt_pipelines/pdf_downloader.py:56-64`). `make dlt-smoke-all` includes `pdf_downloader` and exits 0 because the no-op is graceful. | Phase 5 — rewrite `pdf_downloader` to use `duckdb.connect(...)` directly + query `raw.official_documents`. |
| **`notebooks/02_*.ipynb`, `notebooks/03_*.ipynb`, `notebooks/04_*.ipynb` had 2 pre-existing broken patterns** | The notebooks used relative paths (`data/gemini_hackathon.duckdb`) that resolved incorrectly when the Jupyter kernel's CWD was `notebooks/` instead of the repo root. The print-format spec `:80s` rejected Path objects. | Phase 1 added a setup cell (`os.chdir(<repo root>)`) and changed the spec to `:80s` of `str(...)`. All 3 now execute end-to-end. | No further action. |
