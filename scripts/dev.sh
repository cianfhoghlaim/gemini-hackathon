#!/usr/bin/env bash
# scripts/dev.sh — one-shot local dev bootstrap for gemini_hackathon.
#
# Mirrors the journey/scripts/setup.sh pattern. Idempotent. Safe to
# re-run. Logs progress to stdout; exits non-zero on failure. Wraps
# the canonical Google 5-step local dev recipe from docs/LOCAL_DEV.md:
#
#   1. Install uv (the 2026 standard Python package manager)
#   2. Sync dependencies (`make install`)
#   3. Copy .env.example → .env
#   4. Regenerate + test the BAML client (`make baml`)
#   5. Run the 8-tick verify gate (`make verify`)
#
# Usage:
#   ./scripts/dev.sh                 # full bootstrap + verify
#   ./scripts/dev.sh --no-verify     # bootstrap only, skip the verify pass
#   make setup                       # the Makefile alias

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
            sed -n '2,25p' "$0"
            exit 0
            ;;
        *) fail "Unknown argument: $arg" ;;
    esac
done

# ---------------------------------------------------------------------------
# Locate repo root (script may be invoked from anywhere)
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

banner "gemini_hackathon — local dev bootstrap"

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
        fail "Neither curl nor wget available; install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
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

banner "[2/5] uv sync (deps + dev + docs + lint groups)"

if [[ ! -f "pyproject.toml" ]]; then
    fail "pyproject.toml not found in $REPO_ROOT — are you in the project root?"
fi

make install
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
# 4. BAML codegen + tests
# ---------------------------------------------------------------------------

banner "[4/5] BAML codegen + tests"

if make baml >/dev/null 2>&1; then
    ok "BAML client generated + tests pass"
else
    warn "make baml exited non-zero — check baml_extracts/*.baml syntax"
fi

# ---------------------------------------------------------------------------
# 5. Verify (the 8-tick gate)
# ---------------------------------------------------------------------------

if [[ "$VERIFY" -eq 1 ]]; then
    banner "[5/5] Verify (the 8-tick gate)"

    if make verify; then
        ok "All verify ticks green"
    else
        warn "Some verify ticks failed — see docs/LOCAL_DEV.md §'What to do when something breaks'"
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
  1. Edit .env with real API keys (GEMINI_API_KEY, GOOGLE_CLOUD_PROJECT, …)
  2. Bring up the lakehouse + observability stack:
        ${C_BOLD}make dev${C_RESET}    # docker compose up --build
  3. Run the data plane:
        ${C_BOLD}make dlt-smoke-all && make cocoindex-update${C_RESET}
  4. Launch the NCCE learning-graph Gradio studio:
        ${C_BOLD}make ncce-visualise${C_RESET}
  5. Or use the Python backend directly:
        ${C_BOLD}make backend${C_RESET}

  See ${C_BOLD}docs/LOCAL_DEV.md${C_RESET} for the full step-by-step recipe.
EOF