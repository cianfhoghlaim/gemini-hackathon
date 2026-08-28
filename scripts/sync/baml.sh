#!/usr/bin/env bash
# sync/baml.sh — sync the gemini-hackathon BAML contracts against the
# canonical cianfhoghlaim patterns (Phase 1.2-1.3 + Phase 4 lifts).
#
# - Regenerates the BAML client
# - Verifies the 5 canonical LC6 extraction functions resolve
# - Verifies the BIEP subject registry enums are present
#
# Lifted from cianfhoghlaim/scripts/sync/baml.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> [sync:baml] Regenerating BAML client"
uv run baml-cli generate 2>&1 | tail -5

echo "==> [sync:baml] Verifying the 5 canonical LC6 extraction functions"
uv run --no-sync python -c "
from baml_client.sync_client import b
import inspect
for fn_name in ['ExtractCurriculumSyllabus', 'ExtractExamPaperLayout',
               'ExtractMarkingSchemeGuideline', 'ExtractCrossLinguisticConcept',
               'ExtractSyllabusDiagram']:
    fn = getattr(b, fn_name, None)
    if fn is None:
        print(f'  - {fn_name}: MISSING')
    else:
        sig = inspect.signature(fn)
        print(f'  - {fn_name}{sig}')
"

echo "==> [sync:baml] Verifying the BIEP subject registry enums"
uv run --no-sync python -c "
from baml_client.types import (
    Jurisdiction, EducationalStage, AwardingBody, Language,
    CrossJurisdictionConcept, RegistrySource, RegistryStatus,
)
print(f'  - Jurisdiction: {len(list(Jurisdiction))} values')
print(f'  - EducationalStage: {len(list(EducationalStage))} values')
print(f'  - AwardingBody: {len(list(AwardingBody))} values')
print(f'  - Language: {len(list(Language))} values')
print(f'  - CrossJurisdictionConcept: {len(list(CrossJurisdictionConcept))} values')
"

echo "==> [sync:baml] Done"