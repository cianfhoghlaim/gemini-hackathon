"""gemini_hackathon_gradio.an_learning_graph.pedagogy_tab — Pedagogy overlay tab.

Phase 4 of the OpenSpec change
[`2026-08-31-pedagogy-overlay-renderer-v1`](../../../../openspec/changes/2026-08-31-pedagogy-overlay-renderer-v1/proposal.md).

The Pedagogy overlay tab colours every cell in a learning graph by
which NCCE pedagogy principle it uses, and lets the user filter the
graph to "show only cells using principle X".

Workflow:

  1. Pick a learning graph (jurisdiction, subject, year_level).
  2. Pick a filtering principle (e.g. "PRIMM").
  3. The tab renders:
     - The annotated graph as a Plotly heatmap where cells are coloured
       by the dominant pedagogy principle.
     - A hover-card on each cell with the principle name + summary
       + how_to_apply.
     - The filtered count: number of visible cells vs. total.

The underlying data is the ``AnnotatedLearningGraph`` produced by
`orchestration.defs.3_model_lifecycle.pedagogy_overlay.py` and mirrored
to the dev SQLite table `annotated_learning_graphs` (per Phase 3 of
the change).

Palette: reuses the British Isles 5-stage palette from the parent
``theme.py``. The 12 pedagogy principles each get a distinct colour
hash for visual differentiation.
"""

from __future__ import annotations

import json
import logging
import pathlib
import sqlite3
from typing import Any

try:
    import gradio as gr
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    gr = None  # type: ignore[assignment]
    go = None  # type: ignore[assignment]
    PLOTLY_AVAILABLE = False

from .theme import STUDIO_THEME_CSS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent.parent
SQLITE_PATH: pathlib.Path = (
    REPO_ROOT / "data" / "bi_ep" / "extracted_syllabi.sqlite"
)

#: The 6 BIEP priority subjects (the canonical 6 Dagster overlay assets).
SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)

#: Year levels the Y8 Python showcase covers (matches Change A).
YEAR_LEVELS: tuple[int, ...] = (6, 7, 8, 9, 10, 11)

#: The 12 canonical NCCE pedagogy principles (per the canonical disk
#: cache JSON written by `cocoindex_flows/uk_ncce/pedagogy_cache.py`).
#: When the cache is cold the UI shows a 0-length filter dropdown.
DEMO_PRINCIPLE_IDS: tuple[str, ...] = (
    "primm",
    "pair_programming",
    "semantic_waves",
    "lead_with_concepts",
    "live_coding",
    "worked_examples",
    "formative_assessment",
    "talking_points",
    "unplugged_first",
    "spaced_retrieval",
    "dual_coding",
    "interleaving",
)


def _load_principles_from_cache() -> list[dict[str, Any]]:
    """Load the 12 cached principles from the disk cache JSON."""
    cache_path = (
        REPO_ROOT / "data" / "bi_ep" / "syllabi_md" / "uk_ncce"
        / "pedagogy_principles.json"
    )
    if not cache_path.exists():
        return []
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "pedagogy_tab: cache parse failed path=%s: %s", cache_path, exc
        )
        return []
    return [
        {
            "id": str(p.get("id", "")),
            "name": str(p.get("name", "")),
            "summary": str(p.get("summary", "")),
            "how_to_apply": str(p.get("how_to_apply", "")),
        }
        for p in payload.get("principles", [])
        if isinstance(p, dict)
    ]


def _principle_palette(principles: list[dict[str, Any]]) -> dict[str, str]:
    """Stable hex colour per principle id (the canonical 5-stage + extra)."""
    palette: list[str] = [
        "#00733B",  # NCCA green
        "#1e80c6",  # Bunscoil sea-blue
        "#28955e",  # MeanScoil meadow-green
        "#cc9966",  # Scoil Sinsearach harvest-gold
        "#5a4fcf",  # Ollscoil scholarship-indigo
        "#a83a2a",  # Crimson
        "#e8915c",  # Aistear dawn-orange
        "#5c2c0c",  # Aistear ink
        "#7ab5d8",  # Bunscoil soft
        "#7cc09c",  # MeanScoil soft
        "#e3c2a0",  # Scoil Sinsearach soft
        "#9b93e6",  # Ollscoil soft
    ]
    out: dict[str, str] = {}
    for idx, p in enumerate(principles):
        out[p["id"]] = palette[idx % len(palette)]
    return out


