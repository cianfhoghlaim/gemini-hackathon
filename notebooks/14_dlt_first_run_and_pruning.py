# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "pandas",
# ]
# ///

"""Notebook 14 — DLT first-run + pruning walkthrough.

Phase 1 of the BIEP data plane. Inspects the canonical DuckDB at
``gemini_hackathon.duckdb`` and shows the ``raw.official_documents``
table:

  1. Connect to DuckDB (read-only).
  2. Print the per-source-kind row counts.
  3. Print the in-scope vs pruned summary (using the
     ``dlt_pipelines._subject_base._prune_rows`` helper).
  4. Render an interactive ``mo.ui.table`` of the kept + pruned rows.

The notebook is the marimo companion to ``Phase 1 — DLT first run +
source pruning`` in the Lane-A playbook. It assumes the
``dlt_pipelines.uk_ncce_learning_graphs`` pipeline has already been
run (the canonical smoke test is ``make dlt-smoke-all``).
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _intro() -> None:
    import marimo as mo
    mo.md(
        """
        # Phase 1 — DLT first-run + pruning

        This notebook inspects the canonical DuckDB after the Phase 1
        DLT substrate has been run. The ``raw.official_documents``
        table holds:

          - 11 NCCE rows (5 PDF rows + 1 placeholder + 6 per-subject
            tags — see ``dlt_pipelines.uk_ncce_learning_graphs``)
          - 35 ``remote_url`` rows from the other 9 British Isles
            jurisdictions (no PDF on disk yet)
          - 4 ``local_filesystem`` rows from the committed NCCE PDFs

        The pruning rules from ``dlt_pipelines._subject_base`` are
        applied to flag out-of-scope rows (subjects outside the 6
        priority subjects).
        """
    )
    return (mo,)


@app.cell
def _imports() -> None:
    import duckdb
    import pandas as pd

    from dlt_pipelines._subject_base import _prune_rows
    return _prune_rows, duckdb, pd


@app.cell
def _connect(mo) -> None:
    from pathlib import Path

    duckdb_path = Path("gemini_hackathon.duckdb").resolve()
    if not duckdb_path.is_file():
        mo.md(
            f"**DuckDB not found at `{duckdb_path}`** — run `make dlt-smoke-all` first."
        )
        con = None
    else:
        con = duckdb.connect(str(duckdb_path), read_only=True)
    return (con,)


@app.cell
def _summary(con, mo) -> None:
    if con is None:
        return
    summary_df = con.execute(
        """
        SELECT source_kind,
               COUNT(*) AS n_rows,
               COUNT(DISTINCT sha256_hash) AS n_unique_sha
        FROM raw.official_documents
        GROUP BY source_kind
        ORDER BY source_kind
        """
    ).df()
    mo.ui.table(summary_df, label="Per-source-kind row counts")
    return (summary_df,)


@app.cell
def _load(con) -> None:
    if con is None:
        return (None,)
    rows = con.execute(
        """
        SELECT source_key, subject, language, page_count,
               sha256_hash, source_kind
        FROM raw.official_documents
        """
    ).fetchall()
    cols = [
        "source_key", "subject", "language", "page_count",
        "sha256_hash", "source_kind",
    ]
    row_dicts = [dict(zip(cols, r)) for r in rows]
    return (row_dicts,)


@app.cell
def _prune(row_dicts, _prune_rows, pd) -> None:
    if row_dicts is None:
        return None, None
    pruned = _prune_rows(row_dicts)
    kept = [r for r in pruned if not r.get("pruned")]
    flagged = [r for r in pruned if r.get("pruned")]
    return pd.DataFrame(kept), pd.DataFrame(flagged)


@app.cell
def _tables(mo, kept, flagged) -> None:
    if kept is None:
        return
    kept_table = mo.ui.table(
        kept,
        label=f"In-scope rows (n={len(kept)})",
        page_size=20,
    )
    flagged_table = mo.ui.table(
        flagged,
        label=f"Pruned / out-of-scope rows (n={len(flagged)})",
        page_size=20,
    )
    mo.vstack([kept_table, flagged_table])
    return (kept_table, flagged_table)


if __name__ == "__main__":
    app.run()
