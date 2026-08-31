"""gemini_hackathon_gradio.anam_education — the Education Integration Studio.

Lifted from `sruth/spaces/anam_tuatha/` and rewritten for the British
Isles education theme. The Anam (Spirit) integration studio:

  - 7 features mapped to the 5 education stages + 2 cross-cutting:
    1. Curriculum Map (Bunscoil pattern)         - stage accent: Bunscoil-blue
    2. Chemistry Visual (chemistry diagrams)      - stage accent: MeanScoil-green
    3. Exit Card - Formative Assessment            - stage accent: Scoil Sinsearach-gold
    4. Gaelscribhneoir (Irish text quality)        - stage accent: Aistear-orange
    5. Bilingual EN/GA Toggle (Fiosraigh)          - stage accent: Ollscoil-indigo
    6. Certificate Generation (Anam)              - stage accent: Ollscoil-indigo
    7. Skill Progression Ledger (Anam)             - stage accent: Ollscoil-indigo

The Celtic myth of 5 elements (Talamh/Uisce/Tine/Aer/Anam) is replaced
with the 5 education stages (Aistear/Bunscoil/MeanScoil/Scoil
Sinsearach/Ollscoil). The "soulbound token" feature is replaced with
the "skill progression ledger" (W9).

The full app implementation is in W12 (the big Gradio editorial
studio on Cloud Run). This package provides the per-feature modules
that the editorial canvas wires together.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

from .._common import (
    GRADIO_CSS,
    apply_education_theme,
    render_anam_bonneagar_footer,
    set_lang,
)
from .._common import (
    translate as t,
)

_log = logging.getLogger("anam_education.app")
set_lang("en")


# Shared data paths — every per-tab handler reads from the canonical
# `data/bi_ep/extracted_syllabi.sqlite` + `gemini_hackathon.duckdb` + the
# `data/syllabi/` PDF folder. Keeping the paths here (not in each tab)
# means a single edit updates every feature.
_DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
_SYLLABI_SQLITE = _DATA_ROOT / "bi_ep" / "extracted_syllabi.sqlite"
_DUCKDB_PATH = _DATA_ROOT.parent / "gemini_hackathon.duckdb"
_SYLLABI_PDF_DIR = _DATA_ROOT / "syllabi"


def _load_syllabi_rows(limit: int = 25) -> list[list]:
    """Read the top N rows from `data/bi_ep/extracted_syllabi.sqlite`."""
    if not _SYLLABI_SQLITE.exists():
        return [["ERROR", f"missing {_SYLLABI_SQLITE}"]]
    try:
        with sqlite3.connect(_SYLLABI_SQLITE) as con:
            rows = con.execute(
                "SELECT id, pdf_path, baml_function, extracted_at, confidence_avg "
                "FROM extracted_syllabi ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [list(r) for r in rows]
    except Exception as exc:  # noqa: BLE001 — surfaces in UI
        return [["ERROR", str(exc), "", "", ""]]


def _load_skill_progression(limit: int = 50) -> list[list]:
    """Read the skill-progression ledger from DuckDB (raw.official_documents)."""
    if not _DUCKDB_PATH.exists():
        return [["ERROR", f"missing {_DUCKDB_PATH}"]]
    try:
        import duckdb

        with duckdb.connect(str(_DUCKDB_PATH), read_only=True) as con:
            rows = con.execute(
                "SELECT source_id, jurisdiction, level, subject, language, file_size_bytes "
                "FROM raw.official_documents ORDER BY jurisdiction, level LIMIT ?",
                (limit,),
            ).fetchall()
        return [list(r) for r in rows]
    except Exception as exc:  # noqa: BLE001 — surfaces in UI
        return [["ERROR", str(exc), "", "", "", ""]]


def _list_syllabi_pdfs() -> list[str]:
    """Return the file paths of every PDF in `data/syllabi/`."""
    if not _SYLLABI_PDF_DIR.exists():
        return []
    return sorted(str(p) for p in _SYLLABI_PDF_DIR.glob("**/*.pdf"))


def build_app():
    """Build the Anam Oideachais (Education Integration Studio) Gradio app.

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with "
            "`pip install gradio>=6.0,<7.0`"
        )

    # The 7 features are wired as Gradio tabs. Each tab delegates to the
    # per-feature module (lifted in W12):
    #
    #   - Curriculum Map        -> data/bi_ep/extracted_syllabi.sqlite (W5)
    #   - Chemistry Visual      -> Placeholder Plotly scatter (Molmo2 placeholder)
    #   - Exit Card             -> Reportlab PDF stub (PExitCardSet stub)
    #   - Gaelscribhneoir       -> Grammar check stub (Aistear)
    #   - Bilingual EN/GA       -> Side-by-side render (Fiosraigh)
    #   - Certificate           -> gr.Gallery of data/syllabi/*.pdf (W14)
    #   - Skill Progression     -> DuckDB raw.official_documents (W9)
    with gr.Blocks(
        theme=apply_education_theme(), css=GRADIO_CSS, title="Anam Oideachais"
    ) as demo:
        gr.Markdown(
            f"""# {t("anam_education.title")}
### *{t("anam_education.subtitle")}*

The integration studio — every feature of the British Isles education
system, on one canvas. Each tab maps to one of the 5 stage coordinators
(W7) and is wired to the corresponding data pipeline (W5).""",
            elem_classes="stage-ollscoil",
        )

        with gr.Tabs():
            # 1. Curriculum Map — top-N rows from the BAML-extracted syllabi
            with gr.Tab("Curriculum Map", elem_classes="stage-bunscoil"):
                gr.Markdown(
                    "**Per-subject LC + JC syllabus map.** Reads the BAML "
                    "extractions from `data/bi_ep/extracted_syllabi.sqlite` "
                    "(Lane A owns the W5 DLT pipeline that populates it)."
                )
                cm_refresh = gr.Button("Refresh", variant="primary")
                cm_df = gr.Dataframe(
                    headers=["id", "pdf_path", "baml_function", "extracted_at", "confidence_avg"],
                    value=_load_syllabi_rows(),
                    interactive=False,
                    wrap=True,
                )
                cm_refresh.click(fn=lambda: _load_syllabi_rows(), outputs=[cm_df])

            # 2. Chemistry Visual — Plotly scatter (Molmo2 placeholder)
            with gr.Tab("Chemistry Visual", elem_classes="stage-meanscoil"):
                gr.Markdown(
                    "**SVG / Plotly molecule renderer.** Placeholder — "
                    "real Molmo2 diagram extraction lives in the W12 "
                    "chemistry_visual module."
                )
                try:
                    import plotly.graph_objects as go

                    fig = go.Figure(
                        data=go.Scatter(
                            x=[1, 2, 3, 4, 5, 6, 7, 8],
                            y=[1, 4, 9, 16, 25, 36, 49, 64],
                            mode="lines+markers",
                            name="placeholder reactivity curve",
                        )
                    )
                    fig.update_layout(
                        title="Reaction rate vs. time (placeholder until Molmo2)",
                        xaxis_title="time (s)",
                        yaxis_title="concentration (mol/L)",
                    )
                    chem_plot = gr.Plot(value=fig, label="Reactivity curve")
                except ImportError:
                    chem_plot = gr.Markdown("Install `plotly` to see the placeholder chart.")

            # 3. Exit Card — BAML-driven formative assessment stub
            with gr.Tab("Exit Card", elem_classes="stage-scoil-sinsearach"):
                gr.Markdown(
                    "**Formative-assessment exit-card generator.** "
                    "Returns a PDF stub via Reportlab when available; "
                    "falls back to a Markdown stub otherwise."
                )
                with gr.Row():
                    ec_topic = gr.Textbox(
                        value="LC Maths — differentiation",
                        label="Topic",
                    )
                    ec_learner = gr.Textbox(
                        value="Maya O'Brien",
                        label="Learner",
                    )
                ec_btn = gr.Button("Generate exit card", variant="primary")
                ec_out = gr.File(label="Generated PDF (or stub)")
                ec_status = gr.Markdown()

                def _generate_exit_card(topic: str, learner: str):
                    """Build a 1-page exit card PDF via Reportlab."""
                    try:
                        from reportlab.lib.pagesizes import A4
                        from reportlab.pdfgen import canvas

                        out_path = Path("/tmp") / f"exit_card_{learner.replace(' ', '_')}.pdf"
                        c = canvas.Canvas(str(out_path), pagesize=A4)
                        c.setFont("Helvetica-Bold", 16)
                        c.drawString(72, 770, f"Exit Card — {learner}")
                        c.setFont("Helvetica", 11)
                        c.drawString(72, 740, f"Topic: {topic}")
                        c.drawString(72, 720, "Q1. What did you learn today?")
                        c.drawString(72, 700, "Q2. What is still unclear?")
                        c.drawString(72, 680, "Q3. One question you'd like answered.")
                        c.save()
                        return str(out_path), f"Generated **{out_path.name}** via Reportlab."
                    except ImportError:
                        stub_path = Path("/tmp") / f"exit_card_{learner.replace(' ', '_')}.md"
                        stub_path.write_text(
                            f"# Exit Card — {learner}\n\nTopic: {topic}\n\n"
                            "Q1. What did you learn today?\n\n"
                            "Q2. What is still unclear?\n\n"
                            "Q3. One question you'd like answered.\n",
                            encoding="utf-8",
                        )
                        return str(stub_path), "Reportlab not installed — wrote a Markdown stub."

                ec_btn.click(
                    fn=_generate_exit_card,
                    inputs=[ec_topic, ec_learner],
                    outputs=[ec_out, ec_status],
                )

            # 4. Gaelscribhneoir — Irish grammar helper stub
            with gr.Tab("Gaelscribhneoir", elem_classes="stage-aistear"):
                gr.Markdown(
                    "**Irish-text quality checker.** Checks for missing "
                    "fada marks + the 11 séimhiú/eclipsis patterns. Stub "
                    "for now — full grammar model lives in W12."
                )
                gs_input = gr.Textbox(
                    value="Tá mé ag dul go dtí an scoil gach maidin.",
                    label="Irish text",
                    lines=4,
                )
                gs_btn = gr.Button("Check", variant="primary")
                gs_out = gr.Markdown()

                def _gaelscribhneoir_check(text: str) -> str:
                    """Heuristic Irish-text quality report (stub)."""
                    if not text:
                        return "_Provide some Irish text above._"
                    notes = []
                    if "á" not in text and "é" not in text and "í" not in text and "ó" not in text and "ú" not in text:
                        notes.append("- ⚠️ No fada-marked vowels detected — check whether any should appear.")
                    if "dt" in text:
                        notes.append("- ✅ Found an eclipsis (`dt` after `go` / `ar` / etc.) — well done.")
                    if "mb" in text or "gc" in text or "nd" in text or "ng" in text:
                        notes.append("- ✅ Detected at least one séimhiú.")
                    notes.append(f"- {len(text.split())} words · {len(text)} chars")
                    notes.append("\n_Full Gaelscribhneoir module is in W12 — this is a stub._")
                    return "\n".join(notes)

                gs_btn.click(fn=_gaelscribhneoir_check, inputs=[gs_input], outputs=[gs_out])

            # 5. Bilingual EN/GA — side-by-side toggle
            with gr.Tab("Bilingual EN/GA", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "**Bilingual EN/GA toggle.** Enter the same content in "
                    "both languages and the renderer shows them side-by-side."
                )
                with gr.Row():
                    en_text = gr.Textbox(
                        value="Welcome to the British Isles Education Platform.",
                        label="English",
                        lines=4,
                    )
                    ga_text = gr.Textbox(
                        value="Fáilte go dtí an Ardán Oideachais na nOileán Briotanacha.",
                        label="Gaeilge",
                        lines=4,
                    )
                bil_btn = gr.Button("Render side-by-side", variant="primary")
                bil_out = gr.Markdown()

                def _render_bilingual(en: str, ga: str) -> str:
                    return (
                        f"| EN | GA |\n|---|---|\n"
                        f"| {en.replace(chr(10), ' ')} | {ga.replace(chr(10), ' ')} |\n\n"
                        f"_Welsh / Scottish Gaelic / Manx toggles land in W12._"
                    )

                bil_btn.click(fn=_render_bilingual, inputs=[en_text, ga_text], outputs=[bil_out])

            # 6. Certificate — gallery of syllabus PDFs
            with gr.Tab("Certificate", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "**LC/JC certificate generation** from the 5 NCCA "
                    "policy PDFs (W2). This tab shows the source PDFs the "
                    "certificate is composed from."
                )
                pdf_paths = _list_syllabi_pdfs()
                if pdf_paths:
                    cert_gal = gr.Gallery(
                        value=[(p, Path(p).name) for p in pdf_paths],
                        label="Source PDFs in data/syllabi/",
                        columns=2,
                        height="auto",
                    )
                else:
                    cert_gal = gr.Markdown("_No PDFs in `data/syllabi/`._")

            # 7. Skill Progression — DuckDB mastery ledger
            with gr.Tab("Skill Progression", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "**Per-learner mastery ledger (W9).** Reads "
                    "`raw.official_documents` from `gemini_hackathon.duckdb` "
                    "as the canonical evidence-source index."
                )
                sp_refresh = gr.Button("Refresh", variant="primary")
                sp_df = gr.Dataframe(
                    headers=["source_id", "jurisdiction", "level", "subject", "language", "file_size_bytes"],
                    value=_load_skill_progression(),
                    interactive=False,
                    wrap=True,
                )
                sp_refresh.click(fn=lambda: _load_skill_progression(), outputs=[sp_df])

        render_anam_bonneagar_footer(
            space_id="cianfhoghlaim/gemini-hackathon-anam-education",
            subnation="Ireland (NCCA)",
            stage="Scoil Sinsearach",
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)


__all__ = ["build_app"]
