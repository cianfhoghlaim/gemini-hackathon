"""gemini_hackathon_gradio.oideachais_mission_control — 5-operator mission control.

Lifted from `sruth/spaces/oideachais_mission_control/`. The Celtic 5-element
tabs were replaced with the 5 British Isles education stages in Phase 3.

Phase 4 (the `2026-08-31-journey-gradio-polish-v1` openspec change)
extended the studio with 5 NEW operator tabs that surface live platform
state for the workshop host:

  - **Subjects** — the 14-subject SUBJECT_WIRING_REGISTRY as a Dataframe
  - **Models** — the MODEL_REGISTRY._entries as a Dataframe
  - **Outputs** — the generated certificates (data/certificates/*.json)
  - **Observability** — the last 5 structlog events (mocked)
  - **Settings** — the .env.example keys as a Markdown code block

The 5 stage tabs (Aistear / Bunscoil / MeanScoil / Scoil Sinsearach /
Ollscoil) are preserved as a separate section so the operator can see
the live evidence rows per stage.
"""

from __future__ import annotations

import logging
from pathlib import Path

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore[assignment]

from gemini_hackathon.agents.registry import SUBJECT_WIRING_REGISTRY

from .._common import (
    GRADIO_CSS,
    apply_education_theme,
    render_anam_bonneagar_footer,
)
from .._common import (
    translate as t,
)

_log = logging.getLogger("oideachais_mission_control.app")

_DUCKDB_PATH = Path(__file__).resolve().parents[2] / "gemini_hackathon.duckdb"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # the gemini_hackathon/ repo root
_CERTIFICATES_DIR = _PROJECT_ROOT / "data" / "certificates"
_ENV_EXAMPLE = _PROJECT_ROOT / ".env.example"

# Each stage tab maps to one (or more) jurisdictions + the canonical
# `level` filter that matches the 5-stage taxonomy.
_STAGE_FILTERS = {
    "aistear": ("Ireland", ("Early Years", "Aistear", "Foundation")),
    "bunscoil": ("Ireland", ("Primary", "Bunscoil", "KS1", "KS2")),
    "meanscoil": ("Ireland", ("Junior Cycle", "MeanScoil", "KS3", "GCSE")),
    "scoil-sinsearach": (
        "Ireland",
        ("Senior Cycle", "Scoil Sinsearach", "KS4", "A-Level", "Leaving Certificate"),
    ),
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
        return (
            [list(r) for r in rows]
            if rows
            else [["", "(no rows match this stage)", "", "", "", ""]]
        )
    except Exception as exc:
        return [["ERROR", str(exc), "", "", "", ""]]


# ---------------------------------------------------------------------------
# Phase 4 polish — the 5 operator panels
# ---------------------------------------------------------------------------


def _subjects_dataframe_rows() -> list[list]:
    """Render the 14-subject SUBJECT_WIRING_REGISTRY as a Dataframe."""
    rows: list[list] = []
    for slug, wire in sorted(SUBJECT_WIRING_REGISTRY.items()):
        rows.append(
            [
                slug,
                wire.ncca_subject,
                "(stage-agnostic)",  # subjects are stage-agnostic in the registry
                "EN+GA",  # default bilingual
                wire.langfuse_trace_name,
                wire.baml_prefix,
                wire.memory_namespace,
                wire.litellm_routing_key,
            ]
        )
    return rows


def _models_dataframe_rows() -> list[list]:
    """Render MODEL_REGISTRY._entries as a Dataframe."""
    try:
        from gemini_hackathon.model_registry import MODEL_REGISTRY
    except ImportError as exc:
        return [["ERROR", f"MODEL_REGISTRY import failed: {exc}", "", "", "", ""]]
    rows: list[list] = []
    for entry in MODEL_REGISTRY:
        rows.append(
            [
                entry.key,
                str(entry.family),
                entry.role,
                str(entry.backend),
                str(entry.profile),
                "yes" if entry.available else "no",
            ]
        )
    return rows


def _outputs_dataframe_rows() -> list[list]:
    """List the generated certificate JSONs in data/certificates/."""
    if not _CERTIFICATES_DIR.exists():
        return [["", "(data/certificates/ does not exist yet)", "", "", ""]]
    paths = sorted(_CERTIFICATES_DIR.glob("*.json"))
    if not paths:
        return [["", "(no certificates generated yet)", "", "", ""]]
    return [
        [p.name, str(p.stat().st_size), p.stat().st_mtime, str(p.parent), p.name] for p in paths
    ]


def _observability_events() -> list[list]:
    """Return 5 mocked structlog-style events (Phase 4 placeholder).

    The real implementation reads the logfire / langfuse endpoint —
    that's Phase 5. For the workshop demo we surface the last 5 mocked
    events so the operator can see the panel.
    """
    return [
        ["ts=10:00:01", "level=INFO", "module=editorial_studio.app", "msg=build_app() OK"],
        ["ts=10:00:02", "level=INFO", "module=anam_education.app", "msg=build_app() OK"],
        [
            "ts=10:00:03",
            "level=INFO",
            "module=oideachais_mission_control.app",
            "msg=build_app() OK",
        ],
        ["ts=10:00:04", "level=INFO", "module=oideachais_pdf_review.app", "msg=build_app() OK"],
        ["ts=10:00:05", "level=INFO", "module=an_scrudu.app", "msg=build_app() OK"],
    ]


def _settings_markdown() -> str:
    """Render the .env.example keys as a fenced code block."""
    if not _ENV_EXAMPLE.exists():
        return "_`.env.example` not found in the project root._"
    try:
        text = _ENV_EXAMPLE.read_text(encoding="utf-8")
    except OSError as exc:
        return f"_Could not read `.env.example`: {exc}_"
    # Show only the `KEY=value` lines + the section comments.
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("#")
            or ("=" in stripped and not stripped.startswith("export "))
        ):
            out.append(line)
        else:
            out.append(line)
    return "```bash\n" + "\n".join(out) + "\n```"


