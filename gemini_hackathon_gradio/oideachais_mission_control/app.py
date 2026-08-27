"""gemini_hackathon_gradio.oideachais_mission_control — 5-stage mission control.

Lifted from `sruth/spaces/oideachais_mission_control/`. The Celtic 5-element
tabs are replaced with the 5 British Isles education stages:

  - Aistear (Early Years 0-6)
  - Bunscoil (Primary 4-12)
  - MeanScoil (Junior Cycle 12-15)
  - Scoil Sinsearach (Senior Cycle / Leaving Certificate 15-19)
  - Ollscoil (Tertiary — Phase 2)

The 4-tab structure becomes 5 tabs. Each tab is wired to a marimo
notebook + the Cognify + BAML extraction buttons per stage.

The full app implementation is in W12.
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
    translate as t,
)


_log = logging.getLogger("oideachais_mission_control.app")


def build_app():
    """Build the Oideachais Mission Control Gradio app (5-tab).

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with "
            "`pip install gradio>=5.28.0,<6.0`"
        )
    with gr.Blocks(
        title="Oideachais — Mission Control",
        theme=apply_education_theme(),
        css=GRADIO_CSS,
    ) as demo:
        gr.Markdown(
            f"""# {t("mission_control.title")}
### *{t("mission_control.subtitle")}*""",
            elem_classes="stage-bunscoil",
        )

        with gr.Tabs():
            with gr.Tab("Aistear", elem_classes="stage-aistear"):
                gr.Markdown(
                    "_Early Childhood (0-6). Per-stage BAML extractions, "
                    "marimo notebook, Cognee cognify button, BAML "
                    "extraction button. See W5 for the Ireland pipeline._"
                )

            with gr.Tab("Bunscoil (Primary)", elem_classes="stage-bunscoil"):
                gr.Markdown(
                    "_Primary (Stages 1-4, ages 4-12). 12 NCCA areas._"
                )

            with gr.Tab("MeanScoil (Junior Cycle)", elem_classes="stage-meanscoil"):
                gr.Markdown(
                    "_Junior Cycle (Years 1-3, ages 12-15). 18 NCCA "
                    "subjects + 16 short courses + 36 CBAs._"
                )

            with gr.Tab("Scoil Sinsearach (LC)", elem_classes="stage-scoil-sinsearach"):
                gr.Markdown(
                    "_Senior Cycle / Leaving Certificate (Years 4-6, ages "
                    "15-19). 14 NCCA subjects (8 NCCA + 6 adjacent) + the "
                    "5 NCCA policy corpus (W2)._"
                )

            with gr.Tab("Ollscoil (Tertiary)", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "_Tertiary — Phase 2. UoG + 5 programmes (deferred)._"
                )

        render_anam_bonneagar_footer(
            space_id="cianfhoghlaim/gemini-hackathon-mission-control",
            subnation="Ireland (NCCA)",
            stage="All stages",
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)


__all__ = ["build_app"]
