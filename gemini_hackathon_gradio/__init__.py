"""gemini_hackathon_gradio — the British Isles Education Gradio studios.

Lifted from `sruth/spaces/_common/` + the 5 Spaces, and rewritten for the
5-stage British Isles education theme.

Studios (each is a `build_app()` function returning a `gr.Blocks`):
  - an_scrudu                 — LC past-paper heatmap (lifted + rewritten)
  - anam_education            — 7-feature integration studio
  - oideachais_mission_control — 5-stage mission control
  - oideachais_pdf_review     — human review of Stage-4 mismatches
  - editorial_studio          — the big editorial canvas (Cloud Run, W12)

Sub-packages:
  - _common          — the shared library (theme, baml_client, etc.)
  - an_scrudu        — past-paper heatmap studio
  - anam_education    — integration studio
  - oideachais_mission_control — 5-stage control
  - oideachais_pdf_review     — human review
  - editorial_studio  — headline canvas (W12)

The top-level `__init__.py` lazily imports the studio app builders so
the package is importable without Gradio installed (for tests + dev).
Use `gemini_hackathon_gradio.build_an_scrudu_app()` etc. after
`pip install gradio` to launch the studios.
"""

from __future__ import annotations

__all__ = [
    "build_an_scrudu_app",
    "build_anam_education_app",
    "build_editorial_studio_app",
    "build_oideachais_mission_control_app",
    "build_oideachais_pdf_review_app",
    "build_workflow_canvas",
]


def __getattr__(name: str):
    """Lazily import studio app builders (require Gradio)."""
    if name == "build_an_scrudu_app":
        from gemini_hackathon_gradio.an_scrudu.app import build_app

        return build_app
    if name == "build_anam_education_app":
        from gemini_hackathon_gradio.anam_education.app import build_app

        return build_app
    if name == "build_oideachais_mission_control_app":
        from gemini_hackathon_gradio.oideachais_mission_control.app import build_app

        return build_app
    if name == "build_oideachais_pdf_review_app":
        from gemini_hackathon_gradio.oideachais_pdf_review.app import build_app

        return build_app
    if name == "build_editorial_studio_app":
        from gemini_hackathon_gradio.editorial_studio.app import build_app

        return build_app
    if name == "build_workflow_canvas":
        from gemini_hackathon_gradio.editorial_studio.app import build_workflow_canvas

        return build_workflow_canvas
    raise AttributeError(f"module 'gemini_hackathon_gradio' has no attribute {name!r}")
