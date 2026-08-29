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

import logging

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


def build_app():
    """Build the Anam Oideachais (Education Integration Studio) Gradio app.

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with "
            "`pip install gradio>=5.28.0,<6.0`"
        )

    # The 7 features are wired as Gradio tabs. Each tab delegates to the
    # per-feature module (lifted in W12):
    #
    #   - Curriculum Map        -> gemini_hackathon.dlt_pipelines.ireland (W5)
    #   - Chemistry Visual      -> gemini_hackathon_gradio.anam_education.chemistry_visual
    #   - Exit Card             -> gemini_hackathon_gradio.anam_education.exit_card
    #   - Gaelscribhneoir       -> gemini_hackathon_gradio.anam_education.gaelscribhneoir
    #   - Bilingual EN/GA       -> gemini_hackathon_gradio.anam_education.bilingual_switcher
    #   - Certificate           -> gemini_hackathon_gradio.certificate (W14)
    #   - Skill Progression     -> gemini_hackathon_gradio.anam_education.skill_progression
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
            with gr.Tab("Curriculum Map", elem_classes="stage-bunscoil"):
                gr.Markdown(
                    "_Per-subject LC + JC syllabus map. See W5 for the "
                    "Ireland DLT pipeline + W11 for the per-subnation "
                    "live scrape._"
                )

            with gr.Tab("Chemistry Visual", elem_classes="stage-meanscoil"):
                gr.Markdown(
                    "_SVG molecule renderer for the 8 NCCA LC chemistry "
                    "subjects (extended to 14 NCCA subjects). See "
                    "`anam_education/chemistry_visual.py` (W12)._"
                )

            with gr.Tab("Exit Card", elem_classes="stage-scoil-sinsearach"):
                gr.Markdown(
                    "_Formative-assessment exit-card generator (BAML → typed "
                    "PExitCardSet). Uses `baml_extracts/education/player_assessment.baml`. "
                    "See `anam_education/exit_card.py` (W12)._"
                )

            with gr.Tab("Gaelscribhneoir", elem_classes="stage-aistear"):
                gr.Markdown(
                    "_Irish-text quality checker (fada / eclipsis / punctum "
                    "metrics). Lifted from `sruth/spaces/anam_tuatha/gaelscribhneoir.py`. "
                    "See `anam_education/gaelscribhneoir.py` (W12)._"
                )

            with gr.Tab("Bilingual EN/GA", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "_Bilingual EN/GA toggle (with Welsh / Scottish Gaelic / "
                    "Manx as second-tier). See `anam_education/bilingual_switcher.py` "
                    "(W12)._"
                )

            with gr.Tab("Certificate", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "_LC/JC certificate generation from the 5 NCCA policy "
                    "PDFs (W2). See `gemini_hackathon_gradio.certificate` (W14) — "
                    "the SHOWCASE workstream._"
                )

            with gr.Tab("Skill Progression", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "_Per-learner mastery ledger (W9): Firestore (UI) + "
                    "the mastery-vector store + the Firestore skill-prerequisite graph._"
                )

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
