#!/usr/bin/env bash
# verify.sh — the 8-tick smoke gate. Run before any workshop host trusts anything.
#
# Same shape as Way Back Home's verify.sh: each tick is a one-line
# `python -c "..."` that prints OK or FAIL. Mirrors `journey/scripts/
# setup.sh` step 8.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d .venv ]; then
    echo "verify: .venv missing — run setup.sh first"
    exit 1
fi
source .venv/bin/activate

_t=0
_ok() { echo "  [OK]   $1"; _t=$((_t+1)); }
_fail() { echo "  [FAIL] $1"; }
_section() { echo ""; echo "=== $1 ==="; }

# ── 1. Imports ────────────────────────────────────────────────────────
_section "1. Imports"
.venv/bin/python -c "
import importlib, sys
modules = [
    'gemini_hackathon.theming',
    'gemini_hackathon.agents.registry',
    'gemini_hackathon.knowledge_graph',
    'gemini_hackathon.ledger',
    'gemini_hackathon.ocr',
    'gemini_hackathon.ocr_ensemble',
    'gemini_hackathon.certificate',
    'cocoindex_flows._factory.four_stage',
    'cocoindex_flows._factory.bi_jurisdiction',
    'baml_client',
]
for m in modules:
    importlib.import_module(m)
print('OK')
" && _ok "every gemini_hackathon module imports" || _fail "import failed (see traceback above)"

# ── 2. Theming registry has the 8 subnations ──────────────────────────
_section "2. Theming registry"
.venv/bin/python -c "
from gemini_hackathon.theming import list_all_palettes
palettes = list_all_palettes()
assert len(palettes) >= 13, f'expected >=13 palettes, got {len(palettes)}: {palettes}'
print(f'OK: {len(palettes)} palettes loaded')
" && _ok "theming has >=13 palettes" || _fail "theming has too few palettes"

# ── 3. SUBJECT_WIRING_REGISTRY ────────────────────────────────────────
.venv/bin/python -c "
from gemini_hackathon.agents.registry import SUBJECT_WIRING_REGISTRY
n = len(SUBJECT_WIRING_REGISTRY)
print(f'OK: {n} subjects wired')
" && _ok "subject registry loaded" || _fail "subject registry missing"

# ── 4. OCR dispatch table has 7 capabilities ────────────────────────
.venv/bin/python -c "
from gemini_hackathon.ocr import _DISPATCH_TABLE, Capability
assert len(_DISPATCH_TABLE) == 7
assert {c.value for c in _DISPATCH_TABLE} == {
    'forms', 'layout', 'tables+latex', 'doctags',
    'gaelic', 'english', 'tesseract-fallback'
}
print('OK')
" && _ok "OCR dispatch table has 7 capabilities" || _fail "OCR dispatch table wrong"

# ── 5. 4-stage factory manifest ──────────────────────────────────────
.venv/bin/python -c "
from cocoindex_flows._factory.four_stage import get_4_stage_manifest
m = get_4_stage_manifest()
assert m['total_apps'] >= 100, f'expected >=100 Apps, got {m[\"total_apps\"]}'
print(f'OK: {m[\"total_apps\"]} Apps across 4 stages')
" && _ok "4-stage factory has >=100 Apps" || _fail "4-stage factory low count"

# ── 6. MasteryLedger facade ──────────────────────────────────────────
.venv/bin/python -c "
import asyncio
from gemini_hackathon.ledger import MasteryLedger
from gemini_hackathon.ledger.types import MasteryRecord, MasteryUpdate

async def main():
    ledger = MasteryLedger.default()
    record = MasteryRecord(
        learner_id='verify-script',
        subject_slug='mathematics',
        learning_outcome_code='MA-LC-MA-1.1',
        stage='scoil_sinsearach',
        mastery_score=0.5,
        key_competency_codes=['communicating'],
    )
    await ledger.update_mastery(MasteryUpdate(record=record, delta=0.1))
    state = await ledger.get_learner_state('verify-script')
    return len(state['achievements'])

n = asyncio.run(main())
assert n >= 1, f'expected >=1 achievement, got {n}'
print(f'OK: {n} achievement(s) written')
" && _ok "MasteryLedger round-trip works" || _fail "MasteryLedger failed"

# ── 7. OCR ensemble consensus ────────────────────────────────────────
.venv/bin/python -c "
from gemini_hackathon.ocr_ensemble import EnsemblePathOutput, consensus_vote
p1 = EnsemblePathOutput(path='document_ai', raw_response='the cat sat on the mat today')
p2 = EnsemblePathOutput(path='gemini_vision', raw_response='the cat sat on the mat today')
p3 = EnsemblePathOutput(path='gemma4_vertex', raw_response='completely unrelated text here')
winner, score, text = consensus_vote([p1, p2, p3])
assert winner in ('document_ai', 'gemini_vision'), f'winner should be one of the two agreeing paths, got {winner}'
assert score > 0
print(f'OK: winner={winner}, score={score:.2f}')
" && _ok "OCR ensemble consensus vote" || _fail "consensus vote wrong"

# ── 8. Journey config + subnation table ───────────────────────────────
.venv/bin/python -c "
import json
from pathlib import Path
cfg = json.loads(Path('journey/journey.config.json').read_text())
assert cfg['default_subnation'] in ('ireland', 'england')
assert len(cfg['levels_unlocked']) == 6
print(f'OK: event={cfg[\"event_code\"]}, default={cfg[\"default_subnation\"]}')
" && _ok "journey config loads" || _fail "journey config broken"

echo ""
echo "=== Result ==="
echo "$_t/8 ticks green"
if [ "$_t" -lt 8 ]; then
    echo "FAIL — fix above before continuing"
    exit 1
fi
echo "All ticks green ✓"
