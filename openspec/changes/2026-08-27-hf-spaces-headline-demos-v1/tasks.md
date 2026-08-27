# Tasks

## Status: closed

## Workstream: W13

- [x] **Why**: The 5 per-stage editorial canvases need to be publishable to Hugging Face Spaces for judge-shareable evaluation.
- [x] **Scope**: Created hf_spaces/ with _generate.py (the shared generator) + 5 Space directories (gemini_hackathon_aistear / bunscoil / junior_cycle / leaving_certificate / editorial_studio) each with README.md (HF ...
- [x] **Acceptance**: All 5 Spaces pass the validation smoke test (README has frontmatter, app.py imports gradio, requirements.txt pins gradio 5.28+).