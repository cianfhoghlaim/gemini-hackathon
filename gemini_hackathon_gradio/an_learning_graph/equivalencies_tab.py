"""gemini_hackathon_gradio.an_learning_graph.equivalencies_tab — Equivalencies tab.

Phase 3 of the OpenSpec change
[`2026-08-31-learning-graph-equivalency-graph-v1`](../../../../openspec/changes/2026-08-31-learning-graph-equivalency-graph-v1/proposal.md).

The Equivalencies tab is the "see one cell, see its 7 equivalents"
surface. The user picks:

  1. **Source** — (jurisdiction, subject, year_level, row_id, column_id)
  2. **Targets** — a multi-select of the 7 other BI jurisdictions

…and the tab displays:

  - The 7 equivalent cells in the chosen target jurisdictions (read
    from the Firestore `prerequisiteEdges/{edge_id}` collection or the
    dev SQLite mirror at `learning_graph_crossrefs`).
  - A **Sankey-style** cross-walk diagram with confidence scores as
    link widths (Plotly `go.Sankey`).
  - A natural-language summary table that pairs each equivalent cell
    with its NCEA / AQA / WJEC / CCEA / SQA / IoM / JC-G mapping.

This is the headline BIEP cross-jurisdiction view — it turns the 36
isolated per-jurisdiction learning graphs into 1 cross-walked graph
that's navigable in the studio.

Palette: reuses the British Isles 5-stage palette from the parent
``theme.py`` and the per-subnation awarding-body palettes loaded from
``themes/*.json``.

Run standalone (when wired into ``__init__.build_app()``)::

    python -m gemini_hackathon_gradio.an_learning_graph
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
# Constants — canonical 7 target jurisdictions + 6 priority subjects
# ---------------------------------------------------------------------------

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent.parent
SQLITE_PATH: pathlib.Path = (
    REPO_ROOT / "data" / "bi_ep" / "extracted_syllabi.sqlite"
)

#: The 7 target jurisdictions for Change B (source is always UK_NCCE).
TARGET_JURISDICTIONS: tuple[str, ...] = (
    "ENGLAND",
    "WALES",
    "NORTHERN_IRELAND",
    "SCOTLAND",
    "ISLE_OF_MAN",
    "JERSEY",
    "GUERNSEY",
)

#: Display labels — maps BAML Jurisdiction enum -> human-readable name.
JURISDICTION_DISPLAY: dict[str, str] = {
    "ENGLAND": "England (AQA / OCR / Pearson)",
    "WALES": "Wales (WJEC / CBAC)",
    "NORTHERN_IRELAND": "Northern Ireland (CCEA)",
    "SCOTLAND": "Scotland (SQA — National 5 + Higher)",
    "ISLE_OF_MAN": "Isle of Man (IoM Meanscoil)",
    "JERSEY": "Jersey (Curriculum Authority)",
    "GUERNSEY": "Guernsey (ESC)",
}

#: The 6 priority subjects that have cross-walk assets (one per pair).
SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)

#: Default row × column for the demo (the Y8 Python "variables" cell).
DEFAULT_ROW_ID: str = "row_variables"
DEFAULT_COLUMN_ID: str = "col_lesson_3"


# ---------------------------------------------------------------------------
# SQLite + crossref loader
# ---------------------------------------------------------------------------


def _read_crossrefs_from_sqlite(
    path: pathlib.Path,
    *,
    subject: str,
    source_jurisdiction: str,
    target_jurisdiction: str | None = None,
) -> list[dict[str, Any]]:
    """Read the per-subject crossrefs from the dev SQLite mirror.

    The Firestore `prerequisiteEdges/{edge_id}` collection is the
    canonical production source; SQLite is the dev fallback (same
    schema, no GCP credentials required).
    """
    if not path.exists():
        logger.warning(
            "equivalencies_tab.sqlite_missing path=%s — has the "
            "uk_ncce_learning_graph_equivalencies Dagster asset group run?",
            path,
        )
        return []
    with sqlite3.connect(str(path)) as conn:
        try:
            if target_jurisdiction is None:
                rows = conn.execute(
                    "SELECT target_jurisdiction, cell_edges_json, overall_confidence, "
                    "subject FROM learning_graph_crossrefs WHERE subject = ? "
                    "ORDER BY overall_confidence DESC",
                    (subject,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT target_jurisdiction, cell_edges_json, overall_confidence, "
                    "subject FROM learning_graph_crossrefs "
                    "WHERE subject = ? AND target_jurisdiction = ?",
                    (subject, target_jurisdiction),
                ).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning(
                "equivalencies_tab: learning_graph_crossrefs table missing — "
                "has any uk_ncce_learning_graph_equivalencies asset run? "
                "reason=%s",
                exc,
            )
            return []
    out: list[dict[str, Any]] = []
    for tgt, cell_edges_json, overall_confidence, sub in rows:
        try:
            cell_edges = json.loads(cell_edges_json)
        except (TypeError, json.JSONDecodeError):
            cell_edges = []
        out.append(
            {
                "target_jurisdiction": tgt,
                "subject": sub,
                "cell_edges": cell_edges,
                "overall_confidence": float(overall_confidence),
            }
        )
    return out


def _pick_one_cell_per_target(
    crossrefs: list[dict[str, Any]],
    *,
    source_row_id: str,
    source_column_id: str,
) -> dict[str, dict[str, Any]]:
    """Pick the single best edge from each target jurisdiction.

    Returns ``{ target_jurisdiction_str -> best_cell_dict }``.
    """
    out: dict[str, dict[str, Any]] = {}
    for c in crossrefs:
        target = c["target_jurisdiction"]
        cell_edges = c.get("cell_edges") or []
        if not cell_edges:
            continue
        best = max(cell_edges, key=lambda e: float(e.get("confidence", 0.0)))
        out[target] = best
    return out


# ---------------------------------------------------------------------------
# Sankey cross-walk diagram
# ---------------------------------------------------------------------------


def _render_sankey(
    source_label: str,
    equivalents: dict[str, dict[str, Any]],
) -> Any:
    """Build a Plotly Sankey diagram of the source-cell → 7 equivalents flow.

    The link width is proportional to the BAML confidence; the source
    cell anchors the left node, the 7 equivalent cells anchor the right
    nodes.

    Returns ``None`` when Plotly is unavailable (the Gradio tab degrades
    gracefully — the markdown table is the source of truth).
    """
    if not PLOTLY_AVAILABLE:
        return None
    if not equivalents:
        return None

    # Sankey expects 4 parallel lists: source, target, value, label.
    labels: list[str] = [source_label]
    sources: list[int] = []
    targets: list[int] = []
    values: list[float] = []
    link_labels: list[str] = []

    for jurisdiction in TARGET_JURISDICTIONS:
        eq = equivalents.get(jurisdiction)
        if eq is None:
            continue
        target_label = (
            f"{JURISDICTION_DISPLAY.get(jurisdiction, jurisdiction)}\n"
            f"({eq.get('cell_id', '?')})"
        )
        labels.append(target_label)
        sources.append(0)  # index of source_label in `labels`
        targets.append(len(labels) - 1)
        conf = float(eq.get("confidence", 0.0))
        # Sankey link width should be in [0, ∞); use max(conf, 0.05) so
        # low-confidence edges are still visible.
        values.append(max(conf, 0.05))
        link_labels.append(f"{conf:.2f}")

    link = dict(
        source=sources, target=targets, value=values, label=link_labels
    )
    node = dict(
        label=labels,
        pad=18,
        thickness=18,
        color="#28955e",  # MeanScoil meadow-green from theme.py
    )
    fig = go.Figure(data=[go.Sankey(link=link, node=node)])
    fig.update_layout(
        title=(
            f"Cross-walk from `<b>{source_label}</b>` to its equivalents in the "
            f"other 7 BI jurisdictions"
        ),
        font=dict(size=11),
        height=520,
        margin={"l": 30, "r": 30, "t": 60, "b": 30},
    )
    return fig


def _build_equivalents_table_md(
    equivalents: dict[str, dict[str, Any]],
) -> str:
    """Markdown table of (target jurisdiction → cell_id, confidence, notes)."""
    lines: list[str] = [
        "| Target jurisdiction | Cell id | Confidence | Notes |",
        "|----------------------|---------|------------|-------|",
    ]
    for jurisdiction in TARGET_JURISDICTIONS:
        eq = equivalents.get(jurisdiction)
        if eq is None:
            lines.append(
                f"| {JURISDICTION_DISPLAY.get(jurisdiction, jurisdiction)} | _no data_ | — | — |"
            )
            continue
        cell_id = eq.get("cell_id", "—") or "—"
        conf = float(eq.get("confidence", 0.0))
        marker = "  ⚠️" if conf < 0.50 else ""
        notes = (eq.get("notes", "") or "").replace("\n", " ")
        lines.append(
            f"| {JURISDICTION_DISPLAY.get(jurisdiction, jurisdiction)} "
            f"| `{cell_id}` | {conf:.2f}{marker} | {notes} |"
        )
    return "\n".join(lines)


def _build_synthesis_md(
    *,
    subject: str,
    source_row_id: str,
    source_column_id: str,
    equivalents: dict[str, dict[str, Any]],
) -> str:
    """One-paragraph narrative summary of the cross-walk."""
    n_found = sum(
        1
        for tgt in TARGET_JURISDICTIONS
        if equivalents.get(tgt) is not None
    )
    if n_found == 0:
        return (
            f"**No cross-walk data** for "
            f"`{subject} / {source_row_id} / {source_column_id}` yet. "
            f"Run the `uk_ncce_<subject>_<jurisdiction>_equivalencies` "
            f"Dagster assets to materialise the Firestore "
            f"`prerequisiteEdges` collection + the dev SQLite mirror."
        )
    return (
        f"### Synthesis\n\n"
        f"- Subject: **{subject}**\n"
        f"- Source cell: **{source_row_id} × {source_column_id}** "
        f"(NCCE Y8 Python learning graph)\n"
        f"- Equivalents found in **{n_found} of {len(TARGET_JURISDICTIONS)}** "
        f"target jurisdictions\n\n"
        f"_Hover over a Sankey link to see the per-edge confidence. "
        f"Cells with confidence < 0.50 are flagged in the table above._"
    )


# ---------------------------------------------------------------------------
# Gradio handler
# ---------------------------------------------------------------------------


def _on_walk(
    subject: str,
    source_row_id: str,
    source_column_id: str,
    targets: list[str] | None,
) -> tuple[Any, str, str]:
    """Gradio handler — load crossrefs, return (Sankey, table_md, synthesis_md)."""
    targets = targets or list(TARGET_JURISDICTIONS)
    source_label = f"NCCE / {subject} / {source_row_id}×{source_column_id}"

    crossrefs: dict[str, dict[str, Any]] = {}
    if not SQLITE_PATH.exists():
        return (
            None,
            (
                "_No SQLite mirror yet — run `mise run dagster:launch --assets "
                "uk_ncce_learning_graph_equivalencies` to populate the "
                "`prerequisiteEdges` collection._"
            ),
            "",
        )

    for target in targets:
        rows = _read_crossrefs_from_sqlite(
            SQLITE_PATH,
            subject=subject,
            source_jurisdiction="UNITED_KINGDOM_NCCE",
            target_jurisdiction=target,
        )
        if not rows:
            continue
        chosen = _pick_one_cell_per_target(
            rows,
            source_row_id=source_row_id,
            source_column_id=source_column_id,
        )
        if target in chosen:
            crossrefs[target] = chosen[target]

    fig = _render_sankey(source_label, crossrefs)
    table_md = _build_equivalents_table_md(crossrefs)
    synthesis = _build_synthesis_md(
        subject=subject,
        source_row_id=source_row_id,
        source_column_id=source_column_id,
        equivalents=crossrefs,
    )
    return fig, table_md, synthesis


# ---------------------------------------------------------------------------
# Public build function (matches the `from .equivalencies_tab import ...`
# contract in the Change A __init__.py)
# ---------------------------------------------------------------------------


def build_equivalencies_tab() -> None:
    """Build the Equivalencies tab (registers inputs/outputs with the parent Blocks)."""
    if not PLOTLY_AVAILABLE or gr is None:
        return

    gr.Markdown(
        "### Cell-level cross-jurisdiction equivalencies (Phase 4b)\n\n"
        "Pick a source cell in the NCCE Y8 Python learning graph; the tab "
        "shows the 7 equivalents in the other British Isles jurisdictions "
        "(NCCA LC CS / AQA GCSE CS / Edexcel GCSE CS / WJEC GCSE CS / "
        "CCEA GCSE CS / SQA National 5 CS / IoM Meanscoil CS / Jersey "
        "/ Guernsey) as a Sankey diagram + a synthesis table.\n\n"
        "_Sankey link widths are proportional to the BAML "
        "`ExtractCellEquivalencies` confidence._"
    )
    with gr.Row():
        subject_dd = gr.Dropdown(
            label="Subject",
            choices=list(SUBJECTS),
            value="computer_science",
        )
        row_id = gr.Textbox(
            label="Source row_id",
            value=DEFAULT_ROW_ID,
            placeholder="e.g. row_variables",
        )
        col_id = gr.Textbox(
            label="Source column_id",
            value=DEFAULT_COLUMN_ID,
            placeholder="e.g. col_lesson_3",
        )
    with gr.Row():
        targets_cb = gr.CheckboxGroup(
            label="Target jurisdictions",
            choices=list(TARGET_JURISDICTIONS),
            value=list(TARGET_JURISDICTIONS),
        )
        walk_btn = gr.Button("Walk cross-walk", variant="primary")
    sankey_out = gr.Plot(label="Cross-walk (Plotly Sankey)")
    table_md = gr.Markdown()
    synthesis_md = gr.Markdown()
    walk_btn.click(
        fn=_on_walk,
        inputs=[subject_dd, row_id, col_id, targets_cb],
        outputs=[sankey_out, table_md, synthesis_md],
    )


__all__ = ["build_equivalencies_tab"]
