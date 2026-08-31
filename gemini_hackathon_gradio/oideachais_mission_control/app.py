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

Each tab now shows a live `gr.Dataframe` sourced from
`raw.official_documents` in `gemini_hackathon.duckdb` — filtered by
jurisdiction + level so the operator can see the available evidence at a
glance.
"""

from __future__ import annotations

import logging
from pathlib import Path

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

_DUCKDB_PATH = Path(__file__).resolve().parents[2] / "gemini_hackathon.duckdb"

# Each tab maps to one (or more) jurisdictions + the canonical
# `level` filter that matches the 5-stage taxonomy. The Irish rows
# default to "Ireland" + the per-stage level labels.
_STAGE_FILTERS = {
    "aistear": ("Ireland", ("Early Years", "Aistear", "Foundation")),
    "bunscoil": ("Ireland", ("Primary", "Bunscoil", "KS1", "KS2")),
    "meanscoil": ("Ireland", ("Junior Cycle", "MeanScoil", "KS3", "GCSE")),
    "scoil-sinsearach": ("Ireland", ("Senior Cycle", "Scoil Sinsearach", "KS4", "A-Level", "Leaving Certificate")),
    "ollscoil": ("Ireland", ("Tertiary", "Ollscoil", "Higher Education", "Degree")),
}


def _stage_documents(jurisdiction: str, level_filter: tuple[str, ...]) -> list[list]:
    """Return the rows for one stage tab from `raw.official_documents`."""
    if not _DUCKDB_PATH.exists():
        return [["ERROR", f"missing {_DUCKDB_PATH}", "", "", "", ""]]
    try:
        import duckdb

        like_clauses = " OR ".join(["level ILIKE ?"] * len(level_filter))
        params: list = [f"%{level}%" for level in level_filter]
        sql = (
            "SELECT source_id, jurisdiction, level, subject, language, file_size_bytes "
            "FROM raw.official_documents WHERE jurisdiction = ? "
            f"AND ({like_clauses}) "
            "ORDER BY level, subject LIMIT 100"
        )
        with duckdb.connect(str(_DUCKDB_PATH), read_only=True) as con:
            rows = con.execute(sql, [jurisdiction, *params]).fetchall()
        return [list(r) for r in rows] if rows else [["", "(no rows match this stage)", "", "", "", ""]]
    except Exception as exc:  # noqa: BLE001 — surfaces in UI
        return [["ERROR", str(exc), "", "", "", ""]]


def build_app():
    """Build the Oideachais Mission Control Gradio app (5-tab).

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with "
            "`pip install gradio>=6.0,<7.0`"
        )
    with gr.Blocks(
        title="Oideachais — Mission Control",
        theme=apply_education_theme(),
        css=GRADIO_CSS,
    ) as demo:
        gr.Markdown(
            f"""# {t("mission_control.title")}
### *{t("mission_control.subtitle")}*

The 5-stage mission control — each tab surfaces the live
`raw.official_documents` rows for that stage's jurisdiction + level
filter, so the operator can see what evidence is available before they
hit the Cognify / BAML extraction buttons.""",
            elem_classes="stage-bunscoil",
        )

        headers = ["source_id", "jurisdiction", "level", "subject", "language", "file_size_bytes"]

        with gr.Tabs():
            with gr.Tab("Aistear", elem_classes="stage-aistear"):
                gr.Markdown("**Early Childhood (0-6).** Filtered on Early Years / Aistear / Foundation.")
                gr.Dataframe(
                    headers=headers,
                    value=_stage_documents(*_STAGE_FILTERS["aistear"]),
                    interactive=False,
                    wrap=True,
                )

            with gr.Tab("Bunscoil (Primary)", elem_classes="stage-bunscoil"):
                gr.Markdown("**Primary (Stages 1-4, ages 4-12).** 12 NCCA areas + KS1/KS2.")
                gr.Dataframe(
                    headers=headers,
                    value=_stage_documents(*_STAGE_FILTERS["bunscoil"]),
                    interactive=False,
                    wrap=True,
                )

            with gr.Tab("MeanScoil (Junior Cycle)", elem_classes="stage-meanscoil"):
                gr.Markdown("**Junior Cycle (Years 1-3, ages 12-15).** 18 NCCA subjects + KS3 / GCSE.")
                gr.Dataframe(
                    headers=headers,
                    value=_stage_documents(*_STAGE_FILTERS["meanscoil"]),
                    interactive=False,
                    wrap=True,
                )

            with gr.Tab("Scoil Sinsearach (LC)", elem_classes="stage-scoil-sinsearach"):
                gr.Markdown(
                    "**Senior Cycle / Leaving Certificate (Years 4-6, ages "
                    "15-19).** 14 NCCA subjects + the 5 NCCA policy corpus (W2)."
                )
                gr.Dataframe(
                    headers=headers,
                    value=_stage_documents(*_STAGE_FILTERS["scoil-sinsearach"]),
                    interactive=False,
                    wrap=True,
                )

            with gr.Tab("Ollscoil (Tertiary)", elem_classes="stage-ollscoil"):
                gr.Markdown("**Tertiary — Phase 2.** UoG + 5 programmes.")
                gr.Dataframe(
                    headers=headers,
                    value=_stage_documents(*_STAGE_FILTERS["ollscoil"]),
                    interactive=False,
                    wrap=True,
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