def build_app():
    """Build the Oideachais Mission Control Gradio app (5 stage + 5 operator tabs).

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with `pip install gradio>=6.0,<7.0`"
        )
    with gr.Blocks(
        title="Oideachais — Mission Control",
        theme=apply_education_theme(),
        css=GRADIO_CSS,
    ) as demo:
        gr.Markdown(
            f"""# {t("mission_control.title")}
### *{t("mission_control.subtitle")}*

The 5-stage mission control + 5 operator panels. The 5 stage tabs
(Aistear / Bunscoil / MeanScoil / Scoil Sinsearach / Ollscoil) surface
the live `raw.official_documents` rows per stage. The 5 operator tabs
(Subjects / Models / Outputs / Observability / Settings) surface the
canonical platform registries.""",
            elem_classes="stage-bunscoil",
        )

        headers = ["source_id", "jurisdiction", "level", "subject", "language", "file_size_bytes"]

        with gr.Tabs():
            # ── Phase 4 polish — the 5 operator tabs ────────────────────
            with gr.Tab("Subjects", elem_classes="stage-bunscoil"):
                gr.Markdown(
                    "**The 14-subject `SUBJECT_WIRING_REGISTRY`** "
                    "(`gemini_hackathon/agents/registry.py:94`)."
                )
                subj_refresh = gr.Button("Refresh", variant="primary")
                subj_df = gr.Dataframe(
                    headers=[
                        "subject_slug",
                        "ncca_subject",
                        "stage",
                        "language",
                        "langfuse_trace_name",
                        "baml_prefix",
                        "memory_namespace",
                        "litellm_routing_key",
                    ],
                    value=_subjects_dataframe_rows(),
                    interactive=False,
                    wrap=True,
                )
                subj_refresh.click(fn=_subjects_dataframe_rows, outputs=[subj_df])

            with gr.Tab("Models", elem_classes="stage-meanscoil"):
                gr.Markdown(
                    "**The `MODEL_REGISTRY._entries`** (`gemini_hackathon/model_registry.py:1092`)."
                )
                models_refresh = gr.Button("Refresh", variant="primary")
                models_df = gr.Dataframe(
                    headers=["key", "family", "role", "backend", "profile", "available"],
                    value=_models_dataframe_rows(),
                    interactive=False,
                    wrap=True,
                )
                models_refresh.click(fn=_models_dataframe_rows, outputs=[models_df])

            with gr.Tab("Outputs", elem_classes="stage-scoil-sinsearach"):
                gr.Markdown(
                    "**Generated certificates.** Reads JSONs from "
                    "`data/certificates/` (the output of "
                    "`CertificatePipeline.run()`)."
                )
                outputs_refresh = gr.Button("Refresh", variant="primary")
                outputs_df = gr.Dataframe(
                    headers=["filename", "bytes", "mtime", "dir", "_"],
                    value=_outputs_dataframe_rows(),
                    interactive=False,
                    wrap=True,
                )
                outputs_refresh.click(fn=_outputs_dataframe_rows, outputs=[outputs_df])

            with gr.Tab("Observability", elem_classes="stage-ollscoil"):
                gr.Markdown(
                    "**Last 5 structlog events.** Real implementation "
                    "(Logfire / Langfuse) lands in Phase 5 — for now these "
                    "are mocked so the operator sees the panel."
                )
                gr.Dataframe(
                    headers=["timestamp", "level", "module", "message"],
                    value=_observability_events(),
                    interactive=False,
                    wrap=True,
                )

            with gr.Tab("Settings", elem_classes="stage-aistear"):
                gr.Markdown(
                    "**The `.env.example` keys.** Every env var the platform reads at runtime."
                )
                gr.Markdown(value=_settings_markdown())

            # ── Phase 3 baseline — the 5 stage tabs ─────────────────────
            with gr.Tab("Aistear", elem_classes="stage-aistear"):
                gr.Markdown(
                    "**Early Childhood (0-6).** Filtered on Early Years / Aistear / Foundation."
                )
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
                gr.Markdown(
                    "**Junior Cycle (Years 1-3, ages 12-15).** 18 NCCA subjects + KS3 / GCSE."
                )
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