def _load_annotated_graph(
    *,
    subject: str,
    year_level: int,
) -> dict[str, Any] | None:
    """Read the AnnotatedLearningGraph for one (subject, year_level) pair."""
    if not SQLITE_PATH.exists():
        logger.warning(
            "pedagogy_tab.sqlite_missing path=%s — has the pedagogy_overlay "
            "Dagster asset group run?",
            SQLITE_PATH,
        )
        return None
    with sqlite3.connect(str(SQLITE_PATH)) as conn:
        try:
            row = conn.execute(
                "SELECT payload_json FROM annotated_learning_graphs "
                "WHERE subject = ? ORDER BY generated_at DESC LIMIT 1",
                (subject,),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            logger.warning(
                "pedagogy_tab: annotated_learning_graphs table missing — "
                "has any pedagogy_overlay asset run? reason=%s",
                exc,
            )
            return None
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as exc:
        logger.warning("pedagogy_tab: parse failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Renderer — coloured SVG heatmap (Plotly)
# ---------------------------------------------------------------------------


def _render_pedagogy_overlay(
    annotated_graph: dict[str, Any] | None,
    *,
    filter_principle: str,
    principles: list[dict[str, Any]],
) -> tuple[Any, str, str]:
    """Render the annotated graph + return (Plotly, hover-card md, counts md).

    When ``filter_principle`` matches "ALL" the full graph is shown;
    otherwise only cells tagged with that principle are fully visible
    (others are greyed out).
    """
    if not PLOTLY_AVAILABLE:
        return (
            None,
            "_Plotly not installed — `pip install plotly` to enable the renderer._",
            "",
        )
    if annotated_graph is None:
        return (
            None,
            "_No annotated graph yet — run `dg launch --assets "
            "pedagogy_overlay_<subject>` to populate the "
            "`annotated_learning_graphs` SQLite table._",
            "",
        )

    graph = annotated_graph.get("graph", {})
    rows = graph.get("rows", [])
    columns = graph.get("columns", [])
    cells = graph.get("cells", [])
    cell_annotations: dict[str, list[str]] = annotated_graph.get(
        "cell_annotations", {}
    )

    palette = _principle_palette(principles)
    row_labels = [r.get("label", r.get("id", "")) for r in rows]
    col_labels = [c.get("label", c.get("id", "")) for c in columns]

    if not row_labels or not col_labels:
        return (
            None,
            f"_Empty graph: {len(row_labels)} rows × {len(col_labels)} columns._",
            "",
        )

    cell_lookup: dict[tuple[str, str], dict[str, Any]] = {
        (c.get("row_id", ""), c.get("column_id", "")): c for c in cells
    }
    cell_text: list[list[str]] = []
    cell_color: list[list[float | str]] = []
    cell_hovertext: list[list[str]] = []
    visible_count = 0
    total_cells = 0

    for ri, row in enumerate(rows):
        text_row: list[str] = []
        color_row: list[float | str] = []
        hover_row: list[str] = []
        for ci, col in enumerate(columns):
            cell = cell_lookup.get((row.get("id", ""), col.get("id", "")), {})
            cell_id = cell.get("id", "")
            annotation_ids = cell_annotations.get(cell_id, [])
            total_cells += 1
            primary_principle_id = (
                annotation_ids[0] if annotation_ids else "lead_with_concepts"
            )
            color = palette.get(primary_principle_id, "#bcb8b0")
            if (
                filter_principle != "ALL"
                and primary_principle_id != filter_principle
            ):
                # Grey out cells that don't match the filter.
                color = "#e6e6e6"
            else:
                visible_count += 1
            color_row.append(color)
            text_row.append(cell.get("skill_description", "")[:60])
            principle_names = [
                next(
                    (p["name"] for p in principles if p["id"] == pid),
                    pid,
                )
                for pid in annotation_ids
            ]
            hover_row.append(
                f"<b>{row.get('label', row.get('id', ''))} × "
                f"{col.get('label', col.get('id', ''))}</b><br>"
                f"Skills: {cell.get('skill_description', '—')}<br>"
                f"Pedagogy: {', '.join(principle_names) or '—'}<br>"
                f"<extra></extra>"
            )
        cell_text.append(text_row)
        cell_color.append(color_row)
        cell_hovertext.append(hover_row)

    fig = go.Figure(
        data=go.Heatmap(
            z=[[0] * len(col_labels) for _ in row_labels],
            x=col_labels,
            y=row_labels,
            text=cell_text,
            texttemplate="%{text}",
            hovertext=cell_hovertext,
            hoverinfo="text",
            colorscale=[[0, "#fdfaf3"], [1, "#fdfaf3"]],
            showscale=False,
        )
    )
    # Overlay coloured squares per cell using shapes — gives a richer
    # per-cell colour than a heatmap.
    for ri in range(len(row_labels)):
        for ci in range(len(col_labels)):
            fig.add_shape(
                type="rect",
                x0=ci - 0.5, x1=ci + 0.5,
                y0=ri - 0.5, y1=ri + 0.5,
                line=dict(color="#ffffff", width=2),
                fillcolor=cell_color[ri][ci],
                layer="below",
                xref="x", yref="y",
            )
    fig.update_layout(
        title=(
            f"{graph.get('jurisdiction', 'Unknown')} / "
            f"{graph.get('subject', 'Unknown')} / "
            f"Year {graph.get('year_level', '?')} (coloured by pedagogy)"
        ),
        xaxis_title="Lesson column",
        yaxis_title="Skill row",
        height=520,
        margin={"l": 160, "r": 60, "t": 60, "b": 60},
    )

    # Hover card — show the selected principle's full metadata.
    if filter_principle != "ALL":
        chosen = next(
            (p for p in principles if p["id"] == filter_principle),
            None,
        )
        if chosen:
            hover_md = (
                f"### {chosen['name']}\n\n"
                f"**Summary**: {chosen['summary']}\n\n"
                f"**How to apply**: {chosen['how_to_apply']}\n\n"
                f"_Visible cells: **{visible_count}** "
                f"of **{total_cells}** total._"
            )
        else:
            hover_md = ""
    else:
        # All cells visible — show a summary card describing the dominant
        # principle of the first 3 visible cells.
        cards: list[str] = []
        for ri in range(min(3, len(row_labels))):
            for ci in range(min(3, len(col_labels))):
                cell = cell_lookup.get(
                    (rows[ri].get("id", ""), columns[ci].get("id", ""))
                )
                if cell is None:
                    continue
                cell_id = cell.get("id", "")
                principle_ids = cell_annotations.get(cell_id, [])
                if not principle_ids:
                    continue
                first = principle_ids[0]
                principle = next(
                    (p for p in principles if p["id"] == first),
                    None,
                )
                if principle is None:
                    continue
                cards.append(
                    f"**{cell.get('skill_description', '—')[:80]}…** "
                    f"\n  _{principle['name']}_"
                )
        hover_md = "### Sample of visible cells\n\n" + "\n\n".join(cards)

    counts_md = (
        f"**Visible cells**: `{visible_count}` of `{total_cells}` total. "
        f"_Source: `{annotated_graph.get('pedagogy_source', 'live_pdf')}`._"
    )
    return fig, hover_md, counts_md


# ---------------------------------------------------------------------------
# Gradio handler
# ---------------------------------------------------------------------------


def _on_overlay(
    subject: str,
    year_level: int,
    filter_principle: str,
) -> tuple[Any, str, str]:
    """Gradio handler — render the coloured overlay, return (Plotly, hover_md, counts_md)."""
    principles = _load_principles_from_cache()
    annotated_graph = _load_annotated_graph(
        subject=subject, year_level=year_level
    )
    return _render_pedagogy_overlay(
        annotated_graph,
        filter_principle=filter_principle,
        principles=principles,
    )


def _principle_dropdown_choices(principles: list[dict[str, Any]]) -> list[str]:
    """Build the dropdown choices — ["ALL"] + [name for each principle]."""
    return ["ALL"] + [p["name"] for p in principles]


def _lookup_principle_id(display: str, principles: list[dict[str, Any]]) -> str:
    """Display name (`'PRIMM'`) -> canonical id (`'primm'`)."""
    for p in principles:
        if p["name"] == display:
            return p["id"]
    return "ALL"


# ---------------------------------------------------------------------------
# Public build function (matches the `from .pedagogy_tab import ...`
# contract in the Change A __init__.py)
# ---------------------------------------------------------------------------


def build_pedagogy_tab() -> None:
    """Build the Pedagogy overlay tab."""
    if not PLOTLY_AVAILABLE or gr is None:
        return

    principles = _load_principles_from_cache()
    if principles:
        intro_md = (
            f"### Coloured pedagogy overlay\n\n"
            f"Loaded **{len(principles)} NCCE pedagogy principles** from the "
            f"disk cache. Pick a learning graph and a principle to filter by."
        )
        dropdown_choices = _principle_dropdown_choices(principles)
        default_filter = "ALL"
    else:
        intro_md = (
            "### Coloured pedagogy overlay\n\n"
            "_No pedagogy cache found — run "
            "`python -m cocoindex_flows.uk_ncce.pedagogy_cache` to populate "
            "the disk cache, then re-open this tab._"
        )
        dropdown_choices = list(DEMO_PRINCIPLE_IDS)  # fallback for offline UX
        default_filter = "ALL"

    gr.Markdown(intro_md)
    with gr.Row():
        subject_dd = gr.Dropdown(
            label="Subject",
            choices=list(SUBJECTS),
            value="computer_science",
        )
        year_dd = gr.Dropdown(
            label="Year level",
            choices=list(YEAR_LEVELS),
            value=8,
        )
        filter_dd = gr.Dropdown(
            label="Filter by principle",
            choices=dropdown_choices,
            value=default_filter,
        )
        overlay_btn = gr.Button("Render overlay", variant="primary")

    plot_out = gr.Plot(label="Annotated learning graph (pedagogy-coloured)")
    hover_md = gr.Markdown()
    counts_md = gr.Markdown()

    def _handler(
        subject: str, year_level: int, filter_display: str
    ) -> tuple[Any, str, str]:
        principles2 = _load_principles_from_cache()
        filter_id = _lookup_principle_id(filter_display, principles2)
        annotated_graph = _load_annotated_graph(
            subject=subject, year_level=int(year_level)
        )
        return _render_pedagogy_overlay(
            annotated_graph,
            filter_principle=filter_id,
            principles=principles2,
        )

    overlay_btn.click(
        fn=_handler,
        inputs=[subject_dd, year_dd, filter_dd],
        outputs=[plot_out, hover_md, counts_md],
    )


__all__ = ["build_pedagogy_tab"]
