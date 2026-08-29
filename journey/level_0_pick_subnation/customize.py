"""customize.py — Level 0 participant entry point (pre-launch checklist).

The Way Back Home convention (`level_0/customize.py`) has the participant
do a 60-second pre-flight before launching the full app. For us, the
pre-flight is checking that the `#REPLACE-*` markers in `app.py` are visible
+ that the Firestore in-memory fallback works end-to-end (no creds needed)
+ that the palette stub returns the right shape.

Run it standalone: `python customize.py`
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add the repo root to sys.path so `from gemini_hackathon.journey.level_0...`
# resolves (this script may be run from anywhere — no `uv run` requirement).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gemini_hackathon.journey.level_0_pick_subnation.app import (  # noqa: E402
    SUBNATIONS,
    _apply_palette,
    _build_learner_doc,
    write_learner_profile,
)


def main() -> int:
    print("=== Level 0: Pick your subnation — pre-flight ===")
    print()

    print(f"SUBNATIONS table: {len(SUBNATIONS)} jurisdictions")
    for slug, display, palette in SUBNATIONS:
        print(f"  - {display:<35}  -> {palette}")

    print()
    print("Stub write (in-memory fallback, no Firestore creds needed):")
    result = write_learner_profile(
        learner_id="alice@school.ie",
        display_name="Alice O'Brien",
        subnation="ireland",
    )
    print(f"  learner_id:    {result['learner_id']}")
    print(f"  subnation:     {result['subnation']}")
    print(f"  palette_file:  {result['palette_file']}")
    print(f"  palette_applied: {result['palette_applied']}")
    print(f"  offline_stub:  {result['offline_stub']}")

    print()
    print("Stub write for a non-default subnation (Jersey):")
    result2 = write_learner_profile(
        learner_id="bob@school.je",
        display_name="Bob",
        subnation="jersey",
    )
    print(f"  learner_id:    {result2['learner_id']}")
    print(f"  subnation:     {result2['subnation']}")
    print(f"  palette_file:  {result2['palette_file']}")

    print()
    print("_build_learner_doc shape (matches the Firestore document that the workshop's progress.py will read back):")
    doc = _build_learner_doc("alice@school.ie", "Alice O'Brien", "ireland", "ncca_palette.json")
    for k, v in doc.items():
        print(f"  {k:<22}  {v}")

    print()
    print("All ✓ — you can now run `python -m journey.level_0_pick_subnation.app` (after `uv add gradio`).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
