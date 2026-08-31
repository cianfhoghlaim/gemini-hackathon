"""gemini_hackathon_learning_graphs — the HF Space entry point.

The HF Space for the 4-tab learning-graph studio. Lazy-imports the
canonical `gemini_hackathon_gradio.an_learning_graph` package so the
Space doesn't force the full `gemini_hackathon_gradio` dependency on
the cold-start path. When the canonical package is missing, falls
back to a 4-tab `gr.Markdown` placeholder so the demo at least
renders — and the **Pedagogy overlay tab reads the disk cache at
``data/bi_ep/annotated_learning_graphs/<subject>.json``** so the
Phase 5 materialisation is surfaced even when the full studio is
absent.
"""

from __future__ import annotations

import json
import logging
import pathlib

import gradio as gr

_log = logging.getLogger(__name__)


# The 6 priority subjects (canonical NCCE showcase list).
PRIORITY_SUBJECTS: tuple[str, ...] = (
    "computer_science",
    "mathematics",
    "english",
    "gaeilge",
    "chemistry",
    "geography",
)


def _annotated_graph_path(subject: str) -> pathlib.Path:
    """Return the canonical disk-cache path for one subject's annotated graph."""
    return pathlib.Path(f"data/bi_ep/annotated_learning_graphs/{subject}.json")


def _pedagogy_cache_path() -> pathlib.Path:
    """Return the canonical disk-cache path for the 12 pedagogy principles."""
    return pathlib.Path("data/bi_ep/syllabi_md/uk_ncce/pedagogy_principles.json")


