# 2026-08-27-hf-spaces-headline-demos-v1

> HF Spaces (5 headline demos at cianfhoghlaim/gemini_hackathon_*)

## Why

The 5 per-stage editorial canvases need to be publishable to Hugging Face Spaces for judge-shareable evaluation.

## What changes

Created hf_spaces/ with _generate.py (the shared generator) + 5 Space directories (gemini_hackathon_aistear / bunscoil / junior_cycle / leaving_certificate / editorial_studio) each with README.md (HF frontmatter) + app.py + requirements.txt.

## Acceptance
- All 5 Spaces pass the validation smoke test (README has frontmatter, app.py imports gradio, requirements.txt pins gradio 5.28+).