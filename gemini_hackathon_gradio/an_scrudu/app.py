"""gemini_hackathon_gradio.an_scrudu.app — LC past-paper heatmap studio.

Lifted from `sruth/spaces/an_scrudu/app.py` and adapted:

  - Celtic theme replaced with the British Isles 5-stage palette.
  - Celtic mythology strings removed; education strings added.
  - Pydantic `MarkingSchemeExtraction` (from `.extraction`) replaces the
    legacy `CircularExtraction` (legacy compat is in the dataclass too).
  - 3-tier LLM client (LiteLLM → Unsloth Studio → HF Inference) replaces
    the HF-only chain.

The studio is the entry point for the editorial canvas's
"Scoil Sinsearach → An Scrudu" tab (the LC past-paper heatmap).
"""

from __future__ import annotations

import logging
import os

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

from .._common import (
    GRADIO_CSS,
    apply_education_theme,
    render_anam_bonneagar_footer,
    set_lang,
    translate,
)
from .._common.i18n import translate as t
from .._common.pclm_emitter import emit_pclm_pdf_bytes, emit_pclm_xml
from .extraction import MarkingSchemeExtraction, extract_circular
from .heatmap import render_heatmap, render_pclm_html


_log = logging.getLogger("an_scrudu.app")
set_lang("en")


# Built-in sample: LC Chemistry 2024 (canonical SEC paper)
_SAMPLE_FILENAME = "LC_Chemistry_2024_sample.txt"
_SAMPLE_TEXT = """\
Leaving Certificate Examination 2024
Chemistry - Higher Level - Paper 2

Time: 3 hours
Total marks: 300

Section A (100 marks) - Answer all 10 questions
Section B (200 marks) - Answer 4 of 6 questions

Topic distribution (approximate):
CH1 Atomic Structure + Periodic Table    30 marks
CH2 Chemical Bonding                    45 marks
CH3 Stoichiometry + Formulas            30 marks
CH4 Organic Chemistry                   50 marks
CH5 Rates of Reaction + Equilibrium     40 marks
CH6 Acids + Bases                       35 marks
CH7 Electrochemistry                    35 marks
CH8 Optional: Industrial Chemistry      35 marks

Oral: No
Coursework: No

Source: State Examinations Commission
"""


def _on_extract(
    file_obj: gr.File | None,
    use_sample: bool,
) -> tuple[str, str, str, str]:
    """Extract a marking scheme and return the heatmap, PCLM preview, XML, and metadata.

    Returns:
        (heatmap_html, pclm_preview_html, pclm_xml, metadata_md)
    """
    if use_sample or file_obj is None:
        filename, text = _SAMPLE_FILENAME, _SAMPLE_TEXT
    else:
        try:
            filename = file_obj.name.split("/")[-1]
            if filename.endswith(".pdf"):
                return (
                    "",
                    "",
                    "",
                    f"**Note:** PDF parsing requires the `pypdf` package. "
                    f"File: {filename}. For the demo, click 'Use sample paper' "
                    f"to extract from the built-in LC Chemistry 2024 sample.",
                )
            with open(file_obj.name, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except (AttributeError, OSError) as e:
            return ("", "", "", f"**Error reading file:** {e}")

    ext: MarkingSchemeExtraction = extract_circular(text, filename)

    heatmap_html = render_heatmap(ext)
    pclm_preview = render_pclm_html(ext)
    pclm_xml = emit_pclm_xml(ext)

    metadata = (
        f"**{ext.circular.subject} - {ext.circular.issued_year}**\n\n"
        f"- **{t('an_scrudu.heatmap_caption')}**\n"
        f"- Source: `{ext.source_model}`\n"
        f"- Confidence: `{ext.extraction_confidence:.2f}`\n"
        f"- Total: {ext.scheme.total_marking_points} marks across "
        f"{len(ext.scheme.topics)} topics"
    )

    return (heatmap_html, pclm_preview, pclm_xml, metadata)


def _on_download_pdf(file_obj: gr.File | None, use_sample: bool) -> str:
    """Generate a PDF for download. Returns a file path."""
    if use_sample or file_obj is None or (file_obj and file_obj.name.endswith(".pdf")):
        filename, text = _SAMPLE_FILENAME, _SAMPLE_TEXT
    else:
        filename = file_obj.name.split("/")[-1]
        with open(file_obj.name, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

    ext = extract_circular(text, filename)
    pdf_bytes = emit_pclm_pdf_bytes(ext)
    out_path = f"/tmp/{filename.rsplit('.', 1)[0]}_pclm.pdf"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(pdf_bytes)
    return out_path


def build_app():
    """Build the An Scrudu Gradio app (LC past-paper heatmap studio).

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with "
            "`pip install gradio>=6.0,<7.0`"
        )
    with gr.Blocks(
        theme=apply_education_theme(), css=GRADIO_CSS, title="An Scrudu"
    ) as demo:
        gr.Markdown(
            f"""# {t("an_scrudu.title")}
### *{t("an_scrudu.subtitle")}*

**Stage:** Scoil Sinsearach (Senior Cycle / Leaving Certificate) — Tine element.
The 3-tier LLM fallback (LiteLLM → Unsloth Studio → HF Inference) extracts
the marking scheme. If all 3 tiers fail, an offline regex fallback engages
so the heatmap always renders.""",
            elem_classes="stage-scoil-sinsearach",
        )

        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(
                    label=t("an_scrudu.upload_label"),
                    file_types=[".txt", ".md"],
                )
                use_sample_check = gr.Checkbox(
                    label="Use sample paper (LC Chemistry 2024)",
                    value=True,
                )
                extract_btn = gr.Button(
                    t("an_scrudu.extract_button"),
                    variant="primary",
                )
                download_pdf_btn = gr.Button(
                    "Download as PDF",
                    variant="secondary",
                )
                pdf_file = gr.File(label="Generated PDF", visible=False)
            with gr.Column(scale=3):
                metadata_md = gr.Markdown(
                    value="_Click 'Extract Marking Scheme' to begin._",
                    label="Extraction metadata",
                )
                heatmap_html = gr.HTML(
                    value=(
                        '<div style="padding:2em; color:#bcb8b0; '
                        'text-align:center; font-style:italic;">'
                        "Heatmap appears here after extraction.</div>"
                    ),
                    label=t("an_scrudu.heatmap_caption"),
                )

        with gr.Row():
            pclm_preview_html = gr.HTML(
                value=(
                    '<div style="padding:2em; color:#bcb8b0; '
                    'text-align:center; font-style:italic;">'
                    "PCLM preview appears here.</div>"
                ),
                label="PCLM-XML preview",
            )
            pclm_xml = gr.Code(
                value="",
                language="xml",
                label="PCLM-XML (downloadable)",
            )

        # Wire events
        extract_btn.click(
            fn=_on_extract,
            inputs=[file_input, use_sample_check],
            outputs=[heatmap_html, pclm_preview_html, pclm_xml, metadata_md],
        )
        download_pdf_btn.click(
            fn=_on_download_pdf,
            inputs=[file_input, use_sample_check],
            outputs=[pdf_file],
        ).then(
            fn=lambda: gr.update(visible=True),
            inputs=[],
            outputs=[pdf_file],
        )

        render_anam_bonneagar_footer(
            space_id="cianfhoghlaim/gemini-hackathon-an-scrudu",
            subnation="Ireland (NCCA)",
            stage="Scoil Sinsearach",
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)