def _render_pedagogy_panel(subject: str) -> str:
    """Render the pedagogy overlay panel as Markdown for one subject.

    Reads the disk cache at
    ``data/bi_ep/annotated_learning_graphs/<subject>.json`` and returns
    a Markdown block that summarises:

      - The number of cells in the underlying learning graph.
      - The number of cells annotated with each of the 12 principles.
      - The pedagogy_source provenance ("cache" / "cognee" / "live_pdf").

    Returns a "no cache yet" message when the disk cache is cold.
    """
    ann = _annotated_graph_path(subject)
    if not ann.is_file():
        return (
            f"_No annotated graph for **{subject}** yet. "
            f"Run `python -m cocoindex_flows.uk_ncce.pedagogy_cache` then "
            f"`python scripts/materialise_annotated_learning_graphs.py` "
            f"to populate `data/bi_ep/annotated_learning_graphs/{subject}.json`._"
        )
    try:
        payload = json.loads(ann.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("HF Space pedagogy: parse failed path=%s reason=%s", ann, exc)
        return f"_Annotated graph parse failed: {exc}_"

    cell_annotations: dict[str, list[str]] = payload.get("cell_annotations", {})
    counts: dict[str, int] = {}
    for ids in cell_annotations.values():
        if not isinstance(ids, list):
            continue
        for pid in ids:
            counts[pid] = counts.get(pid, 0) + 1

    principle_names: dict[str, str] = {}
    cache_path = _pedagogy_cache_path()
    if cache_path.is_file():
        try:
            cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
            for p in cache_payload.get("principles", []):
                if isinstance(p, dict):
                    principle_names[str(p.get("id", ""))] = str(p.get("name", ""))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("HF Space pedagogy: cache parse failed: %s", exc)

    source = payload.get("pedagogy_source", "unknown")
    n_annotated = len(cell_annotations)

    lines = [
        f"### {subject} — pedagogy overlay",
        "",
        f"- **Annotated cells:** `{n_annotated}`",
        f"- **Pedagogy source:** `{source}`",
        f"- **Cache file:** `{ann}`",
        "",
        "**Principle counts:**",
        "",
        "| Principle | Cells |",
        "| --- | --- |",
    ]
    for pid, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        name = principle_names.get(pid, pid)
        lines.append(f"| {name} | {count} |")
    if not counts:
        lines.append("| _(none)_ | 0 |")
    lines.append("")
    lines.append(
        "See `gemini_hackathon_gradio.an_learning_graph.pedagogy_tab` for the "
        "interactive Plotly overlay (per-cell colour + hover cards)."
    )
    return "\n".join(lines)


def _build_pedagogy_tab() -> None:
    """Build the 4th tab — Pedagogy overlay (HF Space disk-cache fallback).

    The full interactive Plotly overlay lives in
    ``gemini_hackathon_gradio.an_learning_graph.pedagogy_tab``. When the
    canonical Gradio studio is missing (this fallback), the HF Space
    renders a Markdown summary of the disk-cache materialisation.
    """
    gr.Markdown(
        "## Pedagogy overlay — disk-cache summary\n\n"
        "The 12 NCCE pedagogy principles applied to every cell of the "
        "per-subject learning graph. The numbers below come from "
        "`data/bi_ep/annotated_learning_graphs/<subject>.json` — the "
        "canonical materialisation produced by "
        "`scripts/materialise_annotated_learning_graphs.py`.\n\n"
        "_Re-extraction requires the local `gemini_hackathon_gradio` package._"
    )

    subject_dd = gr.Dropdown(
        label="Subject",
        choices=list(PRIORITY_SUBJECTS),
        value="computer_science",
    )
    panel_md = gr.Markdown(_render_pedagogy_panel("computer_science"))

    def _on_change(subject: str) -> str:
        return _render_pedagogy_panel(subject)

    subject_dd.change(fn=_on_change, inputs=[subject_dd], outputs=[panel_md])


def _build_app() -> gr.Blocks:
    """Build the canonical learning-graph studio (lazy import)."""
    try:
        from gemini_hackathon_gradio.an_learning_graph import build_app

        demo = build_app()
        if demo is not None:
            return demo
        _log.warning(
            "gemini_hackathon_gradio.an_learning_graph.build_app returned None; "
            "falling back to the placeholder."
        )
    except ImportError as exc:
        _log.warning(
            "gemini_hackathon_gradio not available (%s); falling back to placeholder.",
            exc,
        )

    # Fallback placeholder — mirrors the canonical 4-tab layout. Tabs 1-3
    # are pure Markdown; Tab 4 (Pedagogy overlay) reads the disk cache to
    # surface the Phase 5 materialisation even without the full studio.
    with gr.Blocks(
        title="An Léaráid Foghlama — The Learning Graph Studio",
        theme=gr.themes.Soft(primary_hue="green", secondary_hue="yellow"),
    ) as demo:
        gr.Markdown(
            "# An Léaráid Foghlama — The Learning Graph Studio\n\n"
            "Install `gemini_hackathon_gradio` to enable the full 4-tab studio. "
            "See https://github.com/cianfhoghlaim/gemini-hackathon for the source.\n\n"
            "**Phase 5 of `2026-08-31-ncce-showcase-complete-v1`** wires the "
            "Pedagogy overlay tab to read the disk cache at "
            "`data/bi_ep/annotated_learning_graphs/<subject>.json`."
        )
        with gr.Tab("Render"):
            gr.Markdown(
                "**Tab 1 — Render.** Pick a jurisdiction, subject, and year level; "
                "view the canonical LearningGraph as a Plotly SVG heatmap with "
                "prerequisite edges overlaid. _(Full studio requires the local "
                "`gemini_hackathon_gradio` package.)_"
            )
        with gr.Tab("Equivalencies"):
            gr.Markdown(
                "**Tab 2 — Equivalencies.** Cell-level cross-walk from a single "
                "NCCE source cell to the 7 other British Isles jurisdictions. "
                "Powered by the Firestore `cellEquivalents` collection populated "
                "by `orchestration/defs/3_model_lifecycle/learning_graph_equivalency_graph.py`. "
                "_(Full studio requires the local `gemini_hackathon_gradio` package.)_"
            )
        with gr.Tab("Generate from PDF"):
            gr.Markdown(
                "**Tab 3 — Generate from PDF.** Upload a syllabus PDF and run "
                "the per-subject BAML extractor. The canonical `generate_tab` "
                "lives in `gemini_hackathon_gradio.an_learning_graph.generate_tab`."
            )
        with gr.Tab("Pedagogy overlay"):
            _build_pedagogy_tab()

    return demo


if __name__ == "__main__":
    demo = _build_app()
    demo.launch(server_name="0.0.0.0", server_port=7860)
