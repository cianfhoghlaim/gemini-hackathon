"""gemini_hackathon_gradio.an_learning_graph — the 4-tab learning-graph studio.

Phase 5 of the OpenSpec change
[`2026-08-31-uk-ncce-learning-graph-showcase-v1`](../../../../openspec/changes/2026-08-31-uk-ncce-learning-graph-showcase-v1/proposal.md).

The headline studio for the BIEP v3 learning-graph substrate. Hosts the
canonical 4-tab interface per the proposal:

    Tab 1 — Render : pick (jurisdiction, subject, year_level) -> render
                       the learning graph as Plotly SVG.
    Tab 2 — Equivalencies : cell-level cross-jurisdiction equivalencies
                              (STUB — shipped by Change B).
    Tab 3 — Generate from PDF : upload a syllabus PDF -> run the BAML
                                  extractor -> preview the generated grid.
    Tab 4 — Pedagogy overlay : dynamic overlay of the 12 NCCE pedagogy
                                  principles onto the graph cells
                                  (STUB — shipped by Change C).

Ships as a Gradio studio + a HF Space mirror (see
`hf_spaces/gemini_hackathon_learning_graphs/`).

Theme: the British Isles 5-stage palette (see `theme.py`).

Run standalone:
    python -m gemini_hackathon_gradio.an_learning_graph
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    gr = None  # type: ignore[assignment]
    GRADIO_AVAILABLE = False

from .render_tab import build_render_tab
from .equivalencies_tab import build_equivalencies_tab
from .generate_tab import build_generate_tab
from .pedagogy_tab import build_pedagogy_tab
from .theme import STUDIO_THEME_CSS, apply_learning_graph_theme

logger = logging.getLogger(__name__)


__all__ = [
    "STUDIO_THEME_CSS",
    "apply_learning_graph_theme",
    "build_app",
    "main",
]


def build_app() -> Any:
    """Build the canonical ``an_learning_graph`` Gradio app."""
    if not GRADIO_AVAILABLE:
        logger.warning(
            "an_learning_graph: gradio not installed; build_app() returns None."
        )
        return None

    theme = apply_learning_graph_theme()
    with gr.Blocks(
        title="An Léaráid Foghlama — The Learning Graph Studio",
        theme=theme,
        css=STUDIO_THEME_CSS,
    ) as demo:
        gr.Markdown(
            "# An Léaráid Foghlama — The Learning Graph Studio\n\n"
            "The 4-tab interface for the BIEP v3 learning-graph substrate:\n\n"
            "  1. **Render** — pick (jurisdiction, subject, year_level) and view the graph\n"
            "  2. **Equivalencies** — cell-level cross-jurisdiction equivalencies (*shipped by Change B*)\n"
            "  3. **Generate** — upload a syllabus PDF → run the BAML extractor → preview the grid\n"
            "  4. **Pedagogy overlay** — overlay the 12 NCCE pedagogy principles (*shipped by Change C*)\n"
        )

        with gr.Tab("Render"):
            build_render_tab()

        with gr.Tab("Equivalencies"):
            build_equivalencies_tab()

        with gr.Tab("Generate from PDF"):
            build_generate_tab()

        with gr.Tab("Pedagogy overlay"):
            build_pedagogy_tab()

    return demo


def main() -> int:
    """CLI entry: ``python -m gemini_hackathon_gradio.an_learning_graph``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    app = build_app()
    if app is None:
        return 1
    app.launch(server_name="0.0.0.0", server_port=7860)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
