"""
Aistear — Early Years (0-6) — the gemini_hackathon HF Space.

Headline surface for the aistear stage of the
British Isles Education Platform. The full editorial studio
runs on Cloud Run (see `gemini_hackathon_gradio/editorial_studio/deploy.py`)
— this Space is the smaller, shareable entry point.
"""

from __future__ import annotations

import logging

import gradio as gr

_log = logging.getLogger(__name__)


def build_app():
    """Build the aistear Gradio app."""
    with gr.Blocks(
        title="Aistear — Early Years (0-6)",
        theme=gr.themes.Soft(primary_hue="orange", secondary_hue="amber"),
    ) as demo:
        gr.Markdown("# Aistear — Early Years (0-6)")
        gr.Markdown("Aistear framework for ages 0-6 — play-based learning, 4 themes (wellbeing / identity / communicating / exploring).")
        # The actual implementation lives in
        # `gemini_hackathon_gradio/editorial_studio/app.py`
        # (the canonical editorial canvas). This Space re-exports
        # the relevant tab for the aistear stage.
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