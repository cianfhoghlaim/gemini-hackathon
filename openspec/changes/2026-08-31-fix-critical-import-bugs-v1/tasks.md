# Tasks for 2026-08-31-fix-critical-import-bugs-v1

## Phase 0 — OpenSpec change folder (this commit)

- [x] T0.1: `openspec/changes/2026-08-31-fix-critical-import-bugs-v1/proposal.md` written
- [x] T0.2: `openspec/changes/.../specs/model-registry/spec.md` written
- [x] T0.3: `openspec/changes/.../tasks.md` (this file) written
- [x] T0.4: `openspec validate 2026-08-31-fix-critical-import-bugs-v1 --strict` passes

## Phase 1 — Fix the 5 import-breaking bugs

- [ ] T1.1: `gemini_hackathon/model_registry.py:781-801` — delete the duplicate `z-image-turbo` (llama_swap) entry. Add the kept-`invokeai` comment marker per instructions.
- [ ] T1.2: `gemini_hackathon/assets/image_gen.py:255-258` — delete the stub `_StubBackend` (no methods). Keep the rich one at `:259-276`.
- [ ] T1.3: `gemini_hackathon/cli.py:318-328` — replace `_cmd_serve` to spawn `python -m gemini_hackathon.backend --port {port}` via `subprocess.Popen`.
- [ ] T1.4: `gemini_hackathon/cli.py:232-238` — update the `serve` subcommand's `--help` text.
- [ ] T1.5: `gemini_hackathon/model_registry.py` — add the 11 missing entries (`minimax-m3`, `qwen3.8-27b`, `deepseek-v4-flash`, `kimi-k2.6`, `bge-m3`, `bge-reranker-v2-m3`, `orpheus-3b`, `sesame-csm-1b`, `minicpm-o-4_5`, `qwen3-vl-8b`, `qwen3-vl-4b`) in the appropriate family sections, marking tombstones as `available=False`.
- [ ] T1.6: `gemini_hackathon/models/__init__.py` — delete entirely.
- [ ] T1.7: `gemini_hackathon/call_llm.py:361-373` — delete the duplicate `PublicModelEntry` dataclass.
- [ ] T1.8: Replace all `from gemini_hackathon.models import …` with `from gemini_hackathon.model_registry import …` (13 callsites in tests + cli.py + gemini_hackathon_gradio/oideachais_pdf_review/app.py).
- [ ] T1.9: Verify 0 hits remain: `grep -rn "from gemini_hackathon.models" gemini_hackathon/ tests/ scripts/`.
- [ ] T1.10: Verify `from gemini_hackathon.model_registry import PublicModelEntry` works AND `from gemini_hackathon.call_llm import PublicModelEntry` raises `ImportError`.

## Phase 2 — Quality gates

- [ ] T2.1: `uv run python -c "import gemini_hackathon; print('OK')"` prints `OK`
- [ ] T2.2: `make lint` exits 0
- [ ] T2.3: `make typecheck` exits 0
- [ ] T2.4: `make test` exits 0 with 333 passed
- [ ] T2.5: `make verify` exits 0 with 8/8 [OK]
- [ ] T2.6: `openspec validate 2026-08-31-fix-critical-import-bugs-v1 --strict` passes

## Phase 3 — Commit + archive

- [ ] T3.1: `git commit -m "fix(model-registry): remove 5 import-breaking bugs …"` — conventional-commits message that references the openspec change ID.
- [ ] T3.2: `openspec archive 2026-08-31-fix-critical-import-bugs-v1 --yes`

## Out of scope (Phase 1+)

- Anything in `cloud/`, `hf_spaces/`, `gemini_hackathon_gradio/` (other than the 1 callsite fix), `web/`, `orchestration/`, `journey/`, `baml_extracts/`, `baml_client/`, `dlt_pipelines/`, `cocoindex_flows/`.
- The 3 follow-on openspec changes (`learning-graph-equivalency-graph-v1`, `pedagogy-overlay-renderer-v1`, `uk-ncce-learning-graph-showcase-v1`).
- Any new entry that would change the public model roster.
