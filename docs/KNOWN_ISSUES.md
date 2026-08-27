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
