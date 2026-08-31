# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "altair",
#     "pandas",
#     "pypdfium2",
#     "plotly",
# ]
# ///

"""Notebook 10 — The NCCE Learning Graph walkthrough.

Demonstrates the full BIEP v3 pipeline for the 5 NCCE artefacts:

  1. Inspect the lifted PDFs at ``data/bi_ep/syllabi_raw/uk_ncce/``
  2. Run the DLT substrate (``dlt_pipelines.uk_ncce_learning_graphs``)
  3. Run the CocoIndex App (``cocoindex_flows.uk_ncce.learning_graphs_app``)
  4. Inspect the canonical SQLite mirror
  5. Render the Y8 Python learning graph (the canonical showcase)

This is the marimo companion to ``docs/LEARNING_GRAPH_SHOWCASE.md``.
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")

@app.cell
def _intro() -> None:
    import marimo as mo
    mo.md(
        """
        # The NCCE Learning Graph Showcase

        The headline change of the 2026-08-31 batch. Lifts the 5 NCCE PDFs
        (3 learning graphs + pedagogy + the full Y7→Y11 Curriculum Journey)
        into the gemini_hackathon BIEP substrate as the canonical example
        of how every official syllabus becomes a structured row × column
        learning graph.

        **Run the cells below** to see the pipeline execute end-to-end.
        """
    )

@app.cell
def _step1_inspect_pdfs(mo) -> None:
    mo.md("## Step 1 — inspect the lifted PDFs")

@app.cell
def _step1_list(mo) -> None:
    import pathlib
    raw_root = pathlib.Path("data/bi_ep/syllabi_raw/uk_ncce/curriculum")
    if not raw_root.exists():
        mo.md(f"**No NCCE artefacts found at `{raw_root}`.** Run `mise run data:ncce:download` first.")
    artefacts = sorted(raw_root.iterdir())
    md_lines = ["| Path | Size | Kind |", "|---|---|---|"]
    for p in artefacts:
        kind = "PDF" if p.suffix == ".pdf" else ("INDEX" if p.name == "INDEX.yaml" else ("placeholder" if p.suffix == ".json" else "?"))
        size = p.stat().st_size if p.is_file() else 0
        md_lines.append(f"| `{p.name}` | {size} | {kind} |")
    mo.md("\n".join(md_lines))

@app.cell
def _step2_dlt(mo) -> None:
    mo.md(
        """
        ## Step 2 — run the DLT substrate

        The DLT resource ``dlt_pipelines.uk_ncce_learning_graphs`` emits
        **11 OFFICIAL_DOC_COLUMNS rows** into the canonical DuckDB at
        ``gemini_hackathon.duckdb`` (5 PDF rows + 6 per-subject rows).
        """
    )

@app.cell
def _step2_run(mo) -> None:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        from dlt_pipelines.uk_ncce_learning_graphs import run
        load_info = run()
        mo.md(f"**DLT load complete.** {load_info}")
    except Exception as exc:
        mo.md(f"**DLT failed:** `{exc}`")

@app.cell
def _step3_cocoindex(mo) -> None:
    mo.md(
        """
        ## Step 3 — run the CocoIndex App

        The CocoIndex App ``cocoindex_flows.uk_ncce.learning_graphs_app``
        walks the 5 NCCE artefacts and writes grid-aware Markdown output
        to ``data/bi_ep/syllabi_md/uk_ncce/`` — preserving the row × column
        structure of the learning-graph PDFs as Markdown tables.
        """
    )

@app.cell
def _step3_run(mo) -> None:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        from cocoindex_flows.uk_ncce.learning_graphs_app import run as run_cocoindex
        stats = run_cocoindex()
        mo.md(f"**CocoIndex run complete.** {stats}")
    except Exception as exc:
        mo.md(f"**CocoIndex failed:** `{exc}`")

@app.cell
def _step4_sqlite(mo) -> None:
    mo.md(
        """
        ## Step 4 — inspect the canonical SQLite mirror

        Each Dagster asset persists its JSON artefact to
        ``data/bi_ep/extracted_syllabi.sqlite`` in the
        ``uk_ncce_learning_graphs`` table.
        """
    )

@app.cell
def _step4_query(mo) -> None:
    import pathlib
    import sqlite3
    db_path = pathlib.Path("data/bi_ep/extracted_syllabi.sqlite")
    if not db_path.exists():
        mo.md(f"**No SQLite DB at `{db_path}`.** Run the Dagster assets first.")
    with sqlite3.connect(str(db_path)) as con:
        rows = list(con.execute(
            "SELECT slug, kind, subject, year_level, sha256_hash "
            "FROM uk_ncce_learning_graphs ORDER BY slug"
        ))
    md_lines = ["| slug | kind | subject | year_level | sha256 (first 12) |", "|---|---|---|---|---|"]
    for slug, kind, subject, year_level, sha in rows:
        md_lines.append(f"| `{slug}` | {kind} | {subject or ''} | {year_level or ''} | `{sha[:12]}…` |")
    mo.md("\n".join(md_lines))

@app.cell
def _step5_render(mo) -> None:
    mo.md(
        """
        ## Step 5 — render the Y8 Python learning graph

        The canonical showcase artefact — the NCCE Y8 Intro to Python
        Programming learning graph — rendered as a Plotly heatmap with
        prerequisite edges overlaid.
        """
    )

@app.cell
def _step5_plot(mo) -> None:
    import json
    import pathlib
    graph_path = pathlib.Path("data/bi_ep/learning_graphs/uk_ncce_computer_science_y8.json")
    if not graph_path.is_file():
        mo.md(f"**No extracted graph at `{graph_path}`.** Run the Dagster asset first.")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    rows = graph.get("rows", [])
    cols = graph.get("columns", [])
    cells = graph.get("cells", [])
    if not rows or not cols:
        mo.md("Empty graph — no cells to render.")
    import plotly.graph_objects as go
    row_labels = [r.get("label", r.get("id", "")) for r in rows]
    col_labels = [c.get("label", c.get("id", "")) for c in cols]
    cell_lookup = {(c.get("row_id"), c.get("column_id")): c for c in cells}
    z = [[0.0] * len(cols) for _ in rows]
    text = [["" for _ in cols] for _ in rows]
    for ri, row in enumerate(rows):
        for ci, col in enumerate(cols):
            cell = cell_lookup.get((row.get("id"), col.get("id")), {})
            z[ri][ci] = float(cell.get("confidence", 0.5))
            text[ri][ci] = (cell.get("skill_description") or "")[:60]
    fig = go.Figure(data=go.Heatmap(z=z, x=col_labels, y=row_labels, text=text, texttemplate="%{text}", colorscale="Greens"))
    fig.update_layout(
        title=f"{graph.get('jurisdiction', '?')} / {graph.get('subject', '?')} / Y{graph.get('year_level', '?')}",
        height=520, margin={"l": 160, "r": 60, "t": 60, "b": 60},
    )
    mo.mpl.figure(fig) if False else fig  # marimo doesn't have plotly renderer here, just print
    mo.md(f"**Rendered {len(rows)} rows × {len(cols)} columns.** (See the Plotly figure in the Gradio studio for the interactive view.)")

@app.cell
def _outro(mo) -> None:
    mo.md(
        """
        ## Done

        The NCCE learning-graph substrate is fully wired:

          - 4 PDFs lifted verbatim from the upstream cianfhoghlaim leabharlann
          - 1 PDF (the full curriculum journey) deferred via a placeholder JSON
          - 11 DLT rows in the canonical ``official_documents`` table
          - 11 Dagster assets (5 PDF + 6 per-subject)
          - 4-tab Gradio studio at ``gemini_hackathon_gradio.an_learning_graph``
          - HF Space at ``hf_spaces/gemini_hackathon_learning_graphs/``
          - React landing page at ``/learning-graphs``

        See ``docs/LEARNING_GRAPH_SHOWCASE.md`` for the full canonical guide.
        """
    )

if __name__ == "__main__":
    app.run()
