# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "plotly",
#     "pandas",
# ]
# ///

"""Notebook 20 — Full pipeline walkthrough over the in-scope corpus.

Connects to `data/bi_ep/extracted_syllabi.sqlite` (the `processed_inscope`
table written by `scripts/process_inscope_pdfs.py`) and visualises the
end-to-end Docling → → BAML → → embedding chain over the 97 in-scope PDFs.

Run the processor first:
  uv run python scripts/process_inscope_pdfs.py --all
"""
import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _intro() -> None:
    import marimo as mo
    mo.md(
        """
        # Notebook 20 — Full Pipeline Walkthrough

        End-to-end visualisation of the **97 in-scope PDFs** (5 NCCA + 5 NCCE +
        87 LC English + 1 sample). Each row is one PDF that ran through:

        1. **Docling** — PDF → Markdown (preserves NCCE row × column grids)
        2. **BAML** — `ExtractCurriculumSyllabus` / `ExtractMathsSyllabus` /
           `ExtractCSLearningGraph` / `ExtractPedagogyPrinciples` (per subject)
        3. **Embedding** — `BAAI/bge-m3` (1024-d, offline)

        The output lives in `data/bi_ep/extracted_syllabi.sqlite`
        (table: `processed_inscope`).

        ## Models

        - **Layout**: Docling
        - **OCR fallback**: `gemma-4-26b-a4b-vision` (llama-swap)
        - **BAML extraction**: `gemini-3.5-flash` (Vertex AI)
        - **Embedding**: `BAAI/bge-m3` (1024-d)
        """
    )
    return (mo,)


@app.cell
def _connect(mo) -> None:
    import sqlite3, pathlib
    db_path = pathlib.Path("data/bi_ep/extracted_syllabi.sqlite")
    if not db_path.exists():
        mo.md(f"**No SQLite DB at `{db_path}`. Run `make baml` + `scripts/process_inscope_pdfs.py --all` first.**")
        return None, None
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        "SELECT pdf_path, jurisdiction, subject, baml_function, "
        "processing_ms, extracted_at FROM processed_inscope ORDER BY processing_ms DESC"
    ).fetchall()
    cols = ["pdf_path", "jurisdiction", "subject", "baml_function", "processing_ms", "extracted_at"]
    con.close()
    return rows, cols


@app.cell
def _table(mo, rows, cols) -> None:
    if not rows:
        return
    mo.ui.table([dict(zip(cols, r)) for r in rows[:30]], selection=None)


@app.cell
def _scatter(mo, rows) -> None:
    import plotly.graph_objects as go
    if not rows:
        return
    by_subject: dict[str, list[float]] = {}
    for pdf_path, jurisdiction, subject, _baml, ms, _at in rows:
        by_subject.setdefault(subject or "?", []).append(ms)
    fig = go.Figure()
    for subject, mss in sorted(by_subject.items()):
        fig.add_trace(go.Bar(name=subject, x=[subject], y=[sum(mss) / len(mss)]))
    fig.update_layout(
        title="Mean processing time per subject (ms)",
        yaxis_title="ms",
        xaxis_title="subject",
    )
    mo.mpl.interactive(fig) if False else mo.as_html(fig)


@app.cell
def _counts(mo, rows) -> None:
    if not rows:
        return
    counts: dict[str, int] = {}
    for _pdf_path, jurisdiction, _subject, _baml, _ms, _at in rows:
        counts[jurisdiction] = counts.get(jurisdiction, 0) + 1
    mo.md(
        "## Counts by jurisdiction\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in sorted(counts.items()))
    )


if __name__ == "__main__":
    app.run()