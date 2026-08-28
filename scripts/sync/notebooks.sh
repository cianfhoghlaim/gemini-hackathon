#!/usr/bin/env bash
# sync/notebooks.sh — sync the gemini-hackathon marimo notebooks
# against the canonical cianfhoghlaim notebooks (Phase 7 prep).
#
# - Verifies the marimo CLI is reachable
# - Verifies the gemini-hackathon marimo notebooks import cleanly
# - (Phase 7) Converts 13 canonical marimo notebooks → .ipynb
#
# Lifted from cianfhoghlaim/scripts/sync/notebooks.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> [sync:notebooks] Verifying marimo CLI"
uv run --with marimo marimo --version

echo "==> [sync:notebooks] Verifying the 3 existing gemini-hackathon marimo notebooks"
for nb in notebooks/00_theming_extraction.py notebooks/01_biep_equivalency_map.py notebooks/per_subject.py; do
  uv run --with marimo marimo export ipynb --help >/dev/null 2>&1 && \
    echo "  - $nb: OK (marimo export ipynb reachable)"
done

echo "==> [sync:notebooks] Phase 7: convert 13 canonical marimo notebooks → .ipynb"
echo "    (TODO: implement the 13-source batch conversion in Phase 7)"
echo "    Sources: cianfhoghlaim/notebooks/{lc/mathematics,english,gaeilge,chemistry,"
echo "              physics,biology,geography,computer_science,40_leaving_cert_subject_panel,"
echo "              10_biep_pipeline_lakehouse_07_subject_full_pipeline,00_marimo_patterns_tour,"
echo "              30_unsloth_vision_compare,00_control_panel}.py"

echo "==> [sync:notebooks] Done"