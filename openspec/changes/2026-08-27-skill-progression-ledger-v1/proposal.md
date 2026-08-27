# 2026-08-27-skill-progression-ledger-v1

        > Skill-progression ledger (Convex + LanceDB + FalkorDB)

        ## Why

        The LC/JC certificate needs a per-learner mastery ledger that the editorial canvas + the W14 certificate pipeline can read.

        ## What changes

        Created gemini_hackathon/ledger/ with types + 3 backends (Convex, Lance, Falkor) + MasteryLedger facade. 320-dim mastery vectors (5 × 8 × 4 × 2). 8 LC Mathematics graph nodes seeded.

        ## Acceptance
        - All backends import cleanly
- MasteryLedger.default() builds a consistent in-memory stack
- update_mastery() writes to all 4 (best-effort)
- get_learner_state() reads all 4.