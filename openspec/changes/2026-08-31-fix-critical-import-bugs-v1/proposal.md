# 2026-08-31-fix-critical-import-bugs-v1

> **Phase 0 critical-fix.** The `gemini_hackathon` package currently
> fails to import because `gemini_hackathon.model_registry.MODEL_REGISTRY`
> raises `ValueError("Duplicate registry key: 'z-image-turbo'")` at
> construction time (`gemini_hackathon/model_registry.py:826-829`). This
> blocks all 333 tests, all 4 quality gates, and every local dev
> workflow. This change fixes 5 import-breaking bugs in one shot and
> re-establishes `model_registry.py` as the canonical single registry.

## Why

Every `import gemini_hackathon` currently raises `ValueError` because of
one duplicate key in `_image_gen_entries()`. Once that is fixed, four
additional bugs surface:

1. **`gemini_hackathon/model_registry.py:713-728` and `:781-801`** both
   declare `z-image-turbo` (one `invokeai`, one `llama_swap`). The
   constructor at `:826-829` rejects the second.
2. **`gemini_hackathon/assets/image_gen.py:255-261`** defines
   `_StubBackend` twice. The second silently overwrites the first, but
   only the second has the proper docstring + `metadata` dict + the
   `generate()` implementation that the router relies on (the router
   catches the broken version silently).
3. **`gemini_hackathon/cli.py:318-328`** (`_cmd_serve`) uses
   `http.server.SimpleHTTPRequestHandler`, which serves only static
   files. None of `/api/health`, `/api/chat/completions`, `/api/themes`
   are reachable. The correct invocation per `backend.py:27` docstring is
   `python -m gemini_hackathon.backend`.
4. **`gemini_hackathon/models/__init__.py`** duplicates
   `MODEL_REGISTRY` / `ModelRegistry` / `ModelRegistryEntry` /
   `ModelFamily` / `ModelRole` / `ModelProfile` / `model_for` /
   `PublicModelEntry` and adds 11 entries (`minimax-m3`,
   `qwen3.8-27b`, `deepseek-v4-flash`, `kimi-k2.6`, `bge-m3`,
   `bge-reranker-v2-m3`, `orpheus-3b`, `sesame-csm-1b`, `minicpm-o-4_5`,
   `qwen3-vl-8b`, `qwen3-vl-4b`) that `model_registry.py` does NOT have.
   Conflicting entries (`qwen-image-2512`, etc.) would split policy.
5. **`gemini_hackathon/call_llm.py:361-373`** defines a duplicate
   `PublicModelEntry` dataclass (identical shape to
   `model_registry.py:1013-1025`). Two definitions of the same type
   cause confusion about which is canonical.

## What changes

- **#1**: Delete the `llama_swap` variant at `model_registry.py:781-801`
  (kept the `invokeai` variant per `infra/stacks/litellm/config/config.yaml`
  routing). Add the comment marker per the instructions.
- **#2**: Delete the stub `_StubBackend` class at `image_gen.py:255-258`
  (no docstring, no methods); keep the rich one at `:259-276`.
- **#3**: Replace `_cmd_serve` (cli.py:318-328) to spawn
  `python -m gemini_hackathon.backend --port {port}` via
  `subprocess.Popen` with stdout/stderr piped to the parent. Handle
  `KeyboardInterrupt` cleanly. Update the `serve` subcommand's
  `--help` text.
- **#4**: Add the 11 missing entries to `model_registry.py` in the
  appropriate family sections (`text_llm` / `embedder` / `rerank` /
  `voice` / `translation`). Mark each as `available=False` (tombstone)
  unless it belongs to the active `hackathon` profile per the
  `model_registry.py:1-15` docstring. Delete
  `gemini_hackathon/models/__init__.py`. Fix all 13 callsites of
  `from gemini_hackathon.models import …` to import from
  `gemini_hackathon.model_registry` instead.
- **#5**: Delete the `PublicModelEntry` dataclass from
  `call_llm.py:361-373` and import it from `model_registry`.

## Acceptance

- `uv run python -c "import gemini_hackathon; print('OK')"` returns
  `OK`
- `make lint` exits 0
- `make typecheck` exits 0
- `make test` shows 333 passed, 0 failed
- `make verify` shows 8/8 [OK]
- `openspec validate 2026-08-31-fix-critical-import-bugs-v1 --strict`
  passes
- 0 hits for `from gemini_hackathon.models import`
- `from gemini_hackathon.model_registry import PublicModelEntry` works
  AND `from gemini_hackathon.call_llm import PublicModelEntry` raises
  `ImportError`
- `gemini_hackathon serve --port 8000` now correctly delegates to
  `python -m gemini_hackathon.backend`

## Dependencies

- **Blocked by:** nothing (greenfield hygiene).
- **Unblocks:** every Phase 1+ change in the project.

## Compatibility

- **No semantic changes** to existing callers — the only behaviour
  delta is that `gemini_hackathon serve` now actually works.
- The 11 new entries added to `model_registry.py` are tombstones
  (`available=False`) where they don't belong to the hackathon profile,
  so the public roster is unchanged.
- The deleted `gemini_hackathon.models` package is replaced by
  `gemini_hackathon.model_registry` — the same names live there.
