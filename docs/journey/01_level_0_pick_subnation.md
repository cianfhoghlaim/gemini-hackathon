# Level 0 — Pick your subnation

> **The 5-minute onboarding.** Choose your jurisdiction (1 of 8),
> auto-apply the matching palette, write your first Firestore doc. After
> this your `{subnation}` + `{learner_id}` are wired into state for
> every downstream level.

## What you'll learn

| Concept | Source |
|---|---|
| **before_agent_callback** | `adk2-tutorial/L0_first_agent` + `way-back-home/level_0` |
| **{key} state templating** | The `{subnation}` you pick here becomes `{state.subnation}` in every downstream level's `instruction="..."` |
| **Firestore session** | The participant's progress doc is the canonical per-event, per-learner state |

## What you'll build

By the end of Level 0:
- A `journeys/{event_code}/participants/{uid}` Firestore document
- The matching subnation palette applied to the studio's CSS variables
- Your `{subnation}` ready for Level 1's `ExtractCurriculumSyllabus` BAML call

## The 3 `#REPLACE-*` markers

Open `gemini_hackathon/journey/level_0_pick_subnation/app.py` (or the
`/journey/level_0_pick_subnation/app.py` mirror at the repo root) and
find these 3 markers. The codelab walks you through each one.

### REPLACE-1 — the Firestore write call (~5 minutes)

In `write_learner_profile()`. The stub uses an in-memory dict so the
workshop runs offline. The real implementation:

```python
client = _get_firestore_client()
if client is not None:
    doc = _build_learner_doc(learner_id, display_name, subnation, palette_file)
    client.collection("journeys").document(event_code) \\
        .collection("participants").document(learner_id).set(doc)
    return doc
# else: fall through to the in-memory stub below
```

### REPLACE-2 — the palette call (~2 minutes)

In `_apply_palette()`. The stub returns a dict placeholder. The real
implementation:

```python
from gemini_hackathon.theming import apply_palette_for_subnation
return apply_palette_for_subnation(subnation)
```

### REPLACE-3 — the display name placeholder (~1 minute)

In the `display_name_in` Gradio `gr.Textbox` `placeholder=` argument.
Replace `(REPLACE-3: enter your display name)` with your real display
name (or just your workshop handle).

## Quickstart

```bash
# 1. Pre-flight (no GCP needed)
python journey/level_0_pick_subnation/customize.py

# 2. Fill in the 3 REPLACE markers

# 3. Launch the studio (needs Gradio)
python journey/level_0_pick_subnation/app.py --port 7860

# 4. In the UI:
#    - Email:    alice@school.ie
#    - Display:  Alice O'Brien
#    - Subnation: Ireland (NCCA)
#    - Click "Onboard me →"
#
# 5. Check the Firestore doc landed:
python -m journey.scripts.progress \\
    --event-code $JOURNEY_EVENT_CODE \\
    --learner-id alice@school.ie
```

## The 8 subnations (matches `gemini_hackathon/session/schema.py`)

| Slug | Display | Palette file |
|---|---|---|
| `ireland` | Ireland (NCCA) | `ncca_palette.json` |
| `england` | England (AQA + OCR + Pearson) | `aqa_palette.json` |
| `northern_ireland` | Northern Ireland (CCEA) | `northern_ireland_palette.json` |
| `scotland` | Scotland (SQA) | `scotland_palette.json` |
| `wales` | Wales (WJEC) | `wales_palette.json` |
| `jersey` | Jersey (States of Jersey) | `jersey_palette.json` |
| `guernsey` | Guernsey (States of Guernsey) | `guernsey_palette.json` |
| `isle_of_man` | Isle of Man (DESC) | `isle_of_man_palette.json` |

Each subnation drives which BAML extraction function runs at Level 1
(e.g. NCCA's `ExtractCurriculumSyllabus` for Ireland, WJEC's
`ExtractWalesSyllabus` for Wales), which OCR path runs at Level 2
(CCEA for NI vs SQA for Scotland differ), and which marking scheme runs
at Level 3. **Pick wisely — your Journey is now scoped.**

## What the verify gate checks (after Level 0)

```
$ ./journey/scripts/verify.sh
=== 2. Theming registry ===
  [OK]   theming has >=13 palettes
=== 3. SUBJECT_WIRING_REGISTRY ===
  [OK]   subject registry loaded
...
```

The theming registry tick (#2) ensures all 13+ palette files exist; the
subject registry tick (#3) ensures the 14 NCCA subjects are wired. If
either is missing, Level 0's `_apply_palette` stub won't have a real
one to wire into for REPLACE-2.
