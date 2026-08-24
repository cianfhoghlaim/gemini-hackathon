# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "altair",
#     "pandas",
# ]
# ///

"""Notebook 01 - cross-jurisdiction equivalency map.

Hard-coded Mathematics topic equivalencies across the 8 BI jurisdictions.
In production this would call the EquivalencyGenerator agent + the BAML
``ExtractEquivalencies`` function.
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium", app_title="gemini_hackathon - BIE Equivalency Map")


@app.cell
def _intro(mo):
    mo.md(
        """
        # Cross-Jurisdiction Equivalency Map — gemini_hackathon

        Stub notebook showing how Mathematics topics map across the 8 BI jurisdictions.
        In production the EquivalencyGenerator agent + the BAML ``ExtractEquivalencies``
        function populate this data automatically from the per-source LC PDFs.
        """
    )
    return (mo,)


@app.cell
def _stub_data():
    rows = [
        {
            "source_topic": "Algebra & Functions",
            "Ireland": "Algebra & Functions",
            "England (AQA)": "Algebra and functions",
            "England (OCR)": "Algebra",
            "England (Pearson)": "Pure Mathematics 1 - Algebra",
            "Scotland": "Expressions and Functions",
            "Wales": "Algebra and Functions",
            "Northern Ireland": "Algebra",
            "Isle of Man": "GCSE Mathematics (EdExcel International)",
        },
        {
            "source_topic": "Complex Numbers",
            "Ireland": "Complex Numbers",
            "England (AQA)": "Complex numbers (A-Level Further)",
            "England (OCR)": "Complex numbers",
            "England (Pearson)": "Pure 2 - Complex numbers",
            "Scotland": "Complex numbers (AH)",
            "Wales": "Complex numbers",
            "Northern Ireland": "Complex numbers (A2)",
            "Isle of Man": "A-Level Further Maths",
        },
        {
            "source_topic": "Calculus",
            "Ireland": "Differentiation & Integration",
            "England (AQA)": "Calculus",
            "England (OCR)": "Calculus",
            "England (Pearson)": "Pure 2 - Calculus",
            "Scotland": "Differentiation & Integration",
            "Wales": "Calculus",
            "Northern Ireland": "Calculus",
            "Isle of Man": "Calculus",
        },
    ]
    return (rows,)


@app.cell
def _render_table(rows, mo):
    import pandas as pd
    df = pd.DataFrame(rows)
    mo.ui.table(df)


if __name__ == "__main__":
    app.run()
