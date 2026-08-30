"""gemini_hackathon_gradio.an_learning_graph.theme — British Isles palette integration.

Integrates with the canonical British Isles 5-stage palette from
`gemini_hackathon_gradio._common.theme` (the Aistear / Bunscoil /
MeanScoil / ScoilSinsearach / Ollscoil education stages). The
learning-graph studio overrides the headline palette so the
right-rail accents align with the 4 new learning-graph stages:

    Discovery  (Year 6)  -> Aistear-soft dawn
    Building   (Year 7)  -> Bunscoil sea-blue
    Practice   (Year 8)  -> MeanScoil meadow-green  (the canonical SHOWCASE)
    Mastery    (Year 11) -> ScoilSinsearach harvest-gold
    Pedagogy   (cross-cutting) -> Ollscoil scholarship-indigo
"""

from __future__ import annotations

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

from .._common.theme import EDUCATION_PALETTE, GRADIO_CSS


# ---------------------------------------------------------------------------
# Theme function
# ---------------------------------------------------------------------------


def apply_learning_graph_theme() -> Any:
    """Return a Gradio Theme configured with the British Isles 5-stage palette.

    Mirrors ``gemini_hackathon_gradio._common.theme.apply_education_theme``
    but tunes the primary hue to the canonical MeanScoil meadow-green
    (the colour of the Y8 Python learning-graph showcase).

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for apply_learning_graph_theme(); "
            "install with `pip install gradio>=5.28.0,<6.0`"
        )
    theme = gr.themes.Soft(
        primary_hue=gr.themes.Color(
            **{".c50": "#e6f4ea", ".c100": "#cce8d3", ".c200": "#a6d3ad",
               ".c300": "#80be87", ".c400": "#5aa961", ".c500": "#3d8e47",
               ".c600": "#2f7138", ".c700": "#21542a", ".c800": "#13381b",
               ".c900": "#081c0e", ".c950": "#040e07"},
        ),
        secondary_hue="orange",
        neutral_hue="dark",
    )
    try:
        theme = theme.set(
            body_background_fill=EDUCATION_PALETTE["hades_base"] if "hades_base" in EDUCATION_PALETTE else "#1d1d2f",
            body_text_color="#d8d4cc",
            block_background_fill="#1a1d2e",
            block_border_color="#a67c52",
            button_primary_background_fill="#28955e",  # MeanScoil meadow-green
            button_primary_text_color="#fdfaf3",
            button_secondary_background_fill="#e8915c",  # Aistear dawn-orange
            input_background_fill="#1a1d2e",
        )
    except Exception:
        pass
    return theme


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

STUDIO_THEME_CSS: str = GRADIO_CSS + """
/* Learning-graph studio extensions on top of the 5-stage palette */

/* Year-level accent strip (the right rail of the Render tab) */
.year-strip-y6  { border-left: 4px solid #e8915c; }
.year-strip-y7  { border-left: 4px solid #1e80c6; }
.year-strip-y8  { border-left: 4px solid #28955e; }
.year-strip-y11 { border-left: 4px solid #cc9966; }

/* Learning-graph cell styles (used by the Plotly SVG renderer) */
.cell-skill     { font-family: 'JetBrains Mono', monospace; font-size: 0.85em; }
.cell-prereq    { stroke: #a83a2a; stroke-width: 1.5px; fill: none; }
.cell-ribbon    { stroke-dasharray: 6 4; }

/* Tab badge (when an equivalency or pedagogy overlay is loaded) */
.tab-badge {
    display: inline-block;
    background: #5a4fcf;
    color: #fdfaf3;
    padding: 0.1em 0.5em;
    border-radius: 6px;
    font-size: 0.7em;
    margin-left: 0.4em;
}
"""

__all__ = ["STUDIO_THEME_CSS", "apply_learning_graph_theme"]
