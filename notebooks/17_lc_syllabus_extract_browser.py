# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "pandas",
#     "plotly",
# ]
# ///

"""Notebook 17 — LC syllabus extract browser.

Read-only marimo notebook that connects to the canonical
``data/bi_ep/extracted_syllabi.sqlite`` SQLite mirror and lets the
operator pick a subject, browse its BAML extraction rows, and inspect
the module_topics tree. The Plotly treemap is a placeholder — the
real layout lives in notebooks 10/11/12 once the BAML client is
fully wired (the 10 rows currently in the DB are all stubs).
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _intro() -> None:
    import marimo as mo
    mo.md(
        """
        # Notebook 17 — LC Syllabus Extract Browser

        Browse the BAML-extracted LC/JC syllabi stored in
        `data/bi_ep/extracted_syllabi.sqlite`. Pick a subject below to
        filter the rows; the table on the right shows the canonical
        `id · pdf_path · baml_function · extracted_at · confidence_avg`
        tuple for each row.

        The treemap below is a placeholder — Lane A's
        `baml_extracts/education/ExtractCurriculumSyllabus.baml` will
        populate the real `module_topics` once the BAML client is
        wired.
        """
    )
    return (mo,)


@app.cell
def _connect(mo) -> None:
    import sqlite3
    import pathlib
    db_path = pathlib.Path("data/bi_ep/extracted_syllabi.sqlite")
    if not db_path.exists():
        mo.md(f"**No SQLite DB at `{db_path}`.** Run the W5 DLT pipeline first.")
        return None, None, db_path
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        "SELECT id, pdf_path, baml_function, extracted_at, confidence_avg, output_json "
        "FROM extracted_syllabi ORDER BY id"
    ).fetchall()
    con.close()
    return rows, db_path


@app.cell
def _subjects(mo, rows) -> None:
    if not rows:
        return mo, [], []
    # Derive a subject label from the baml_function (Extract{CS,Maths,…}LearningGraph) or
    # from the pdf_path. The 10 current rows split into:
    #   - ExtractCSLearningGraph          → CS / computing
    #   - ExtractPedagogyPrinciples       → pedagogy (cross-subject)
    #   - ExtractSourcePalette            → NCCA policy (no subject)
    #   - ExtractMathsLearningGraph       → mathematics
    baml_to_subject = {
        "ExtractCSLearningGraph": "Computer Science",
        "ExtractPedagogyPrinciples": "Pedagogy",
        "ExtractSourcePalette": "NCCA Policy",
        "ExtractMathsLearningGraph": "Mathematics",
    }
    subjects = sorted({baml_to_subject.get(r[2], r[2]) for r in rows})
    default_subjects = ["(all)"] + subjects
    dropdown = mo.ui.dropdown(
        options=default_subjects,
        value="(all)",
        label="Subject (derived from baml_function)",
    )
    dropdown
    return baml_to_subject, default_subjects, dropdown, subjects


@app.cell
def _filtered(mo, rows, baml_to_subject, dropdown) -> None:
    chosen = dropdown.value if dropdown else "(all)"
    if chosen == "(all)":
        filt = rows
    else:
        # Reverse-lookup: which baml_function maps to the chosen subject?
        target_funcs = [k for k, v in baml_to_subject.items() if v == chosen]
        filt = [r for r in rows if r[2] in target_funcs] if target_funcs else rows
    if not filt:
        mo.md(f"**No rows for subject `{chosen}`.**")
        return filt, chosen
    table = mo.ui.table(
        data=[
            {
                "id": r[0],
                "pdf_path": r[1].split("/")[-1] if r[1] else "",
                "baml_function": r[2],
                "extracted_at": r[3],
                "confidence_avg": round(r[4], 4) if r[4] else 0.0,
            }
            for r in filt
        ],
        selection=None,
        pagination=True,
        label=f"Rows for `{chosen}`",
    )
    table
    return filt, chosen, table


@app.cell
def _treemap(mo, rows) -> None:
    import json
    try:
        import plotly.graph_objects as go
    except ImportError:
        mo.md("Install `plotly` to see the module_topics treemap.")
        return

    # Build the treemap from each row's output_json. Stub rows have no
    # module_topics so we synthesise a placeholder label keyed by
    # baml_function so the viz is still informative.
    labels: list[str] = []
    parents: list[str] = []
    values: list[int] = []

    root_label = "extracted_syllabi"
    labels.append(root_label)
    parents.append("")
    values.append(max(1, len(rows)))

    for r in rows:
        func = r[2] or "Unknown"
        labels.append(func)
        parents.append(root_label)
        values.append(1)
        try:
            obj = json.loads(r[5])
            mods = obj.get("module_topics", []) or []
            if mods:
                labels.append(f"{func}/module_topics")
                parents.append(func)
                values.append(len(mods))
            for m in mods:
                mt = m.get("title", "(no title)")[:60]
                labels.append(f"{func}/{mt}")
                parents.append(f"{func}/module_topics")
                values.append(len(m.get("learning_outcomes", [])))
        except Exception:
            # stub JSON — leave the function-level tile alone
            pass

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
        ),
    )
    fig.update_layout(
        title=f"module_topics treemap · {len(rows)} rows",
        margin=dict(t=40, l=0, r=0, b=0),
        height=420,
    )
    mo.ui.plotly(fig)
    return


if __name__ == "__main__":
    app.run()