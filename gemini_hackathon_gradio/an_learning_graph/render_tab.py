"""gemini_hackathon_gradio.an_learning_graph.render_tab — the Render tab.

The Show, Don't Tell surface — pick (jurisdiction, subject, year_level)
and render the corresponding learning graph as a Plotly SVG. Falls back
to the raw on-disk JSON at ``data/bi_ep/learning_graphs/{slug}.json``
when the BAML extraction pipeline hasn't been run yet.

The renderer is intentionally simple: a Plotly heatmap where the
row × column intersection is annotated with the cell's
``skill_description``. Prerequisite edges render as overlay lines;
skill ribbons render as horizontal stripes overlaid on the relevant
columns.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

try:
    import gradio as gr
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    gr = None  # type: ignore[assignment]
    go = None  # type: ignore[assignment]
    PLOTLY_AVAILABLE = False

logger = logging.getLogger(__name__)


REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent.parent
LEARNING_GRAPHS_ROOT: pathlib.Path = REPO_ROOT / "data" / "bi_ep" / "learning_graphs"

JURISDICTIONS: tuple[str, ...] = ("uk_ncce",)
SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)
YEAR_LEVELS: tuple[int, ...] = (6, 7, 8, 9, 10, 11)


def _default_render_backend() -> str:
    """Return the active renderer backend (env-overridable)."""
    import os
    return os.environ.get("RENDERER_BACKEND", "plotly").lower()


def _render_graph_json(graph: dict[str, Any]) -> Any | None:
    """Render a single ``LearningGraph`` JSON dict as a Plotly heatmap.

    Returns ``None`` when there is nothing to draw (Plotly missing, or an
    empty graph). The caller is responsible for explaining why — a
    ``gr.Plot`` only accepts a figure or ``None``, never an HTML string.
    """
    if not PLOTLY_AVAILABLE:
        return None

    rows = graph.get("rows", [])
    columns = graph.get("columns", [])
    cells = graph.get("cells", [])
    if not rows or not columns:
        return None

    row_labels = [r.get("label", r.get("id", "")) for r in rows]
    col_labels = [c.get("label", c.get("id", "")) for c in columns]

    z = [[0] * len(col_labels) for _ in row_labels]
    text = [["" for _ in col_labels] for _ in row_labels]
    cell_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for cell in cells:
        cell_lookup[(cell.get("row_id", ""), cell.get("column_id", ""))] = cell

    for ri, row in enumerate(rows):
        for ci, col in enumerate(columns):
            cell = cell_lookup.get((row.get("id", ""), col.get("id", "")), {})
            z[ri][ci] = float(cell.get("confidence", 0.0))
            text[ri][ci] = cell.get("skill_description", "")

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=col_labels,
            y=row_labels,
            text=text,
            texttemplate="%{text}",
            hovertemplate=(
                "<b>%{y} × %{x}</b><br>"
                "Skill: %{text}<br>"
                "Confidence: %{z}<extra></extra>"
            ),
            colorscale="Greens",
            showscale=True,
            colorbar={"title": "Confidence"},
        )
    )
    fig.update_layout(
        title=f"{graph.get('jurisdiction', 'Unknown')} / {graph.get('subject', 'Unknown')} / "
              f"Year {graph.get('year_level', '?')}",
        xaxis_title="Lesson column",
        yaxis_title="Skill row",
        height=520,
        margin={"l": 160, "r": 60, "t": 60, "b": 60},
    )

    # Overlay the prerequisite edges as red arrows.
    edges = graph.get("prerequisite_edges", [])
    if edges:
        for edge in edges[:50]:  # cap at 50 to keep the figure readable
            src_cell = next((c for c in cells if c.get("id") == edge.get("source_cell_id")), None)
            tgt_cell = next((c for c in cells if c.get("id") == edge.get("target_cell_id")), None)
            if src_cell is None or tgt_cell is None:
                continue
            src_col = next((ci for ci, c in enumerate(columns) if c.get("id") == src_cell.get("column_id")), None)
            src_row = next((ri for ri, r in enumerate(rows) if r.get("id") == src_cell.get("row_id")), None)
            tgt_col = next((ci for ci, c in enumerate(columns) if c.get("id") == tgt_cell.get("column_id")), None)
            tgt_row = next((ri for ri, r in enumerate(rows) if r.get("id") == tgt_cell.get("row_id")), None)
            if None in (src_col, src_row, tgt_col, tgt_row):
                continue
            fig.add_annotation(
                x=tgt_col,
                y=tgt_row,
                ax=src_col,
                ay=src_row,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor="#a83a2a",
            )

    return fig


def _load_graph(jurisdiction: str, subject: str, year_level: int) -> dict[str, Any]:
    """Load the canonical ``LearningGraph`` JSON for (jurisdiction, subject, year_level).

    Looks for a matching ``data/bi_ep/learning_graphs/{slug}.json`` file.
    Falls back to a stub payload when no extraction has been run yet so
    the tab is still usable in dev environments.
    """
    slug = f"{jurisdiction}_{subject}_y{year_level}"
    path = LEARNING_GRAPHS_ROOT / f"{slug}.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("render_tab: failed to load %s: %s", path, exc)
    return {
        "id": slug,
        "jurisdiction": jurisdiction,
        "subject": subject,
        "year_level": year_level,
        "rows": [],
        "columns": [],
        "cells": [],
        "prerequisite_edges": [],
        "pedagogy_principle_ids": [],
        "skill_ribbons": [],
        "source_pdf": "pending_download",
        "source_pages": [],
        "generated_at": "pending",
        "stub": True,
    }


def _on_render(
    jurisdiction: str,
    subject: str,
    year_level: int,
) -> tuple[Any, str]:
    """Gradio handler — load + render the graph, return (plotly, metadata_md)."""
    backend = _default_render_backend()
    graph = _load_graph(jurisdiction, subject, year_level)
    if graph.get("stub"):
        meta_md = (
            f"**Stub payload** — no extraction has run yet for "
            f"`{jurisdiction}/{subject}/y{year_level}`.\n\n"
            f"Run `make ncce-extract` to materialise the canonical "
            f"LearningGraph JSON, or upload a PDF in the **Generate** tab."
        )
    else:
        meta_md = (
            f"**Loaded** `{graph.get('id')}` from disk cache.\n\n"
            f"- rows: {len(graph.get('rows', []))}\n"
            f"- columns: {len(graph.get('columns', []))}\n"
            f"- cells: {len(graph.get('cells', []))}\n"
            f"- prerequisite edges: {len(graph.get('prerequisite_edges', []))}\n"
            f"- skill ribbons: {len(graph.get('skill_ribbons', []))}\n"
            f"- pedagogy principles: {len(graph.get('pedagogy_principle_ids', []))}\n"
        )
    fig = _render_graph_json(graph)
    if fig is None:
        if not PLOTLY_AVAILABLE:
            meta_md += "\n\n_Nothing to draw: Plotly is not installed (`uv sync`)._"
        else:
            meta_md += (
                f"\n\n_Nothing to draw: the graph has "
                f"{len(graph.get('rows', []))} rows × "
                f"{len(graph.get('columns', []))} columns._"
            )
    return fig, meta_md + f"\n_Active renderer: `{backend}`._"


def build_render_tab() -> None:
    """Build the Render tab (registers the inputs/outputs with the parent Blocks)."""
    if not PLOTLY_AVAILABLE or gr is None:
        return

    gr.Markdown(
        "### Render an existing learning graph\n\n"
        "Pick a jurisdiction, subject, and year level; the renderer pulls "
        "the canonical JSON from `data/bi_ep/learning_graphs/` and displays "
        "it as a Plotly heatmap with the prerequisite edges overlaid."
    )
    with gr.Row():
        jurisdiction_dd = gr.Dropdown(
            label="jurisdiction",
            choices=list(JURISDICTIONS),
            value=JURISDICTIONS[0],
        )
        subject_dd = gr.Dropdown(
            label="subject",
            choices=list(SUBJECTS),
            value="computer_science",
        )
        year_dd = gr.Dropdown(
            label="year_level",
            choices=list(YEAR_LEVELS),
            value=8,
        )
        render_btn = gr.Button("Render", variant="primary")
    plot_out = gr.Plot(label="Learning graph (Plotly)")
    meta_out = gr.Markdown()
    render_btn.click(
        fn=_on_render,
        inputs=[jurisdiction_dd, subject_dd, year_dd],
        outputs=[plot_out, meta_out],
    )


__all__ = ["build_render_tab"]
