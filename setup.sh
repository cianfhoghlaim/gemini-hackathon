#!/usr/bin/env bash
# setup.sh — bootstrap the gemini-hackathon development environment.
#
# Idempotent. Safe to re-run. Logs progress to stdout; exits non-zero on failure.
# Sets up:
#   1. uv (the 2026 standard Python package manager)
#   2. Project virtualenv + dependencies via `uv sync`
#   3. .env file (copied from .env.example if missing)
#   4. Smoke-tests the theming loader + the DLT pipeline import
#
# Usage:
#   ./setup.sh                 # full bootstrap + verify
#   ./setup.sh --no-verify     # bootstrap only, skip the verify pass

set -euo pipefail

# ---------------------------------------------------------------------------
# Pretty output
# ---------------------------------------------------------------------------

readonly C_RESET=$'\033[0m'
readonly C_BOLD=$'\033[1m'
readonly C_GREEN=$'\033[32m'
readonly C_BLUE=$'\033[34m'
readonly C_YELLOW=$'\033[33m'
readonly C_RED=$'\033[31m'

log()    { printf '%s==>%s %s\n' "$C_BLUE" "$C_RESET" "$*"; }
ok()     { printf '%s ✓%s  %s\n' "$C_GREEN" "$C_RESET" "$*"; }
warn()   { printf '%s !%s  %s\n' "$C_YELLOW" "$C_RESET" "$*"; }
fail()   { printf '%s ✗%s  %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }
banner() { printf '\n%s%s%s\n' "$C_BOLD" "$*" "$C_RESET"; }

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

VERIFY=1
for arg in "$@"; do
    case "$arg" in
        --no-verify) VERIFY=0 ;;
        -h|--help)
            sed -n '2,20p' "$0"
            exit 0
            ;;
        *) fail "Unknown argument: $arg" ;;
    esac
done

# ---------------------------------------------------------------------------
# Locate repo root (script may be invoked from anywhere)
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

banner "gemini-hackathon setup"
log "Working directory: $SCRIPT_DIR"

# ---------------------------------------------------------------------------
# 1. uv — the 2026 standard Python package manager
# ---------------------------------------------------------------------------

banner "[1/5] uv"

if command -v uv >/dev/null 2>&1; then
    UV_VERSION="$(uv --version)"
    ok "uv already installed: $UV_VERSION"
else
    log "uv not found — installing…"
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        fail "Neither curl nor wget available; please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
    fi

    # Source the env file the astral installer drops in ~/.local/bin
    # shellcheck disable=SC1091
    [[ -f "$HOME/.local/bin/env" ]] && source "$HOME/.local/bin/env"

    if ! command -v uv >/dev/null 2>&1; then
        fail "uv install completed but 'uv' is not on PATH. Add \$HOME/.local/bin to PATH and re-run."
    fi
    ok "uv installed: $(uv --version)"
fi

# ---------------------------------------------------------------------------
# 2. Sync dependencies (uv)
# ---------------------------------------------------------------------------

banner "[2/5] uv sync"

if [[ ! -f "pyproject.toml" ]]; then
    fail "pyproject.toml not found in $SCRIPT_DIR — are you in the project root?"
fi

uv sync --all-extras
ok "Dependencies synced to .venv/"

# ---------------------------------------------------------------------------
# 3. .env file
# ---------------------------------------------------------------------------

banner "[3/5] .env"

if [[ -f ".env" ]]; then
    ok ".env already exists — leaving it alone"
else
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        ok ".env created from .env.example (fill in real secrets before running anything that needs them)"
    else
        warn ".env.example missing — skipping .env creation"
    fi
fi

# ---------------------------------------------------------------------------
# 4. BAML codegen (smoke test that baml_extracts/*.baml parse)
# ---------------------------------------------------------------------------

banner "[4/5] BAML codegen"

if uv run baml-cli --version >/dev/null 2>&1; then
    if [[ -d "baml_extracts" ]]; then
        # The baml_src -> baml_extracts symlink lets BAML's default baml_src
        # lookup find the .baml files without needing --from.
        log "Running baml-cli generate…"
        if uv run baml-cli generate 2>&1 | tail -20; then
            ok "BAML client generated"
        else
            warn "baml-cli generate exited non-zero — check baml_extracts/*.baml syntax"
        fi
    else
        warn "baml_extracts/ directory missing — skipping codegen"
    fi
else
    warn "baml-cli not installed — skipping codegen (install with: uv add 'baml-py[testing]')"
fi

# ---------------------------------------------------------------------------
# 5. Verify
# ---------------------------------------------------------------------------

if [[ "$VERIFY" -eq 1 ]]; then
    banner "[5/5] Verify"

    log "Loading theming module…"
    if uv run python -m gemini_hackathon.theming 2>&1 | tail -30; then
        ok "Theming module loaded"
    else
        warn "Theming module reported errors (see above)"
    fi

    log "Importing DLT pipeline…"
    if uv run python -c "import dlt_pipelines.official_doc_fetcher; print('DLT pipeline OK')" 2>&1; then
        ok "DLT pipeline importable"
    else
        warn "DLT pipeline import failed (may need cd dlt_pipelines/ first)"
    fi
else
    banner "[5/5] Verify (skipped — --no-verify)"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

banner "Done"
cat <<EOF
${C_GREEN}Next steps:${C_RESET}
  1. Edit .env with real API keys (MINIMAX_API_KEY, FIRECRAWL_API_KEY, …)
  2. Run the CLI:        ${C_BOLD}uv run gemini-hackathon${C_RESET}  (or  ${C_BOLD}uv run python -m gemini_hackathon.cli${C_RESET})
  3. Launch notebooks:   ${C_BOLD}uv run marimo edit notebooks/${C_RESET}
  4. Run the test suite: ${C_BOLD}uv run pytest tests/ -v${C_RESET}
  5. Or use the Makefile: ${C_BOLD}make help${C_RESET}
EOF