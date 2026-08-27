"""gemini_hackathon_gradio.an_scrudu — LC past-paper heatmap studio.

Lifted from `sruth/spaces/an_scrudu/` and rewritten for the British
Isles education theme. Modules:

  - app.py        — the Gradio app (build_app())
  - extraction.py — BAML/Pydantic/regex extraction (3-tier fallback)
  - heatmap.py    — HTML heatmap renderer (5-stage palette gradient)
  - pclm_emitter.py — PCLM-XML + minimal-PDF emitter (lifted from
                    `gemini_hackathon_gradio._common.pclm_emitter`)
"""

from __future__ import annotations

# Lazy imports (the studio app requires Gradio)
from gemini_hackathon_gradio.an_scrudu.extraction import (
    CircularReference,
    MarkingSchemeExtraction,
    MarkingSchemeSummary,
    TopicDistribution,
    extract_circular,
)
from gemini_hackathon_gradio.an_scrudu.heatmap import render_heatmap, render_pclm_html


def __getattr__(name: str):
    """Lazily import the studio app (requires Gradio)."""
    if name == "build_app":
        from gemini_hackathon_gradio.an_scrudu.app import build_app as _b
        return _b
    raise AttributeError(f"module 'gemini_hackathon_gradio.an_scrudu' has no attribute {name!r}")


__all__ = [
    "build_app",
    "TopicDistribution",
    "CircularReference",
    "MarkingSchemeSummary",
    "MarkingSchemeExtraction",
    "extract_circular",
    "render_heatmap",
    "render_pclm_html",
]
