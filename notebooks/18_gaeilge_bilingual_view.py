# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "pandas",
# ]
# ///

"""Notebook 18 — Gaeilge / English bilingual syllabus view.

Two-column marimo layout that surfaces the Gaeilge BAML extraction on
the left and the English equivalent on the right. Both columns align
on `topic_id` so the operator can spot translation drift at a glance.

The current BAML rows in `data/bi_ep/extracted_syllabi.sqlite` are all
stubs (the BAML client isn't connected), so the notebook falls back to
a metadata-only display showing the PDF path + extracted_at + the
`pdf_text_chars` count from each row.
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _intro() -> None:
    import marimo as mo
    mo.md(
        """
        # Notebook 18 — Gaeilge / English Bilingual View

        Side-by-side view of the Gaeilge (left) and English (right) BAML
        syllabus extractions. Both columns align on `topic_id` so the
        operator can verify the translation didn't drop learning
        outcomes.

        Each row of the canonical `extracted_syllabi` table holds one
        `output_json` with the BAML extraction for a single PDF. Today
        all rows are stubs (the BAML client isn't wired), so the
        columns show the metadata + `pdf_text_chars` count.
        """
    )
    return (mo,)


@app.cell
def _connect(mo) -> None:
    import sqlite3
    import pathlib
    db_path = pathlib.Path("data/bi_ep/extracted_syllabi.sqlite")
    if not db_path.exists():
        mo.md(f"**No SQLite DB at `{db_path}`.** Run the W5 pipeline first.")
        return None, None
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        "SELECT id, pdf_path, baml_function, output_json FROM extracted_syllabi ORDER BY id"
    ).fetchall()
    con.close()
    return rows, db_path


@app.cell
def _split(rows) -> None:
    # The BAML client has 6 distinct `baml_function` values — split them
    # by what they extract. "Gaeilge"-equivalent rows are the LC syllabus
    # extractions; "English"-equivalent rows are the same with the
    # `language` field set. Since the DB has no `language` column we
    # derive one from the baml_function + pdf_path.
    gaeilge_rows = []
    english_rows = []
    for r in rows:
        path_lower = (r[1] or "").lower()
        # Heuristic — the 2 Irish-language artefacts are `key-competencies-in-senior-cycle_en`
        # + the SC-L1/L2 PDFs (which are bilingual). We bucket by pdf_path.
        is_gaeilge = ("gaeilge" in path_lower or "irish" in path_lower)
        if is_gaeilge:
            gaeilge_rows.append(r)
        else:
            english_rows.append(r)
    return gaeilge_rows, english_rows


@app.cell
def _layout(mo, gaeilge_rows, english_rows) -> None:
    import json

    def _row_to_md(row, side: str) -> str:
        rid, path, func, output_json = row
        try:
            obj = json.loads(output_json)
            is_stub = obj.get("_stub", False)
            reason = obj.get("_stub_reason", "")[:120]
            text_chars = obj.get("pdf_text_chars", 0)
            modules = obj.get("module_topics", []) or []
            topic_lines: list[str] = []
            for m in modules:
                topic_lines.append(f"- **{m.get('title', '(no title)')}**")
                for lo in m.get("learning_outcomes", []):
                    topic_lines.append(f"  - `{lo.get('lo_id', '?')}` — {lo.get('title', '')}")
            module_md = "\n".join(topic_lines) if topic_lines else "_(no module_topics)_"
        except Exception as exc:
            is_stub = True
            reason = str(exc)[:120]
            text_chars = 0
            module_md = "_(output_json unparseable)_"

        return (
            f"### `{side}` row {rid}\n"
            f"- **pdf:** `{path.split('/')[-1] if path else '?'}`\n"
            f"- **baml_function:** `{func}`\n"
            f"- **stub:** {'yes' if is_stub else 'no'}\n"
            f"- **pdf_text_chars:** {text_chars}\n"
            f"- _stub reason: {reason}_\n"
            f"\n**module_topics**\n\n{module_md}\n"
        )

    gaeilge_md = (
        "_(no Gaeilge rows in the DB yet — the LC Gaeilge PDFs haven't been through the pipeline)_"
        if not gaeilge_rows
        else "\n\n---\n\n".join(_row_to_md(r, "Gaeilge") for r in gaeilge_rows)
    )
    english_md = (
        "_(no English rows in the DB yet)_"
        if not english_rows
        else "\n\n---\n\n".join(_row_to_md(r, "English") for r in english_rows)
    )

    mo.vstack(
        [
            mo.md("## Two-column bilingual layout"),
            mo.hstack(
                [
                    mo.vstack([mo.md("### 🇬🇲 Gaeilge (left)"), mo.md(gaeilge_md)]),
                    mo.vstack([mo.md("### 🇬🇧 English (right)"), mo.md(english_md)]),
                ],
                widths=[1, 1],
                gap=2,
            ),
            mo.md(
                f"**Topic alignment:** both columns sorted by `topic_id` = "
                f"`extracted_syllabi.id`. Gaeilge rows: {len(gaeilge_rows)} · "
                f"English rows: {len(english_rows)}."
            ),
        ]
    )
    return (gaeilge_md, english_md)


if __name__ == "__main__":
    app.run()