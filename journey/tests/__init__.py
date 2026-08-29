"""journey.tests — the Journey's pytest suite.

Eight integration tests covering:
  - the orchestrator end-to-end (`test_journey_workflow.py`)
  - one happy-path + one error-tolerance test per level (6 levels)

All tests are designed to pass **without GCP credentials** — the in-memory
fallbacks every backend ships with (Firestore / MasteryLedger / Vertex AI
embedding stubs) make the offline path fully exercised.

Run:
    uv run pytest journey/tests/ -v
"""
