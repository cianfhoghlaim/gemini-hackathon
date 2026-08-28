#!/usr/bin/env bash
# convert_marimo_to_ipynb.sh — convert the 13 canonical marimo notebooks
# from cianfhoghlaim/notebooks/ → .ipynb for the gemini-hackathon repo.
#
# Source: cianfhoghlaim/notebooks/{lc/{mathematics,english,gaeilge,chemistry,
# physics,biology,geography,computer_science},40_leaving_cert_subject_panel,
# 10_biep_pipeline_lakehouse_07_subject_full_pipeline,00_marimo_patterns_tour,
# 30_unsloth_vision_compare,00_control_panel}.py
#
# Output: gemini_hackathon/notebooks/converted/*.ipynb
#
# Uses marimo 0.24 + nbformat (per the marimo export docs).

set -euo pipefail

CIANFHOGHLAIM_REPO="/Users/cianmacandeisigh/dev/cianfhoghlaim"
OUTPUT_DIR="/Users/cianmacandeisigh/dev/gemini_hackathon/notebooks/converted"

# The 13 (source_path:output_filename) pairs
sources=(
  "lc/mathematics.py:lc_mathematics.ipynb"
  "lc/english.py:lc_english.ipynb"
  "lc/gaeilge.py:lc_gaeilge.ipynb"
  "lc/chemistry.py:lc_chemistry.ipynb"
  "lc/physics.py:lc_physics.ipynb"
  "lc/biology.py:lc_biology.ipynb"
  "lc/geography.py:lc_geography.ipynb"
  "lc/computer_science.py:lc_computer_science.ipynb"
  "40_leaving_cert_subject_panel.py:leaving_cert_subject_panel.ipynb"
  "10_biep_pipeline_lakehouse_07_subject_full_pipeline.py:biep_subject_full_pipeline.ipynb"
  "00_marimo_patterns_tour.py:marimo_patterns_tour.ipynb"
  "30_unsloth_vision_compare.py:unsloth_vision_compare.ipynb"
  "00_control_panel.py:control_panel.ipynb"
)

mkdir -p "$OUTPUT_DIR"
ok=0
fail=0
for pair in "${sources[@]}"; do
  src="${pair%%:*}"; dst="${pair##*:}"
  out="${OUTPUT_DIR}/${dst}"
  cd "$CIANFHOGHLAIM_REPO"
  if uv run --with "marimo,nbformat" --no-sync marimo export ipynb "notebooks/${src}" -o "$out" 2>/dev/null; then
    size=$(stat -f %z "$out" 2>/dev/null || stat -c %s "$out" 2>/dev/null)
    echo "  ✓ ${src} → ${dst} (${size} bytes)"
    ok=$((ok+1))
  else
    echo "  ✗ ${src} FAILED"
    fail=$((fail+1))
  fi
done
echo "---"
echo "ok=$ok fail=$fail"