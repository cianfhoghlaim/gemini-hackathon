"""
Bunscoil — Primary (4-12) — the gemini_hackathon HF Space.

Headline surface for the bunscoil stage of the
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
    """Build the bunscoil Gradio app."""
    return gr.Blocks(
        title="Bunscoil — Primary (4-12)",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="indigo"),
    ) as demo:
        gr.Markdown("# Bunscoil — Primary (4-12)")
        gr.Markdown("Bunscoil (Primary) curriculum — 12 NCCA areas, friendly typography, the canonical heatmap studio.")
        # The actual implementation lives in
        # `gemini_hackathon_gradio/editorial_studio/app.py`
        # (the canonical editorial canvas). This Space re-exports
        # the relevant tab for the bunscoil stage.
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