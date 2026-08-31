# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "pyyaml",
# ]
# ///

"""Notebook 19 — NCCA policy citation explorer.

Reads `data/ireland/ncca_policy/INDEX.yaml` (the canonical NCCA policy
corpus) and renders one card per document with the title, blurb, and a
deep-link to the PDF. Click the citation marker button to scroll to
the stub citation marker — the real per-page anchor ships when
Lane A's `baml_extracts/education/ExtractPolicyCitation.baml` lands.
"""

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def _intro() -> None:
    import marimo as mo
    mo.md(
        """
        # Notebook 19 — NCCA Policy Citation Explorer

        The 5 NCCA policy PDFs are the constitutional source of truth for
        the gemini_hackathon LC/JC certificate pipeline (per the
        `2026-08-27-ncca-policy-corpus-lift-v1` change). Every claim on
        every generated certificate cites a page in one of these PDFs.

        Click **Open PDF** to read the canonical document; click the
        **Citation marker** button to scroll to the stub citation
        marker.
        """
    )
    return (mo,)


@app.cell
def _load_index(mo) -> None:
    import pathlib
    import yaml
    index_path = pathlib.Path("data/ireland/ncca_policy/INDEX.yaml")
    if not index_path.exists():
        mo.md(f"**No INDEX.yaml at `{index_path}`.** Run the policy lift first.")
        return None, None, None
    with index_path.open("r", encoding="utf-8") as fh:
        idx = yaml.safe_load(fh)
    docs = idx.get("documents", []) or []
    return docs, idx, index_path


@app.cell
def _metadata(mo, idx, docs, index_path) -> None:
    mo.vstack(
        [
            mo.md(
                f"**Corpus:** `{idx.get('policy_corpus', '?')}` · "
                f"**Version:** {idx.get('version', '?')} · "
                f"**Source:** `{idx.get('source', '?')}`"
            ),
            mo.md(f"**Documents in corpus:** {len(docs)} · **INDEX:** `{index_path}`"),
        ]
    )
    return


@app.cell
def _cards(mo, docs) -> None:
    import pathlib
    pdf_dir = pathlib.Path("data/ireland/ncca_policy")
    cards = []
    for i, doc in enumerate(docs):
        file = doc.get("file", "?")
        role = doc.get("role", "")
        description = doc.get("description", "").strip()
        cert_rel = doc.get("certificate_relevance", "")
        bytes_ = doc.get("bytes", 0)
        pdf_path = pdf_dir / file
        exists = pdf_path.exists()
        pdf_link = (
            f'<a href="file://{pdf_path}" target="_blank">Open PDF →</a>'
            if exists else f'<span style="color:#999;">(missing on disk)</span>'
        )
        anchor_id = f"citation-{role or file.replace('.pdf','').replace(' ','-').lower()}"
        html = (
            f'<article id="{anchor_id}" style="border:1px solid var(--color-secondary,#ccc);'
            f'border-radius:8px;padding:14px;margin:10px 0;background:var(--color-background,#fafafa);">'
            f'<header style="display:flex;justify-content:space-between;align-items:baseline;">'
            f'<h3 style="margin:0;color:var(--color-primary,#5a4fcf);font-family:var(--font-heading,serif);">{file}</h3>'
            f'<span style="font-family:monospace;font-size:11px;color:#999;">{bytes_:,} bytes</span>'
            f'</header>'
            f'<div style="font-size:11px;color:#777;margin:4px 0 6px 0;font-family:monospace;">'
            f'role: <code>{role}</code> · relevance: <code>{cert_rel}</code>'
            f'</div>'
            f'<p style="font-size:13px;line-height:1.45;">{description}</p>'
            f'<footer style="display:flex;gap:12px;align-items:center;margin-top:8px;">'
            f'{pdf_link}'
            f'<button data-cite-target="{anchor_id}" '
            f'style="font-size:11px;padding:2px 8px;border-radius:4px;border:1px solid #999;background:#fff;cursor:pointer;">'
            f'Citation marker</button>'
            f'</footer>'
            f'</article>'
        )
        cards.append(mo.Html(html))
    mo.vstack(cards)
    return cards, pdf_dir


@app.cell
def _marker_button(mo) -> None:
    # The button is rendered inside each card; clicking it just scrolls
    # the browser to the matching `id` (set on the <article>). Real
    # citation markers (per-page) land with ExtractPolicyCitation.baml.
    mo.md(
        """
        ---
        ## How the citation marker works

        Each card's **Citation marker** button is a placeholder — it
        scrolls to the card itself (the `id` on the `<article>`). When
        Lane A's `baml_extracts/education/ExtractPolicyCitation.baml`
        ships, the button will scroll to the specific page anchor
        (e.g. `#SC-L1-L2-Programme-Statement.pdf:page=12`).
        """
    )
    return


if __name__ == "__main__":
    app.run()