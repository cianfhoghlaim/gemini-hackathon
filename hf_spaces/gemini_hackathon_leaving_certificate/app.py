"""
Scoil Sinsearach — Leaving Certificate (15-19) — the gemini_hackathon HF Space.

Headline surface for the leaving_certificate stage of the
British Isles Education Platform. The full editorial studio
runs on Cloud Run (see `gemini_hackathon_gradio/editorial_studio/deploy.py`)
— this Space is the smaller, shareable entry point.
"""

from __future__ import annotations

import logging
import os

import gradio as gr

_log = logging.getLogger(__name__)


def build_app():
    """Build the leaving_certificate Gradio app."""
    return gr.Blocks(
        title="Scoil Sinsearach — Leaving Certificate (15-19)",
        theme=gr.themes.Soft(primary_hue="orange", secondary_hue="yellow"),
    ) as demo:
        gr.Markdown("# Scoil Sinsearach — Leaving Certificate (15-19)")
        gr.Markdown("Scoil Sinsearach (Senior Cycle / Leaving Certificate) — the headline stage. 14 NCCA LC subjects, the LC certificate pipeline, the levy of formative assessment exit cards + the 5 NCCA Key Competencies fan-out.")
        # The actual implementation lives in
        # `gemini_hackathon_gradio/editorial_studio/app.py`
        # (the canonical editorial canvas). This Space re-exports
        # the relevant tab for the leaving_certificate stage.
        # Lazy-import to avoid forcing the dependency on the
        # full gemini_hackathon_gradio package at startup.
        try:
            from gemini_hackathon_gradio import build_editorial_studio_app
            editor = build_editorial_studio_app()
            gr.Markdown("## Editorial Studio preview")
            gr.Markdown(editor.__doc__ or "Editorial Studio (preview).")
        except ImportError as e:
            _log.warning("Could not load full editorial studio: %s", e)
            gr.Markdown("(Install gemini_hackathon_gradio to enable the full editorial canvas.)")

        return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)