"""gemini_hackathon.journey.level_0_pick_subnation — the onboarding level.

Level 0 of the British Isles Journey: the participant chooses their
subnation (1 of 8), auto-applies the matching palette, and writes their
first Firestore document. Mirrors `docs/adk-examples/way-back-home/
level_0/create_identity.py`'s structure (a one-shot Python script with
`#REPLACE` markers a workshop participant fills in).

This level uses these ADK 2 patterns:
    - `before_agent_callback` (per adk2-tutorial/L0_first_agent + way-back-home
      level_0's setup.sh + customize.py pattern)
    - `{key}` state templating: the picked subnation becomes
      `{state.subnation}` for every downstream level

The actual codelab doc (with the 3 `#REPLACE` markers a participant fills in)
lives at `docs/journey/01_level_0_pick_subnation.md`.
"""
