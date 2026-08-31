#!/usr/bin/env bash
# scripts/verify.sh — the 8-tick verify gate for gemini_hackathon.
#
# Same shape as journey/scripts/verify.sh: each tick is a one-line
# `python -c "..."` (or `make <target>`) that prints [OK] / [FAIL].
# Mirrors `scripts/dev.sh` step 5.
#
# Usage:
#   ./scripts/verify.sh
#   make verify     # the Makefile alias

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Output helpers (the canonical Cianfhoghlaim verify pattern)
# ---------------------------------------------------------------------------

readonly C_RESET=$'\033[0m'
readonly C_GREEN=$'\033[32m'
readonly C_RED=$'\033[31m'
readonly C_BLUE=$'\033[34m'
readonly C_BOLD=$'\033[1m'

_t=0
_ok()    { printf '  %s[OK]%s    %s\n' "$C_GREEN" "$C_RESET" "$1"; _t=$((_t+1)); }
_fail()  { printf '  %s[FAIL]%s  %s\n' "$C_RED"   "$C_RESET" "$1"; }
_skip()  { printf '  %s[SKIP]%s  %s\n' "$C_BLUE"  "$C_RESET" "$1"; }
_section() { printf '\n%s%s%s\n' "$C_BOLD" "$1" "$C_RESET"; }

# ---------------------------------------------------------------------------
# 1. Imports — every gemini_hackathon.* module imports cleanly
# ---------------------------------------------------------------------------

_section "1. Imports"

if uv run python -c "
import importlib
modules = [
    'gemini_hackathon.theming',
    'gemini_hackathon.agents.registry',
    'gemini_hackathon.model_registry',
    'gemini_hackathon.call_llm',
    'gemini_hackathon.backend',
    'gemini_hackathon.cli',
    'gemini_hackathon.observability',
    'gemini_hackathon.ocr',
    'gemini_hackathon.ocr_ensemble',
    'gemini_hackathon.subnations',
    'gemini_hackathon.certificate',
    'gemini_hackathon.progression',
    'gemini_hackathon.ledger',
    'gemini_hackathon.knowledge_graph',
    'gemini_hackathon.memory',
    'gemini_hackathon.sources',
]
for m in modules:
    importlib.import_module(m)
print(f'{len(modules)} modules imported OK')
" >/dev/null 2>&1; then
    _ok "gemini_hackathon.* (16 modules)"
else
    _fail "gemini_hackathon.* imports failed (run with PYTHONPATH set to see tracebacks)"
fi

# ---------------------------------------------------------------------------
# 2. BAML — generate + test
# ---------------------------------------------------------------------------

_section "2. BAML"

if uv run baml-cli generate >/dev/null 2>&1; then
    _ok "baml-cli generate"
else
    _fail "baml-cli generate failed (check baml_extracts/*.baml syntax)"
fi

if BAML_TEST_MODE=true uv run baml-cli test >/dev/null 2>&1; then
    _ok "baml-cli test"
else
    _skip "baml-cli test (requires network; CI sets BAML_TEST_MODE=true + OPENAI_API_KEY)"
fi

# ---------------------------------------------------------------------------
# 3. Lint — ruff check + ruff format --check
# ---------------------------------------------------------------------------

_section "3. Lint"

if uv run ruff check . >/dev/null 2>&1; then
    _ok "ruff check ."
else
    _fail "ruff check . found issues"
fi

if uv run ruff format --check . >/dev/null 2>&1; then
    _ok "ruff format --check ."
else
    _fail "ruff format --check . found unformatted files (run: make format)"
fi

# ---------------------------------------------------------------------------
# 4. Typecheck — mypy gemini_hackathon/ (strict)
# ---------------------------------------------------------------------------

_section "4. Typecheck"

if uv run mypy gemini_hackathon/ >/dev/null 2>&1; then
    _ok "mypy gemini_hackathon/"
else
    _fail "mypy gemini_hackathon/ found type errors"
fi

# ---------------------------------------------------------------------------
# 5. DLT smoke — every DLT pipeline imports + (if DuckDB available) runs
# ---------------------------------------------------------------------------

_section "5. DLT smoke"

