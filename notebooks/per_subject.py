# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "altair",
#     "pandas",
#     "ibis-framework[duckdb]",
# ]
# ///

"""Per-subject interactive teaching notebook.

Embedded via the <MarimoEmbed> React component on the
/subjects/<subject> route. The marimo WASM bundle runs in the browser
without any backend; the cloud deployment uses marimo.run to serve
the notebook as an app.
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="full", app_title="gemini_hackathon - Subject Notebook")


@app.cell
def _intro():
    import marimo as mo
    return mo,


@app.cell
def _header(mo):
    return mo.md(
        r"""
        # Subject Notebook

        Interactive teaching surface for a single (subnation, cycle, subject)
        triple. Default: **Ireland / Leaving Cycle / Mathematics**.
        """
    )


@app.cell
def _controls(mo):
    subnation = mo.ui.dropdown(
        options=["ireland", "england", "northern_ireland", "scotland", "wales"],
        value="ireland",
        label="Subnation",
    )
    cycle = mo.ui.dropdown(
        options=["leaving_cycle", "junior_cycle", "gcse", "a_level",
                 "national_5", "higher", "advanced_higher"],
        value="leaving_cycle",
        label="Cycle",
    )
    subject = mo.ui.text_input(value="Mathematics", label="Subject")
    return subnation, cycle, subject


@app.cell
def _outcomes_table(mo, subnation, cycle, subject):
    """Current syllabus outcomes for the chosen (subnation, cycle, subject)."""
    fallback_outcomes = [
        {"code": "LC-MATHS-1.1", "topic": "Algebra",
         "descriptor": "In line with expectations"},
        {"code": "LC-MATHS-1.2", "topic": "Functions",
         "descriptor": "Above expectations"},
        {"code": "LC-MATHS-2.1", "topic": "Differentiation",
         "descriptor": "In line with expectations"},
        {"code": "LC-MATHS-2.2", "topic": "Integration",
         "descriptor": "Exceptional"},
        {"code": "LC-MATHS-3.1", "topic": "Complex Numbers",
         "descriptor": "Above expectations"},
    ]
    return mo.ui.table(fallback_outcomes, label="Syllabus outcomes (stub fallback)"), fallback_outcomes


@app.cell
def _descriptor_chart(mo, fallback_outcomes):
    import pandas as pd
    import altair as alt
    counts = pd.DataFrame(
        [(d["descriptor"], 1) for d in fallback_outcomes],
        columns=["descriptor", "count"],
    )
    chart = (
        alt.Chart(counts)
        .mark_bar()
        .encode(x="descriptor:N", y="count:Q", color="descriptor:N")
        .properties(width=500, height=200, title="NCCA descriptor distribution")
    )
    return chart, counts


@app.cell
def _study_suggestions(mo, subnation, cycle, subject):
    suggestions = [
        f"Focus on {subject} past papers from the last 3 years",
        "Drill descriptor-based mark schemes (Exceptional → Yet to meet)",
        f"Cross-check with {cycle.replace('_', ' ')} syllabus grid",
        f"For {subnation.upper()}: review your awarding body's marking scheme",
    ]
    return mo.vstack(
        [mo.md(f"### Study suggestions for **{subject}**")] +
        [mo.md(f"- {s}") for s in suggestions]
    )


@app.cell
def _layout(header, controls, outcomes_table, descriptor_chart, study_suggestions):
    return header, controls, outcomes_table, descriptor_chart, study_suggestions


if __name__ == "__main__":
    app.run()
