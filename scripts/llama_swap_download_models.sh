#!/usr/bin/env bash
# =============================================================================
# llama_swap_download_models.sh — Gemma+Gemini refocus (2026-08-30)
# =============================================================================
# Downloads the 7 active llama-swap GGUFs from HuggingFace into
# downloaded_models/gguf/<model_dir>/. Idempotent — skips files already
# present. Sources ONLY from huggingface.co/<owner>/<repo>; NO HF Inference
# API (per the refocus directive).
#
# Mapping is the single source of truth for the litellm/llama-swap config.
# If you change this, change infra/stacks/llama-swap/config.yaml too.
#
# Usage:
#   ./scripts/llama_swap_download_models.sh           # download all
#   ./scripts/llama_swap_download_models.sh --dry-run  # print what would happen
#
# Requires: HF_TOKEN env var (or `uv run huggingface-cli login` first).
# Total: ~36 GB on disk.
# =============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEST="${REPO_ROOT}/downloaded_models/gguf"

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

mkdir -p "${DEST}"

# ----------------------------------------------------------------------------
# GGUF catalogue (one per line: model_dir|hf_repo|files-comma-separated)
# Read with a while-loop so bash doesn't choke on the colons in the values.
# ----------------------------------------------------------------------------
MODEL_CATALOGUE=$(cat <<'EOF'
gemma-4-26b-a4b-vision|google/gemma-4-26B-A4B-it|gemma-4-26b-a4b-it-q4_k_m.gguf,gemma-4-26b-a4b-it-mmproj-f16.gguf
gemma-4-12b-vision|google/gemma-4-12b-it|gemma-4-12b-it-q4_k_m.gguf
gemma-4-e4b-vision|google/gemma-4-E4B-it|gemma-4-e4b-it-q4_k_m.gguf
gemma-3-12b-vision|google/gemma-3-12b-it|gemma-3-12b-it-q4_k_m.gguf
gemma-2-9b|google/gemma-2-9b|gemma-2-9b-it-q4_k_m.gguf
gemma-3-1b|google/gemma-3-1b-it|gemma-3-1b-it-q4_k_m.gguf
z-image-turbo|stabilityai/z-image-turbo|z-image-turbo-q4_k_m.gguf
EOF
)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

bold()   { printf '\033[1m%s\033[0m\n' "$*"; }
ok()     { printf '  \033[32m✓\033[0m  %s\n' "$*"; }
warn()   { printf '  \033[33m!\033[0m  %s\n' "$*"; }
fail()   { printf '  \033[31m✗\033[0m  %s\n' "$*" >&2; exit 1; }

hf_token_args=()
if [[ -n "${HF_TOKEN:-}" ]]; then
  hf_token_args=(--token "${HF_TOKEN}")
fi

download_one() {
  local model_dir="$1"
  local hf_repo="$2"
  local fname="$3"
  local dest_dir="${DEST}/${model_dir}"
  mkdir -p "${dest_dir}"

  if [[ -f "${dest_dir}/${fname}" ]]; then
    ok "skip ${model_dir}/${fname} (already present)"
    return
  fi

  if [[ ${DRY_RUN} -eq 1 ]]; then
    printf '  DRY  %s -> %s/%s\n' "${hf_repo}" "${model_dir}" "${fname}"
    return
  fi

  printf '  →  %s/%s ... ' "${hf_repo}" "${fname}"
  if uv run --no-sync huggingface-cli download "${hf_repo}" "${fname}" \
        --local-dir "${dest_dir}" "${hf_token_args[@]}" \
        >/dev/null 2>&1; then
    printf '\033[32mok\033[0m\n'
  else
    printf '\033[31mfail\033[0m\n'
    warn "could not download ${hf_repo}/${fname}; check HF_TOKEN + the repo exists"
  fi
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

bold "llama-swap GGUF downloader — Gemma+Gemini refocus (2026-08-30)"
echo "  destination: ${DEST}"
echo "  total GGUFs: ${total_models}"
echo "  dry_run:     ${DRY_RUN}"
echo ""

if [[ ${DRY_RUN} -eq 0 ]] && ! command -v uv >/dev/null 2>&1; then
  fail "uv not found on PATH (required to call huggingface-cli)"
fi

total_models=$(printf '%s\n' "${MODEL_CATALOGUE}" | wc -l | tr -d ' ')

while IFS='|' read -r model_dir hf_repo filenames; do
  [[ -z "${model_dir}" ]] && continue
  for fname in ${filenames//,/ }; do
    download_one "${model_dir}" "${hf_repo}" "${fname}"
  done
done <<< "${MODEL_CATALOGUE}"

echo ""
if [[ ${DRY_RUN} -eq 1 ]]; then
  bold "Dry run complete. Re-run without --dry-run to actually download."
else
  bold "Download complete. Verify with:"
  echo "  ls -lh ${DEST}/"
  echo "  du -sh ${DEST}/*"
fi