if uv run python -c "
import importlib
modules = [
    'dlt_pipelines.official_doc_fetcher',
    'dlt_pipelines.safeguarding_fetcher',
    'dlt_pipelines.uk_ncce_learning_graphs',
    'dlt_pipelines.pdf_downloader',
    'dlt_pipelines.corpus_downloader',
    'dlt_pipelines._shared',
]
for m in modules:
    importlib.import_module(m)
print(f'{len(modules)} dlt modules imported OK')
" >/dev/null 2>&1; then
    _ok "dlt_pipelines.* (6 modules imported)"
else
    _fail "dlt_pipelines.* import failed (Python 3.11+ required for UTC import)"
fi

# ---------------------------------------------------------------------------
# 6. CocoIndex smoke — every CocoIndex App imports + gracefully degrades
# ---------------------------------------------------------------------------

_section "6. CocoIndex smoke"

if uv run python -c "
import importlib
modules = [
    'cocoindex_flows._shared._lifespan',
    'cocoindex_flows._shared._vector_target',
    'cocoindex_flows._shared._docling_grid_segmenter',
    'cocoindex_flows.pdf.pdf_to_markdown_app',
    'cocoindex_flows.uk_ncce.learning_graphs_app',
    'cocoindex_flows.uk_ncce.pedagogy_cache',
    'cocoindex_flows.ireland.lc_subject_embedding',
    'cocoindex_flows.education.lc6_extraction_app',
    'cocoindex_flows.equivalency.equivalency_graph_app',
]
for m in modules:
    importlib.import_module(m)
print(f'{len(modules)} cocoindex modules imported OK')
" >/dev/null 2>&1; then
    _ok "cocoindex_flows.* (9 modules imported)"
else
    _fail "cocoindex_flows.* import failed"
fi

# ---------------------------------------------------------------------------
# 7. Gradio imports — every gemini_hackathon_gradio.* module imports cleanly
# ---------------------------------------------------------------------------

_section "7. Gradio imports"

if uv run python -c "
import importlib
modules = [
    'gemini_hackathon_gradio.an_learning_graph',
    'gemini_hackathon_gradio.an_learning_graph.render_tab',
    'gemini_hackathon_gradio.an_learning_graph.equivalencies_tab',
    'gemini_hackathon_gradio.an_learning_graph.generate_tab',
    'gemini_hackathon_gradio.an_learning_graph.pedagogy_tab',
    'gemini_hackathon_gradio.an_learning_graph.theme',
]
for m in modules:
    importlib.import_module(m)
print(f'{len(modules)} gradio modules imported OK')
" >/dev/null 2>&1; then
    _ok "gemini_hackathon_gradio.* (6 modules)"
else
    _fail "gemini_hackathon_gradio.* import failed (Gradio may need an isolated venv)"
fi

# ---------------------------------------------------------------------------
# 8. Dagster imports — every orchestration.defs.* module imports cleanly
# ---------------------------------------------------------------------------

_section "8. Dagster imports"

if uv run python -c "
import importlib
modules = [
    'orchestration.defs',
    'orchestration.defs.3_model_lifecycle',
    'orchestration.defs.3_model_lifecycle.uk_ncce_learning_graphs',
    'orchestration.defs.3_model_lifecycle.uk_ncce_learning_graph_equivalencies',
    'orchestration.defs.3_model_lifecycle.learning_graph_equivalency_graph',
    'orchestration.defs.3_model_lifecycle.pedagogy_overlay',
    'orchestration.defs.3_model_lifecycle.pedagogy_principles_cache',
    'orchestration.defs.3_model_lifecycle.sensors.uk_ncce_pdf_sensor',
]
for m in modules:
    importlib.import_module(m)
print(f'{len(modules)} dagster modules imported OK')
" >/dev/null 2>&1; then
    _ok "orchestration.defs.* (9 modules)"
else
    _fail "orchestration.defs.* import failed"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

printf '\n'
if [[ "$_t" -eq 8 ]]; then
    printf '%s✓ 8/8 verify ticks green%s\n' "$C_GREEN" "$C_RESET"
    exit 0
else
    printf '%s✗ %d/8 verify ticks failed%s — see docs/LOCAL_DEV.md §'\\''What to do when something breaks'\\''\n' "$C_RED" "$((8 - _t))" "$C_RESET"
    exit 1
fi