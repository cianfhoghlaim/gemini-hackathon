# 2026-08-27-defer-ni-wales-scotland-iom-v1

        > Deferred NI / Wales / Scotland / IoM (Phase 2)

        ## Why

        Per the user's instruction: the hackathon ships Ireland + England only. The other 4 active subnations (NI / Wales / Scotland / IoM) require live scraping + DLT pipeline additions that aren't feasible within the hackathon window.

        ## What changes

        Records the deferred 4 subnations in subnations.py (Phase 2 tag) and in gemini_hackathon/subnations.py. A future openspec change at the cianfhoghlaim monorepo level will lift the relevant DLT sources + BAML schemas.

        ## Acceptance
        - All 4 Phase 2 subnations are tagged correctly
- the hackathon's get_hackathon_subnations() returns only Ireland + England.