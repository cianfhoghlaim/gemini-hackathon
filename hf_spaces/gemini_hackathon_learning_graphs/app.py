"""gemini_hackathon_learning_graphs — the HF Space entry point.

The HF Space for the 4-tab learning-graph studio. Lazy-imports the
canonical `gemini_hackathon_gradio.an_learning_graph` package so the
Space doesn't force the full `gemini_hackathon_gradio` dependency on
the cold-start path. When the canonical package is missing, falls
back to a 4-tab `gr.Markdown` placeholder so the demo at least
renders.
"""

from __future__ import annotations

import logging

import gradio as gr

_log = logging.getLogger(__name__)


def _build_app() -> gr.Blocks:
    """Build the canonical learning-graph studio (lazy import)."""
    try:
        from gemini_hackathon_gradio.an_learning_graph import build_app

        demo = build_app()
        if demo is not None:
            return demo
        _log.warning(
            "gemini_hackathon_gradio.an_learning_graph.build_app returned None; "
            "falling back to the placeholder."
        )
    except ImportError as exc:
        _log.warning(
            "gemini_hackathon_gradio not available (%s); falling back to placeholder.",
            exc,
        )

    # Fallback placeholder — mirrors the canonical 4-tab layout.
    return gr.Blocks(
        title="An Léaráid Foghlama — The Learning Graph Studio",
        theme=gr.themes.Soft(primary_hue="green", secondary_hue="yellow"),
    ) as demo:
        gr.Markdown(
            "# An Léaráid Foghlama — The Learning Graph Studio\n\n"
            "Install `gemini_hackathon_gradio` to enable the full 4-tab studio. "
            "See https://github.com/cianfhoghlaim/gemini-hackathon for the source."
        )
        with gr.Tab("Render"):
            gr.Markdown(
                "**Tab 1 — Render.** Pick a jurisdiction, subject, and year level; "
                "view the canonical LearningGraph as a Plotly SVG heatmap with "
                "prerequisite edges overlaid. _(Full studio requires the local "
                "`gemini_hackathon_gradio` package.)_"
            )
        with gr.Tab("Equivalencies"):
            gr.Markdown(
                "**Tab 2 — Equivalencies (stub).** Shipped by Change B "
                "(`2026-08-31-learning-graph-equivalency-graph-v1`)."
            )
        with gr.Tab("Generate from PDF"):
            gr.Markdown(
                "**Tab 3 — Generate from PDF.** Upload a syllabus PDF and run "
                "the per-subject BAML extractor."
            )
        with gr.Tab("Pedagogy overlay"):
            gr.Markdown(
                "**Tab 4 — Pedagogy overlay (stub).** Shipped by Change C "
                "(`2026-08-31-pedagogy-overlay-renderer-v1`)."
            )


if __name__ == "__main__":
    demo = _build_app()
    demo.launch(server_name="0.0.0.0", server_port=7860)
