# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "duckdb",
#     "altair",
#     "pandas",
#     "ibis-framework[duckdb]",
#     "motherduck",
# ]
# ///

"""Notebook 00 - theming extraction across the 13 BI sources.

Demonstrates:
- Loading all 13 palettes (8 BI jurisdictions + 5 safeguarding bodies)
- Picking one via dropdown
- Showing color swatches, typography, flag, jurisdiction, level
- An Altair chart of all 13 palettes side by side
- A side-by-side comparator of 2-3 palettes
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium", app_title="gemini_hackathon - Theming Extraction")


@app.cell
def _intro():
    import marimo as mo
    mo.md(
        """
        # Theming Extraction — gemini_hackathon

        Per-source palette extraction across the **8 British Isles jurisdictions** and the
        **5 safeguarding bodies** that govern them. Switch palette via the dropdown
        below; the colour swatches, typography, and Altair chart will re-render.
        """
    )
    return (mo,)


@app.cell
def _load_palettes():
    from notebooks._shared.theme import load_all_palettes, palette_count
    palettes = load_all_palettes()
    count = palette_count()
    return count, palettes


@app.cell
def _show_count(count, palettes, mo):
    mo.md(f"**{count}** palettes loaded:\n\n" + "\n".join(
        f"- `{p['sourceKey']}` ({p['jurisdiction']})" for p in palettes
    ))
    return


@app.cell
def _selector(palettes, mo):
    options = {p["sourceKey"]: f"{p.get('flag', '')} {p['sourceName']}" for p in palettes}
    dropdown = mo.ui.dropdown(
        options=options,
        value="ncca.ie",
        label="Pick a source",
    )
    dropdown
    return dropdown, options


@app.cell
def _render_palette(dropdown, palettes, mo):
    from notebooks._shared.theme import load_palette
    selected = dropdown.value
    palette = load_palette(selected)
    if not palette:
        return mo.md(f"Palette `{selected}` not found.")
    return mo.vstack([
        mo.md(f"### {palette.get('source_name', '')} {palette.get('flag', '')}"),
        mo.md(f"**Jurisdiction:** {palette.get('jurisdiction', '')}"),
        mo.md(f"**Level:** {palette.get('level', '')}"),
        mo.md(
            f"**Colors:** "
            f"<span style='background:{palette.get('primary', '#000')};color:#fff;padding:2px 8px;border-radius:4px'>primary {palette.get('primary', '')}</span> "
            f"<span style='background:{palette.get('secondary', '#000')};color:#fff;padding:2px 8px;border-radius:4px'>secondary {palette.get('secondary', '')}</span> "
            f"<span style='background:{palette.get('accent', '#000')};color:#000;padding:2px 8px;border-radius:4px'>accent {palette.get('accent', '')}</span> "
            f"<span style='background:{palette.get('background', '#fff')};color:{palette.get('text', '#000')};padding:2px 8px;border:1px solid #ddd;border-radius:4px'>bg {palette.get('background', '')}</span>"
        ),
        mo.md(
            f"**Typography:** heading=`{palette.get('heading_font', '')}`, body=`{palette.get('body_font', '')}`"
        ),
    ])


@app.cell
def _all_palettes_chart(palettes):
    import altair as alt
    import pandas as pd
    df = pd.DataFrame([
        {
            "source": p["sourceKey"],
            "primary": p.get("primary", "#000000"),
            "jurisdiction": p.get("jurisdiction", ""),
        }
        for p in palettes
    ])
    chart = (
        alt.Chart(df)
        .mark_circle(size=400)
        .encode(
            x=alt.X("source:N", sort=None, title="Source"),
            y=alt.Y("jurisdiction:N", title="Jurisdiction"),
            color=alt.Color("primary:N", scale=None, legend=None),
        )
        .properties(width=600, height=300, title="All 13 palettes - primary color by jurisdiction")
    )
    chart
    return


@app.cell
def _side_by_side(palettes, mo):
    options = {p["sourceKey"]: f"{p.get('flag', '')} {p['sourceName']}" for p in palettes}
    multi = mo.ui.multiselect(
        options=options,
        value=["ncca.ie", "aqa.org.uk", "sqa.org.uk"],
        label="Compare 2-3 palettes",
    )
    multi
    return multi, options


@app.cell
def _compare_render(multi, options):
    from notebooks._shared.theme import load_palette
    cols = []
    for source_key in multi.value:
        palette = load_palette(source_key)
        if not palette:
            continue
        cols.append(
            f"<div style='flex:1;border:1px solid #ccc;border-radius:8px;padding:12px;margin:4px'>"
            f"<h4>{palette.get('flag', '')} {palette.get('source_name', '')}</h4>"
            f"<div style='background:{palette.get('primary')};color:#fff;padding:8px;border-radius:4px'>{palette.get('primary')}</div>"
            f"<div style='background:{palette.get('secondary')};color:#fff;padding:8px;border-radius:4px;margin-top:4px'>{palette.get('secondary')}</div>"
            f"<div style='background:{palette.get('accent')};color:#000;padding:8px;border-radius:4px;margin-top:4px'>{palette.get('accent')}</div>"
            f"<p style='margin-top:8px;font-size:0.875em'>heading={palette.get('heading_font')}<br>body={palette.get('body_font')}</p>"
            f"</div>"
        )
    import marimo as mo
    mo.Html(f"<div style='display:flex'>{''.join(cols)}</div>")


if __name__ == "__main__":
    app.run()
