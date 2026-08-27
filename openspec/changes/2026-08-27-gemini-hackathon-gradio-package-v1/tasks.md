# Tasks

## Status: closed

## Workstream: W3

- [x] **Why**: The Celtic-themed 5 Spaces in sruth/spaces/ were the closest existing pattern for the 5-stage editorial studios. Lift + rewrite for the British Isles education theme.
- [x] **Scope**: Created gemini_hackathon_gradio/ with _common/ library (theme, baml_client, pclm_emitter, hlml_emitter, i18n, baml_pydantic_bridge, anam_bonneagar, hf_hub_push, demo_recorder) + 5 studios (an_scrudu, ...
- [x] **Acceptance**: All non-Gradio modules import cleanly; the 5 studios + shared library pass smoke tests; lazy `__getattr__` for build_app so Gradio is optional.