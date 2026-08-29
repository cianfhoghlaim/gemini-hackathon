"""journey — top-level Python package (sibling of gemini_hackathon/).

Mirrors Way Back Home's `level_0/`-through-`level_5/` + `scripts/` +
`dashboard/` flat-layout: each level is its own directory with its own
`pyproject.toml` + `app.py` + `customize.py`, the orchestrator is a
package, and the scripts are runnable via `python -m journey.scripts.X`.

Package layout (matches what was actually written to disk):

    journey/
    ├── __init__.py                      (this file)
    ├── README.md                        (single entry-point doc for participants)
    ├── cloudbuild.yaml                  (Cloud Build pipeline for the 6 levels + orchestrator)
    ├── journey.config.json              (workshop metadata schema)
    ├── scripts/
    │   ├── __init__.py
    │   ├── setup.sh                      (one command: venv + ADC + .env + Firestore seed + Vertex check)
    │   ├── verify.sh                     (8-tick smoke gate)
    │   ├── admin_create_event.py         (writes journeys/{event_code} Firestore doc)
    │   ├── progress.py                   (per-learner progress + workshop leaderboard)
    │   └── deploy_journey.sh             (end-to-end Cloud Build + deploy + seed + smoke)
    ├── level_0_pick_subnation/           (Gradio app + customize.py + #REPLACE markers)
    ├── level_1_syllabus_extraction/      (BAML -> Vertex embed -> VectorTarget)
    ├── level_2_past_paper_ocr/           (4-path ensemble + consensus_vote)
    ├── level_3_marking_scheme/           (Pillar1GradingWorkflow + JoinNode + BAML)
    ├── level_4_mastery_update/           (MasteryLedger.update_mastery + 4-backend fan-out)
    ├── level_5_asset_generation/         (BAML question -> FIBO asset)
    ├── journey_orchestrator/             (ADK 2 Workflow chaining all 6 levels)
    └── tests/                            (8 integration + per-level tests)

The actual level bodies live in `gemini_hackathon/journey/*` (one
package, re-exported). The CLIs in `journey/scripts/*` are the thin
wrappers — they call into `gemini_hackathon.journey.*` so that
`import journey.scripts.progress` and `import gemini_hackathon.journey.scripts.progress`
both work (the former is what the README + codelabs document; the latter
is the canonical Python import).
"""
