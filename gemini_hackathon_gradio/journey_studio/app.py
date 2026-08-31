"""gemini_hackathon_gradio.journey_studio — the 5-stage × subnation journey studio.

A thin Gradio host that lets the operator pick a subnation + stage and
embeds the matching marimo notebook as an iframe. Mirrors the palette
loader pattern from `journey/level_0_pick_subnation/app.py`.

The 5 stages (canonical, mapped to the 5 colour codes in
`gemini_hackathon_gradio/_common/theme.py:EDUCATION_PALETTE`):

    1. Aistear (Early Years 0-6)
    2. Bunscoil (Primary 4-12)
    3. MeanScoil (Junior Cycle 12-15)
    4. Scoil Sinsearach (Senior Cycle / Leaving Certificate 15-19)
    5. Ollscoil (Tertiary — Phase 2)

The 8 subnations are the canonical list (also mirrored in
`journey/level_0_pick_subnation/app.py:SUBNATIONS`).

The marimo iframes point at `https://marimo.app/.../<path>` (the marimo
WASM hosting). When the operator's notebook lives locally, the studio
falls back to a placeholder card.
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
)

_log = logging.getLogger("journey_studio.app")


# (slug, display_name, palette_file, accent_class) — accent_class is the
# CSS class from gemini_hackathon_gradio/_common/theme.py that paints the
# 5-stage accent strip.
SUBNATIONS: tuple[tuple[str, str, str, str], ...] = (
    ("ireland", "Ireland (NCCA)", "ncca_palette.json", "stage-scoil-sinsearach"),
    ("england", "England (AQA + OCR + Pearson)", "aqa_palette.json", "stage-meanscoil"),
    (
        "northern_ireland",
        "Northern Ireland (CCEA)",
        "northern_ireland_palette.json",
        "stage-bunscoil",
    ),
    ("scotland", "Scotland (SQA)", "scotland_palette.json", "stage-aistear"),
    ("wales", "Wales (WJEC)", "wales_palette.json", "stage-ollscoil"),
    ("jersey", "Jersey (States of Jersey)", "jersey_palette.json", "stage-bunscoil"),
    ("guernsey", "Guernsey (States of Guernsey)", "guernsey_palette.json", "stage-bunscoil"),
    ("isle_of_man", "Isle of Man (DESC)", "isle_of_man_palette.json", "stage-aistear"),
)

# (stage, accent_class, accent_hex) — the 5 stages.
STAGES: tuple[tuple[str, str, str], ...] = (
    ("Aistear", "stage-aistear", "#e8915c"),
    ("Bunscoil", "stage-bunscoil", "#1e80c6"),
    ("MeanScoil", "stage-meanscoil", "#28955e"),
    ("Scoil Sinsearach", "stage-scoil-sinsearach", "#cc9966"),
    ("Ollscoil", "stage-ollscoil", "#5a4fcf"),
)


# The notebook registry — the iframe src we embed for each (subnation,
# stage) pair. Keys are `(subnation_slug, stage_slug)` and values are the
# marimo.app WASM URL (or a local relative path when the notebook is in
# the repo). The empty default points at a placeholder — real URLs are
# filled in as the per-stage notebooks come online.
_NOTEBOOKS: dict[tuple[str, str], str] = {
    ("ireland", "aistear"): "https://marimo.app/cianfhoghlaim/gemini-hackathon-ireland-aistear",
    ("ireland", "bunscoil"): "https://marimo.app/cianfhoghlaim/gemini-hackathon-ireland-bunscoil",
    ("ireland", "meanscoil"): "https://marimo.app/cianfhoghlaim/gemini-hackathon-ireland-meanscoil",
    (
        "ireland",
        "scoil-sinsearach",
    ): "https://marimo.app/cianfhoghlaim/gemini-hackathon-ireland-sinsearach",
    ("ireland", "ollscoil"): "https://marimo.app/cianfhoghlaim/gemini-hackathon-ireland-ollscoil",
    # Per-jurisdiction stubs (Phase 2 — every jurisdiction gets the same
    # 5-stage skeleton; the per-jurisdiction marimos live in the hf_spaces/
    # mirror).
    (
        "england",
        "scoil-sinsearach",
    ): "https://marimo.app/cianfhoghlaim/gemini-hackathon-england-sinsearach",
    (
        "northern_ireland",
        "scoil-sinsearach",
    ): "https://marimo.app/cianfhoghlaim/gemini-hackathon-ni-sinsearach",
    (
        "scotland",
        "scoil-sinsearach",
    ): "https://marimo.app/cianfhoghlaim/gemini-hackathon-scotland-sinsearach",
    (
        "wales",
        "scoil-sinsearach",
    ): "https://marimo.app/cianfhoghlaim/gemini-hackathon-wales-sinsearach",
}


def _resolve_notebook(subnation_slug: str, stage_slug: str) -> str:
    """Return the marimo iframe URL for the (subnation, stage) pair.

    Falls back to a "Coming soon" card when the pair isn't yet wired up.
    """
    key = (subnation_slug, stage_slug.lower().replace(" ", "-"))
    if key in _NOTEBOOKS:
        return _NOTEBOOKS[key]
    # Try a less specific key — match by stage only.
    for (_sub_slug, stage_slug_alt), url in _NOTEBOOKS.items():
        if stage_slug_alt == key[1]:
            return url
    return ""


def _stage_slug(stage: str) -> str:
    return stage.lower().replace(" ", "-")


def build_app():
    """Build the Journey Studio — subnation + stage pickers + marimo iframe.

    Raises:
        ImportError: If Gradio is not installed.
    """
    if gr is None:
        raise ImportError(
            "Gradio is required for build_app(); install with `pip install gradio>=6.0,<7.0`"
        )

    with gr.Blocks(
        theme=apply_education_theme(),
        css=GRADIO_CSS,
        title="gemini_hackathon — Journey Studio",
    ) as demo:
        gr.Markdown(
            """# Journey Studio
