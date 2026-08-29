"""gemini_hackathon.journey — the British Isles Journey.

The 6-level immersive progressive educational experience that drives
participants through the official syllabus processing pipeline across
all 8 British Isles subnations.

This package is a "Level 0–5 codelab + Cloud Build deploy" mirror of the
Way Back Home pattern (`docs/adk-examples/way-back-home/`), but
re-anchored on the existing gemini_hackathon pipeline:

    Level 0: Pick your subnation          (theming + Firestore session)
    Level 1: Extract the syllabus         (BAML + Vertex embed + VectorTarget)
    Level 2: OCR a past paper             (4-path GCP-native ensemble)
    Level 3: Mark an answer               (ADK 2 Pillar 1 + JoinNode + BAML)
    Level 4: Update the mastery ledger     (Firestore 4-backend fan-out)
    Level 5: Generate an asset from the    (BAML extract + FIBO JSON-native
              syllabus content the user       image gen, ALL 14 subjects x
              asked about                      5 stages prompt bank)

Level 5 was originally "mint the certificate" in the plan; per the user's
reframing, it's now "generate a personalized asset based on the user's
question grounded in the actual syllabus content" — a more pedagogically
useful outcome than a certificate (the syllabus pipeline's *purpose* is
to ground AI output in the official specification, so the natural
demonstration is "ask anything, get an asset informed by the curriculum").

Package layout (mirrors Way Back Home's level_0..level_5 + dashboard split):

    journey/
    ├── README.md                        single entry-point doc
    ├── cloudbuild.yaml                  Cloud Build pipeline (publishes all 6 levels)
    ├── journey.config.json              workshop metadata schema
    ├── scripts/                         setup.sh / verify.sh / admin_create_event.py /
    │                                    progress.py / deploy_journey.sh
    ├── level_0_pick_subnation/          Gradio app + customize.py + #REPLACE markers
    ├── level_1_syllabus_extraction/     BAML -> Vertex embed -> VectorTarget
    ├── level_2_past_paper_ocr/          4-path ensemble + consensus_vote
    ├── level_3_marking_scheme/          Pillar1GradingWorkflow + JoinNode + BAML
    ├── level_4_mastery_update/          MasteryLedger.update_mastery + 4-backend fan-out
    ├── level_5_asset_generation/        BAML question -> FIBO asset
    ├── journey_orchestrator/            ADK 2 Workflow chaining all 6 levels
    │   ├── callback_before_agent.py     canonical before_agent_callback
    │   ├── session_service.py           VertexAiSessionService
    │   ├── memory_service.py            VertexAiMemoryBankService (optional)
    │   └── workflow.py                  the chained Workflow(edges=[...])
    └── tests/                           8 integration + per-level tests

ADK 2 patterns used (per docs/adk-examples/):
    - adk2-tutorial/L0_first_agent     -- one Agent + Runner + one tool (Level 0's
                                          before_agent_callback state template)
    - adk2-tutorial/L1_graph_basics  -- function node + agent node in one
                                          edges list (each level)
    - adk2-tutorial/L2a_parallel_join -- ParallelAgent + JoinNode (Level 3)
    - adk2-tutorial/L2b_router        -- deterministic dict-edge router
                                          (subject -> 14 specialists in L1)
    - way-back-home/level_1         -- multi-agent root + state templating
                                          (Level 4's MasteryLedger fan-out)
    - monstertix/MODULE 5-6         -- LongRunningFunctionTool +
                                          ResumabilityConfig + Workflow
                                          chains (Level 5's asset gen)
    - loop-lab-table/hello_workflow -- RequestInput human-in-the-loop pause
                                          (between Level 4 and Level 5)
    - support-memory-lab/r3        -- Memory Bank for long-term learner
                                          memory across workshop runs
"""
