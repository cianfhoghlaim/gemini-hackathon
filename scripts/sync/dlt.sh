#!/usr/bin/env bash
# sync/dlt.sh — sync the gemini-hackathon DLT pipelines against the canonical
# cianfhoghlaim patterns (Phase 1.4-1.7 lift).
#
# - Verifies the named destinations resolve
# - Verifies the 8 NCCA LC subjects have a factory function
# - Verifies the manifest JSONs parse
#
# Lifted from cianfhoghlaim/scripts/sync/dlt.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> [sync:dlt] Verifying named destinations"
uv run --no-sync python -c "
from dlt_pipelines._shared import list_named_destinations, get_named_destination
for name in list_named_destinations():
    print(f'  - {name}: {get_named_destination(name)}')
"

echo "==> [sync:dlt] Verifying 8 NCCA LC subject factories"
uv run --no-sync python -c "
from dlt_pipelines.ireland.subjects import (
    create_mathematics_source, create_english_source,
    create_gaeilge_source, create_chemistry_source,
    create_geography_source, create_physics_source,
    create_biology_source, create_computer_science_source,
)
for fn in [create_mathematics_source, create_english_source, create_gaeilge_source,
           create_chemistry_source, create_geography_source, create_physics_source,
           create_biology_source, create_computer_science_source]:
    pages, pdfs = fn()
    print(f'  - {fn.__name__}: pages={pages.name} pdfs={pdfs.name}')
"

echo "==> [sync:dlt] Verifying manifest JSONs parse"
uv run --no-sync python -c "
from dlt_pipelines.ireland._manifest import lookup, all_stages, all_lc_subjects, all_active_subjects
print(f'  - stages: {len(all_stages())}')
print(f'  - lc_subjects (all): {len(all_lc_subjects())}')
print(f'  - lc_subjects (active for hackathon): {len(all_active_subjects())}')
print(f'  - lookup(scoil_sinsearach, mathematics): {lookup(\"scoil_sinsearach\", \"mathematics\")[\"name_en\"]}')
"

echo "==> [sync:dlt] Verifying IrelandJurisdictionPipeline yields cohorts"
uv run --no-sync python -c "
from dlt_pipelines._base.jurisdiction_pipeline_base import IrelandJurisdictionPipeline
pipeline = IrelandJurisdictionPipeline()
cohorts = list(pipeline.cohorts())
print(f'  - yielded {len(cohorts)} (stage × subject × language) cohorts')
print(f'  - first: {cohorts[0].pipeline_key}')
print(f'  - last: {cohorts[-1].pipeline_key}')
"

echo "==> [sync:dlt] Done"