### 5 stages × 8 subnations × the BIEP evidence pipeline

Pick a subnation, pick a stage — the matching marimo notebook
loads in the iframe below. The 5 stages mirror the colour codes in
`gemini_hackathon_gradio/_common/theme.py:EDUCATION_PALETTE` so the UI
visibly tracks where you are in the journey.""",
            elem_classes="stage-scoil-sinsearach",
        )

        with gr.Row():
            subnation_picker = gr.Radio(
                choices=[s[1] for s in SUBNATIONS],
                value=SUBNATIONS[0][1],
                label="Subnation",
            )
            stage_picker = gr.Radio(
                choices=[s[0] for s in STAGES],
                value=STAGES[3][0],  # Scoil Sinsearach by default
                label="Stage",
            )

        # The palette preview — a small swatch + the matching accent class.
        palette_out = gr.JSON(label="Palette")

        # The marimo iframe — using gr.HTML for an <iframe> with srcdoc fallback.
        notebook_html = gr.HTML(
            value="<em>Pick a subnation + stage above.</em>",
            label="Notebook",
        )

        # The "explain" section — the matching journey_orchestrator stage + BAML function.
        explain_out = gr.Markdown()

        def _on_pick(subnation_display: str, stage: str) -> tuple[dict, str, str]:
            """Resolve the picker pair to (palette, iframe srcdoc, explainer)."""
            sub = next(s for s in SUBNATIONS if s[1] == subnation_display)
            sub_slug, _, palette_file, accent_class = sub
            stage_slug = _stage_slug(stage)
            stage_accent = next(s for s in STAGES if s[0] == stage)
            _, stage_class_name, accent_hex = stage_accent

            palette = {
                "subnation_slug": sub_slug,
                "palette_file": palette_file,
                "accent_class": accent_class,
                "stage_slug": stage_slug,
                "stage_class": stage_class_name,
                "stage_accent_hex": accent_hex,
            }

            notebook_url = _resolve_notebook(sub_slug, stage)
            if notebook_url:
                iframe = (
                    f'<iframe src="{notebook_url}" '
                    'width="100%" height="700" '
                    'style="border:1px solid var(--color-secondary); border-radius:8px;" '
                    'title="marimo notebook"></iframe>'
                )
            else:
                # Local notebook fallback — try to find a file in /notebooks/ matching the stage.
                (Path(__file__).resolve().parents[2] / "notebooks" / f"{stage_slug}_*.py")
                candidates = sorted(
                    Path(__file__).resolve().parents[2].glob("notebooks/1[0-9]*.py")
                )
                local_match = next((p for p in candidates if stage_slug in p.name.lower()), None)
                if local_match:
                    notebook_url = f"file://{local_match}"
                    iframe = (
                        f'<div style="padding:24px;border:1px dashed var(--color-secondary);border-radius:8px;'
                        f'background:var(--color-background);">'
                        f"<strong>Local marimo:</strong> "
                        f"<code>{local_match.relative_to(local_match.parents[2])}</code><br>"
                        f"Open with <code>marimo edit {local_match.name}</code>.<br><br>"
                        f"WASM preview not yet wired for this stage."
                        f"</div>"
                    )
                else:
                    iframe = (
                        f'<div style="padding:24px;border:1px dashed var(--color-secondary);border-radius:8px;'
                        f'background:var(--color-background);">'
                        f"<strong>Coming soon.</strong><br>"
                        f"No marimo notebook wired for <code>{sub_slug} × {stage_slug}</code> yet. "
                        f"Add it to <code>_NOTEBOOKS</code> in this file or to the local <code>notebooks/</code> directory."
                        f"</div>"
                    )

            explain = (
                f"**Stage:** {stage} (`{stage_class_name}`, accent `{accent_hex}`)\n\n"
                f"**Subnation:** {subnation_display} → `{sub_slug}` (palette `{palette_file}`)\n\n"
                f"**Journey level:** `journey/level_{ {'Aistear': 0, 'Bunscoil': 1, 'MeanScoil': 2, 'Scoil Sinsearach': 3, 'Ollscoil': 4}.get(stage, 0) }_*`\n\n"
                f"**Marimo URL:** `{notebook_url or '(not wired)'}`"
            )
            return palette, iframe, explain

        subnation_picker.change(
            fn=_on_pick,
            inputs=[subnation_picker, stage_picker],
            outputs=[palette_out, notebook_html, explain_out],
        )
        stage_picker.change(
            fn=_on_pick,
            inputs=[subnation_picker, stage_picker],
            outputs=[palette_out, notebook_html, explain_out],
        )

        # Initial population — the default picker values.
        initial_palette, initial_iframe, initial_explain = _on_pick(SUBNATIONS[0][1], STAGES[3][0])
        palette_out.value = initial_palette
        notebook_html.value = initial_iframe
        explain_out.value = initial_explain

        render_anam_bonneagar_footer(
            space_id="cianfhoghlaim/gemini-hackathon-journey-studio",
            subnation="All subnations",
            stage="All stages",
        )

    return demo


if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="0.0.0.0", server_port=7860)


__all__ = ["STAGES", "SUBNATIONS", "build_app"]
