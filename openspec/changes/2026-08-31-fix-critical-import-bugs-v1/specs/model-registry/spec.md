# Spec Delta: model-registry (Phase 0 critical-fix)

This delta is applied by the OpenSpec change
[`2026-08-31-fix-critical-import-bugs-v1`](../proposal.md). It describes
the **ADDED** Requirements to the canonical `model-registry` capability
that this change introduces.

## ADDED Requirements

### Requirement: The `model-registry` capability SHALL be the single source of truth

The `gemini_hackathon.model_registry` module SHALL be the canonical
single source of truth for model strings used by every caller in the
project. The parallel duplicate registry in
`gemini_hackathon/models/__init__.py` SHALL be removed entirely.

#### Scenario: `import gemini_hackathon` succeeds

- **WHEN** a caller imports `gemini_hackathon`
- **THEN** the `model_registry.ModelRegistry` constructor SHALL NOT
  raise `ValueError("Duplicate registry key: …")`
- **AND** the package SHALL be usable end-to-end

#### Scenario: Only one module exposes the registry

- **WHEN** a caller runs `grep -rn "from gemini_hackathon.models" gemini_hackathon/ tests/ scripts/`
- **THEN** the command SHALL return 0 hits
- **AND** every callsite SHALL import from `gemini_hackathon.model_registry`

### Requirement: The `model-registry` capability SHALL define `PublicModelEntry` exactly once

The `@dataclass(frozen=True) class PublicModelEntry` SHALL be defined
in `gemini_hackathon/model_registry.py` (canonical location). It MUST
NOT be re-defined in `gemini_hackathon/call_llm.py` or anywhere else.

#### Scenario: `from gemini_hackathon.call_llm import PublicModelEntry` raises `ImportError`

- **WHEN** a caller attempts to import `PublicModelEntry` from
  `gemini_hackathon.call_llm`
- **THEN** `ImportError` SHALL be raised

#### Scenario: `from gemini_hackathon.model_registry import PublicModelEntry` succeeds

- **WHEN** a caller imports `PublicModelEntry` from
  `gemini_hackathon.model_registry`
- **THEN** the dataclass SHALL be returned with fields `key`, `family`,
  `role`, `display_name`, `backend`, `upstream_id`, `litellm_alias`,
  `tier`, `notes`

### Requirement: The `model-registry` capability SHALL be free of duplicate keys

Every key in `MODEL_REGISTRY` SHALL be unique. The constructor's
duplicate-key check (raises `ValueError`) is the gate that enforces
this invariant.

#### Scenario: Constructor raises on duplicates

- **WHEN** two entries in any family helper (`_text_llm_entries`,
  `_ocr_vision_entries`, `_image_gen_entries`,
  `_learning_graph_entries`) declare the same `key`
- **THEN** `ModelRegistry.__init__` SHALL raise
  `ValueError(f"Duplicate registry key: {key!r}")`

#### Scenario: No duplicate in `image_gen`

- **WHEN** `_image_gen_entries()` is called
- **THEN** the returned dict SHALL NOT contain duplicate keys for any
  `image_gen` model (including the historical `z-image-turbo` conflict
  between `invokeai` and `llama_swap` variants)

### Requirement: The `model-registry` capability SHALL expose the canonical model set

The `MODEL_REGISTRY` SHALL expose the canonical 11 entries that were
previously stranded in the deleted `gemini_hackathon/models/__init__.py`:
`minimax-m3`, `qwen3.8-27b`, `deepseek-v4-flash`, `kimi-k2.6`, `bge-m3`,
`bge-reranker-v2-m3`, `orpheus-3b`, `sesame-csm-1b`, `minicpm-o-4_5`,
`qwen3-vl-8b`, `qwen3-vl-4b`. Each entry SHALL be marked
`available=False` (tombstone) if it does not belong to the active
`hackathon` profile; otherwise `available=True`.

#### Scenario: All 11 stranded entries are present

- **WHEN** `MODEL_REGISTRY` is iterated
- **THEN** every key listed above SHALL be present exactly once
- **AND** every entry SHALL carry a `profile` value (`hackathon`, `dev`,
  or `both`)

### Requirement: The `gemini-hackathon serve` CLI SHALL delegate to the Python backend

The `gemini_hackathon.cli._cmd_serve` function SHALL spawn
`python -m gemini_hackathon.backend --port {port}` via `subprocess.Popen`
with stdout/stderr piped to the parent process. It MUST NOT use
`http.server.SimpleHTTPRequestHandler` (which only serves static files
and does not implement `/api/health`, `/api/chat/completions`,
`/api/themes`).

#### Scenario: `serve` boots the Python backend

- **WHEN** an operator runs `gemini-hackathon serve --port 8000`
- **THEN** the Python backend module SHALL be spawned as a subprocess
- **AND** the parent process SHALL stream the child's stdout + stderr
  to its own stdout + stderr
- **AND** on `KeyboardInterrupt` the child SHALL be terminated cleanly

#### Scenario: `serve --help` advertises the new behaviour

- **WHEN** an operator runs `gemini-hackathon serve --help`
- **THEN** the help text SHALL describe the delegation to
  `python -m gemini_hackathon.backend` rather than the legacy
  `SimpleHTTPRequestHandler` claim
