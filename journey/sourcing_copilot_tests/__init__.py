"""journey.sourcing_copilot_tests — tests for the SourcingCopilot.

Per the `2026-08-31-journey-gradio-polish-v1` openspec change, this
package tests the 7 canonical tools in `gemini_hackathon/journey/
sourcing_copilot/tools.py` + the `build_copilot_agent()` factory in
`gemini_hackathon/journey/sourcing_copilot/agent.py`.

All tests run offline (no GCP / network access required) — the tools
fall back to the in-memory Firestore when `GOOGLE_CLOUD_PROJECT` is not
set, and `BAML_TEST_MODE=true` makes the BAML client use the canonical
`TestMock` stub.
"""
