# Level 0 — Pick your subnation

> **The 5-minute onboarding.** Choose your jurisdiction (1 of 8), auto-apply
> the matching palette, write your first Firestore doc. After this your
> `{subnation}` + `{learner_id}` are wired into state for every downstream
> level.

This level adopts `docs/adk-examples/way-back-home/level_0/`'s shape
(one-shot Python entrypoint + `#REPLACE-*` markers the participant fills
in) but re-anchors on the **official syllabus processing pipeline**:
the chosen subnation drives which BAML extraction function runs at Level 1
(e.g. NCCA's `ExtractCurriculumSyllabus` for Ireland, WJEC's
`ExtractWalesSyllabus` for Wales), which OCR path runs at Level 2 (CCEA
for NI vs CCEA-sub-batches differ from SQA), and which marking-scheme
template runs at Level 3. Pick wisely — your Journey is now scoped.

## What you'll learn

| Concept | Description |
|---|---|
| **before_agent_callback** | The canonical ADK 2 pattern (per `adk2-tutorial/L0_first_agent`) that loads `{learner_id}` + `{subnation}` + `{event_code}` from Firestore into `ctx.state` before any level's agent runs |
| **{key} state templating** | The `{subnation}` you pick here becomes `{state.subnation}` in every downstream level's `instruction="..."` |
| **Cognee skill graph + Firestore Vector Search** | The Firestore document you write here is the same document your `MasteryLedger` (Level 4) will read from — the Journey's per-learner state is one document, five views |

## What you'll build

By the end of Level 0:
- A `journeys/{event_code}/participants/{uid}` Firestore document
- The matching subnation palette applied to the studio's CSS variables
- Your `{subnation}` ready for Level 1's `ExtractCurriculumSyllabus` BAML call

## Prerequisites

- `setup.sh` run successfully (gives you `GOOGLE_CLOUD_PROJECT` + a venv)
- `verify.sh` ticked all 8 boxes
- The `baml generate` step succeeded (you'll need the generated BAML client for Level 1)

## The 3 `#REPLACE-*` markers

Open `app.py` and find these 3 `#REPLACE-*` markers. The codelab walks you
through each one; here's the summary:

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

In the `display_name_in` Gradio `gr.Textbox` `placeholder=` argument. Replace
the `(REPLACE-3: enter your display name)` placeholder with your real
display name.

## Quickstart

```bash
# 1. Pre-flight check (no GCP needed)
python customize.py

# 2. Fill in the 3 REPLACE markers (open app.py in your editor)

# 3. Launch the studio
python -m journey.level_0_pick_subnation.app --port 7860

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

## What the verify gate checks (between Level 0 and Level 1)

```
$ ./journey/scripts/verify.sh
=== 1. Imports ===
  [OK]   every gemini_hackathon module imports
=== 2. Theming registry ===
  [OK]   theming has >=13 palettes
=== 3. SUBJECT_WIRING_REGISTRY ===
  [OK]   subject registry loaded
...
```

When all 8 ticks are green, move to Level 1.
